import os
import hashlib
import py7zr
import tempfile
import traceback
import time # Added for time.time()
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication
from utils.logger import setup_logger

# 初始化logger
logger = setup_logger("hash_thread")

class HashThread(QThread):
    pre_finished = Signal(dict)
    after_finished = Signal(dict)
    
    def __init__(self, mode, install_paths, plugin_hash, installed_status, main_window=None):
        """初始化哈希检查线程
        
        Args:
            mode: 检查模式，"pre"或"after"
            install_paths: 安装路径字典
            plugin_hash: 插件哈希值字典
            installed_status: 安装状态字典
            main_window: 主窗口实例，用于访问UI和状态
        """
        super().__init__()
        self.mode = mode
        self.install_paths = install_paths
        self.plugin_hash = plugin_hash
        self.installed_status = installed_status.copy()
        self.main_window = main_window
        
    def run(self):
        """运行线程"""
        debug_mode = False
        
        # 设置超时限制（分钟）
        timeout_minutes = 10
        max_execution_time = timeout_minutes * 60  # 转换为秒
        start_execution_time = time.time()
        
        # 尝试检测是否处于调试模式
        if self.main_window and hasattr(self.main_window, 'debug_manager'):
            debug_mode = self.main_window.debug_manager._is_debug_mode()
            
        if debug_mode:
            logger.debug(f"DEBUG: 设置哈希计算超时时间: {timeout_minutes} 分钟")
            
        # 在各个关键步骤添加超时检测
        def check_timeout():
            elapsed = time.time() - start_execution_time
            if elapsed > max_execution_time:
                if debug_mode:
                    logger.error(f"DEBUG: 哈希计算超时，已执行 {elapsed:.1f} 秒，超过限制的 {max_execution_time} 秒")
                return True
            return False
        
        if self.mode == "pre":
            status_copy = self.installed_status.copy()
            
            for game_version, install_path in self.install_paths.items():
                if self.isInterruptionRequested():
                    break
                if not os.path.exists(install_path):
                    status_copy[game_version] = False
                    if debug_mode:
                        logger.debug(f"DEBUG: 哈希预检查 - {game_version} 补丁文件不存在: {install_path}")
                    continue
                    
                try:
                    expected_hash = self.plugin_hash.get(game_version, "")
                    if not expected_hash:
                        if debug_mode:
                            logger.debug(f"DEBUG: 哈希预检查 - {game_version} 没有预期哈希值，跳过哈希检查")
                        # 当没有预期哈希值时，保持当前状态不变
                        continue
                        
                    # 分块读取，避免大文件一次性读取内存
                    hash_obj = hashlib.sha256()
                    with open(install_path, "rb") as f:
                        while True:
                            if self.isInterruptionRequested():
                                break
                            # 检查超时
                            if check_timeout():
                                logger.error(f"哈希计算超时，强制终止")
                                result["passed"] = False
                                result["game"] = game_version
                                result["message"] = f"\n{game_version} 哈希计算超时，已超过 {timeout_minutes} 分钟。\n\n请考虑跳过哈希校验或稍后再试。\n"
                                break
                            chunk = f.read(1024 * 1024)
                            if not chunk:
                                break
                            hash_obj.update(chunk)
                    file_hash = hash_obj.hexdigest()
                    
                    if debug_mode:
                        logger.debug(f"DEBUG: 哈希预检查 - {game_version}")
                        logger.debug(f"DEBUG: 文件路径: {install_path}")
                        logger.debug(f"DEBUG: 预期哈希值: {expected_hash}")
                        logger.debug(f"DEBUG: 实际哈希值: {file_hash}")
                        logger.debug(f"DEBUG: 哈希匹配: {file_hash == expected_hash}")
                    
                    if file_hash == expected_hash:
                        status_copy[game_version] = True
                        if debug_mode:
                            logger.debug(f"DEBUG: 哈希预检查 - {game_version} 哈希匹配成功")
                    else:
                        status_copy[game_version] = False
                        if debug_mode:
                            logger.debug(f"DEBUG: 哈希预检查 - {game_version} 哈希不匹配")
                except Exception as e:
                    status_copy[game_version] = False
                    if debug_mode:
                        logger.debug(f"DEBUG: 哈希预检查异常 - {game_version}: {str(e)}")
            
            self.pre_finished.emit(status_copy)
        
        elif self.mode == "after":
            result = {"passed": True, "game": "", "message": ""}
            
            for game_version, install_path in self.install_paths.items():
                if self.isInterruptionRequested():
                    break
                if not os.path.exists(install_path):
                    if debug_mode:
                        logger.debug(f"DEBUG: 哈希后检查 - {game_version} 补丁文件不存在: {install_path}")
                    continue
                    
                # 设置当前处理的游戏版本
                result["game"] = game_version
                    
                try:
                    expected_hash = self.plugin_hash.get(game_version, "")
                    if not expected_hash:
                        if debug_mode:
                            logger.debug(f"DEBUG: 哈希后检查 - {game_version} 没有预期哈希值，跳过哈希检查")
                        # 当没有预期哈希值时，跳过检查
                        continue
                        
                    # 检查文件存在和可读性
                    if not os.path.exists(install_path):
                        logger.error(f"哈希校验失败 - 文件不存在: {install_path}")
                        result["passed"] = False
                        result["game"] = game_version
                        result["message"] = f"\n{game_version} 安装后的文件不存在，无法校验。\n\n文件路径: {install_path}\n"
                        break
                    
                    # 记录文件大小信息
                    file_size = os.path.getsize(install_path)
                    logger.info(f"开始校验 {game_version} 补丁文件")
                    logger.debug(f"文件路径: {install_path}, 文件大小: {file_size} 字节")
                    
                    # 增加块大小，提高大文件处理性能
                    # 文件越大，块越大，最大256MB
                    chunk_size = min(256 * 1024 * 1024, max(16 * 1024 * 1024, file_size // 20))
                    logger.debug(f"使用块大小: {chunk_size // (1024 * 1024)}MB")
                    
                    # 分块读取，避免大文件一次性读取内存
                    hash_obj = hashlib.sha256()
                    bytes_read = 0
                    start_time = time.time()
                    last_progress_time = start_time
                    with open(install_path, "rb") as f:
                        while True:
                            if self.isInterruptionRequested():
                                break
                            # 检查超时
                            if check_timeout():
                                logger.error(f"哈希计算超时，强制终止")
                                result["passed"] = False
                                result["game"] = game_version
                                result["message"] = f"\n{game_version} 哈希计算超时，已超过 {timeout_minutes} 分钟。\n\n请考虑跳过哈希校验或稍后再试。\n"
                                break
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            bytes_read += len(chunk)
                            hash_obj.update(chunk)
                            
                            # 每秒更新一次进度
                            current_time = time.time()
                            if current_time - last_progress_time >= 1.0:
                                progress = bytes_read / file_size * 100
                                elapsed = current_time - start_time
                                speed = bytes_read / (elapsed if elapsed > 0 else 1) / (1024 * 1024)  # MB/s
                                logger.debug(f"哈希计算进度: {progress:.1f}% - 已处理: {bytes_read/(1024*1024):.1f}MB/{file_size/(1024*1024):.1f}MB - 速度: {speed:.1f}MB/s")
                                last_progress_time = current_time
                                
                    # 计算最终的哈希值
                    file_hash = hash_obj.hexdigest()
                    
                    # 记录总用时
                    total_time = time.time() - start_time
                    logger.debug(f"哈希计算完成，耗时: {total_time:.1f}秒，平均速度: {file_size/(total_time*1024*1024):.1f}MB/s")
                    
                    # 记录哈希比较结果
                    is_valid = file_hash == expected_hash
                    logger.info(f"{game_version} 哈希校验{'通过' if is_valid else '失败'}")
                    logger.debug(f"哈希校验详情 - {game_version}:")
                    logger.debug(f"  文件: {install_path}")
                    logger.debug(f"  读取字节数: {bytes_read} / {file_size}")
                    logger.debug(f"  预期哈希: {expected_hash}")
                    logger.debug(f"  实际哈希: {file_hash}")
                    
                    if debug_mode:
                        logger.debug(f"DEBUG: 哈希后检查 - {game_version}")
                        logger.debug(f"DEBUG: 文件路径: {install_path}")
                        logger.debug(f"DEBUG: 预期哈希值: {expected_hash}")
                        logger.debug(f"DEBUG: 实际哈希值: {file_hash}")
                        logger.debug(f"DEBUG: 哈希匹配: {file_hash == expected_hash}")
                    
                    if file_hash != expected_hash:
                        result["passed"] = False
                        result["game"] = game_version
                        result["message"] = f"\n{game_version} 安装后的文件校验失败。\n\n文件可能已损坏或被篡改，请重新安装。\n预期哈希: {expected_hash[:10]}...\n实际哈希: {file_hash[:10]}...\n"
                        if debug_mode:
                            logger.debug(f"DEBUG: 哈希后检查 - {game_version} 哈希不匹配")
                        break
                    elif debug_mode:
                        logger.debug(f"DEBUG: 哈希后检查 - {game_version} 哈希匹配成功")
                except Exception as e:
                    result["passed"] = False
                    result["game"] = game_version
                    result["message"] = f"\n{game_version} 安装后的文件校验过程中发生错误。\n\n错误信息: {str(e)}\n"
                    if debug_mode:
                        logger.debug(f"DEBUG: 哈希后检查异常 - {game_version}: {str(e)}")
                    break
            
            self.after_finished.emit(result)


class OfflineHashVerifyThread(QThread):
    """离线模式下验证补丁文件哈希的线程，支持进度更新"""
    
    progress = Signal(int)  # 进度信号，0-100
    finished = Signal(bool, str, str)  # 完成信号，(成功/失败, 错误信息, 解压后的补丁文件路径)
    
    def __init__(self, game_version, file_path, plugin_hash, main_window=None):
        super().__init__()
        self.game_version = game_version
        self.file_path = file_path
        self.plugin_hash = plugin_hash
        self.main_window = main_window
        self.extracted_patch_path = None  # 添加解压后的补丁文件路径
        
        # 获取预期的哈希值
        self.expected_hash = None
        
        # 直接使用完整游戏名称作为键
        self.expected_hash = self.plugin_hash.get(game_version, "")
        
        # 设置调试模式标志
        self.debug_mode = False
        if main_window and hasattr(main_window, 'debug_manager'):
            self.debug_mode = main_window.debug_manager._is_debug_mode()
            
    def run(self):
        """运行线程"""
        debug_mode = False
        
        # 设置超时限制（分钟）
        timeout_minutes = 10
        max_execution_time = timeout_minutes * 60  # 转换为秒
        start_execution_time = time.time()
        
        # 尝试检测是否处于调试模式
        if self.main_window and hasattr(self.main_window, 'debug_manager'):
            debug_mode = self.main_window.debug_manager._is_debug_mode()
            
        # 检查超时的函数
        def check_timeout():
            elapsed = time.time() - start_execution_time
            if elapsed > max_execution_time:
                if debug_mode:
                    logger.debug(f"DEBUG: 哈希校验超时，已运行 {elapsed:.1f} 秒")
                return True
            return False
            
        # 获取预期的哈希值
        expected_hash = self.plugin_hash.get(self.game_version, "")
        
        if not expected_hash:
            logger.warning(f"DEBUG: 未找到 {self.game_version} 的预期哈希值")
            self.progress.emit(100)
            self.finished.emit(False, f"未找到 {self.game_version} 的预期哈希值", "")
            return
            
        if debug_mode:
            logger.debug(f"DEBUG: 开始验证补丁文件: {self.file_path}")
            logger.debug(f"DEBUG: 游戏版本: {self.game_version}")
            logger.debug(f"DEBUG: 预期哈希值: {expected_hash}")
            
        try:
            # 检查文件是否存在
            if not os.path.exists(self.file_path):
                if debug_mode:
                    logger.warning(f"DEBUG: 补丁文件不存在: {self.file_path}")
                self.progress.emit(100)
                self.finished.emit(False, f"补丁文件不存在: {self.file_path}", "")
                return
                
            # 检查文件大小
            file_size = os.path.getsize(self.file_path)
            if debug_mode:
                logger.debug(f"DEBUG: 补丁文件大小: {file_size} 字节")
                
            if file_size == 0:
                if debug_mode:
                    logger.warning(f"DEBUG: 补丁文件大小为0，无效文件")
                self.progress.emit(100)
                self.finished.emit(False, "补丁文件大小为0，无效文件", "")
                return
                
            # 创建临时目录用于解压文件
            with tempfile.TemporaryDirectory() as temp_dir:
                if debug_mode:
                    logger.debug(f"DEBUG: 创建临时目录: {temp_dir}")
                    
                # 发送进度信号 - 10%
                self.progress.emit(10)
                
                # 解压补丁文件
                try:
                    if debug_mode:
                        logger.debug(f"DEBUG: 开始解压文件: {self.file_path}")
                        
                    # 确定目标文件名
                    target_filename = None
                    if "Vol.1" in self.game_version:
                        target_filename = "adultsonly.xp3"
                    elif "Vol.2" in self.game_version:
                        target_filename = "adultsonly.xp3"
                    elif "Vol.3" in self.game_version:
                        target_filename = "update00.int"
                    elif "Vol.4" in self.game_version:
                        target_filename = "vol4adult.xp3"
                    elif "After" in self.game_version:
                        target_filename = "afteradult.xp3"
                    
                    if not target_filename:
                        if debug_mode:
                            logger.warning(f"DEBUG: 未知的游戏版本: {self.game_version}")
                        self.progress.emit(100)
                        self.finished.emit(False, f"未知的游戏版本: {self.game_version}", "")
                        return
                        
                    with py7zr.SevenZipFile(self.file_path, mode="r") as archive:
                        # 获取压缩包内文件列表
                        file_list = archive.getnames()
                        if debug_mode:
                            logger.debug(f"DEBUG: 压缩包内文件列表: {file_list}")
                            
                        # 查找目标文件
                        target_file_in_archive = None
                        for file_path in file_list:
                            if target_filename in file_path:
                                target_file_in_archive = file_path
                                break
                        
                        if not target_file_in_archive:
                            if debug_mode:
                                logger.warning(f"DEBUG: 在压缩包中未找到目标文件: {target_filename}")
                            # 尝试查找可能的替代文件
                            alternative_files = []
                            for file_path in file_list:
                                if file_path.endswith('.xp3') or file_path.endswith('.int'):
                                    alternative_files.append(file_path)
                            
                            if alternative_files:
                                if debug_mode:
                                    logger.debug(f"DEBUG: 找到可能的替代文件: {alternative_files}")
                                target_file_in_archive = alternative_files[0]
                            else:
                                # 如果找不到任何替代文件，解压全部文件
                                if debug_mode:
                                    logger.debug(f"DEBUG: 未找到任何替代文件，解压全部文件")
                                archive.extractall(path=temp_dir)
                                
                                # 尝试在解压后的目录中查找目标文件
                                for root, dirs, files in os.walk(temp_dir):
                                    for file in files:
                                        if file.endswith('.xp3') or file.endswith('.int'):
                                            patch_file = os.path.join(root, file)
                                            if debug_mode:
                                                logger.debug(f"DEBUG: 找到可能的补丁文件: {patch_file}")
                                            break
                                    if patch_file:
                                        break
                                
                                if not patch_file:
                                    if debug_mode:
                                        logger.warning(f"DEBUG: 未找到解压后的补丁文件")
                                    self.progress.emit(100)
                                    self.finished.emit(False, "未找到解压后的补丁文件", "")
                                    return
                        else:
                            # 只解压目标文件
                            if debug_mode:
                                logger.debug(f"DEBUG: 解压目标文件: {target_file_in_archive}")
                            archive.extract(path=temp_dir, targets=[target_file_in_archive])
                            patch_file = os.path.join(temp_dir, target_file_in_archive)
                        
                        # 发送进度信号 - 50%
                        self.progress.emit(50)
                        
                        # 如果还没有设置patch_file，尝试查找
                        if not 'patch_file' in locals():
                            if "Vol.1" in self.game_version:
                                patch_file = os.path.join(temp_dir, "vol.1", "adultsonly.xp3")
                            elif "Vol.2" in self.game_version:
                                patch_file = os.path.join(temp_dir, "vol.2", "adultsonly.xp3")
                            elif "Vol.3" in self.game_version:
                                patch_file = os.path.join(temp_dir, "vol.3", "update00.int")
                            elif "Vol.4" in self.game_version:
                                patch_file = os.path.join(temp_dir, "vol.4", "vol4adult.xp3")
                            elif "After" in self.game_version:
                                patch_file = os.path.join(temp_dir, "after", "afteradult.xp3")
                        
                        if not os.path.exists(patch_file):
                            if debug_mode:
                                logger.warning(f"DEBUG: 未找到解压后的补丁文件: {patch_file}")
                                # 尝试查找可能的替代文件
                                alternative_files = []
                                for root, dirs, files in os.walk(temp_dir):
                                    for file in files:
                                        if file.endswith('.xp3') or file.endswith('.int'):
                                            alternative_files.append(os.path.join(root, file))
                                if alternative_files:
                                    logger.debug(f"DEBUG: 找到可能的替代文件: {alternative_files}")
                                    patch_file = alternative_files[0]
                                else:
                                    # 检查解压目录结构
                                    logger.debug(f"DEBUG: 检查解压目录结构:")
                                    for root, dirs, files in os.walk(temp_dir):
                                        logger.debug(f"DEBUG: 目录: {root}")
                                        logger.debug(f"DEBUG: 子目录: {dirs}")
                                        logger.debug(f"DEBUG: 文件: {files}")
                            
                            if not os.path.exists(patch_file):
                                self.progress.emit(100)
                                self.finished.emit(False, f"未找到解压后的补丁文件", "")
                                return
                        
                        # 发送进度信号 - 70%
                        self.progress.emit(70)
                        
                        if debug_mode:
                            logger.debug(f"DEBUG: 找到解压后的补丁文件: {patch_file}")
                            
                        # 计算补丁文件哈希值
                        try:
                            # 读取文件内容并计算哈希值，同时更新进度
                            file_size = os.path.getsize(patch_file)
                            
                            # 根据文件大小动态调整块大小
                            # 文件越大，块越大，最大256MB
                            chunk_size = min(256 * 1024 * 1024, max(16 * 1024 * 1024, file_size // 20))
                            if debug_mode:
                                logger.debug(f"DEBUG: 文件大小: {file_size} 字节, 使用块大小: {chunk_size // (1024 * 1024)}MB")
                                
                            hash_obj = hashlib.sha256()
                            
                            with open(patch_file, "rb") as f:
                                bytes_read = 0
                                start_time = time.time()
                                last_progress_time = start_time
                                
                                while True:
                                    if self.isInterruptionRequested():
                                        break
                                    # 检查超时
                                    if check_timeout():
                                        logger.error(f"哈希计算超时，强制终止")
                                        self.progress.emit(100)
                                        self.finished.emit(
                                            False, 
                                            f"{self.game_version} 哈希计算超时，已超过 {timeout_minutes} 分钟。请考虑跳过哈希校验或稍后再试。", 
                                            ""
                                        )
                                        return
                                    chunk = f.read(chunk_size)
                                    if not chunk:
                                        break
                                    hash_obj.update(chunk)
                                    bytes_read += len(chunk)
                                    
                                    # 计算进度 (70-95%)
                                    progress = 70 + int(25 * bytes_read / file_size)
                                    self.progress.emit(min(95, progress))
                                    
                                    # 每秒更新一次日志进度
                                    current_time = time.time()
                                    if debug_mode and current_time - last_progress_time >= 1.0:
                                        elapsed = current_time - start_time
                                        speed = bytes_read / (elapsed if elapsed > 0 else 1) / (1024 * 1024)  # MB/s
                                        percent = bytes_read / file_size * 100
                                        logger.debug(f"DEBUG: 哈希计算进度 - {percent:.1f}% - 已处理: {bytes_read/(1024*1024):.1f}MB/{file_size/(1024*1024):.1f}MB - 速度: {speed:.1f}MB/s")
                                        last_progress_time = current_time
                            
                            # 记录总用时
                            if debug_mode:
                                total_time = time.time() - start_time
                                logger.debug(f"DEBUG: 哈希计算完成，耗时: {total_time:.1f}秒，平均速度: {file_size/(total_time*1024*1024):.1f}MB/s")
                            
                            file_hash = hash_obj.hexdigest()
                            
                            # 比较哈希值
                            result = file_hash.lower() == expected_hash.lower()
                            
                            # 发送进度信号 - 100%
                            self.progress.emit(100)
                            
                            if debug_mode:
                                logger.debug(f"DEBUG: 补丁文件 {patch_file} 哈希值验证: {'成功' if result else '失败'}")
                                logger.debug(f"DEBUG: 预期哈希值: {expected_hash}")
                                logger.debug(f"DEBUG: 实际哈希值: {file_hash}")
                                
                            # 将验证结果和解压后的文件路径传递回去
                            # 注意：由于使用了临时目录，此路径在函数返回后将不再有效
                            # 但这里返回的路径只是用于标识验证成功，实际安装时会重新解压
                            self.finished.emit(result, "" if result else "补丁文件哈希验证失败，文件可能已损坏或被篡改", patch_file if result else "")
                        except Exception as e:
                            if debug_mode:
                                logger.error(f"DEBUG: 计算补丁文件哈希值失败: {e}")
                                logger.error(f"DEBUG: 错误类型: {type(e).__name__}")
                            self.progress.emit(100)
                            self.finished.emit(False, f"计算补丁文件哈希值失败: {str(e)}", "")
                except Exception as e:
                    if debug_mode:
                        logger.error(f"DEBUG: 解压补丁文件失败: {e}")
                        logger.error(f"DEBUG: 错误类型: {type(e).__name__}")
                        logger.error(f"DEBUG: 错误堆栈: {traceback.format_exc()}")
                    self.progress.emit(100)
                    self.finished.emit(False, f"解压补丁文件失败: {str(e)}", "")
                    return
        except Exception as e:
            if debug_mode:
                logger.error(f"DEBUG: 验证补丁哈希值失败: {e}")
                logger.error(f"DEBUG: 错误类型: {type(e).__name__}")
                logger.error(f"DEBUG: 错误堆栈: {traceback.format_exc()}" )
            self.progress.emit(100)
            self.finished.emit(False, f"验证补丁哈希值失败: {str(e)}", "") 