import os
import hashlib
import py7zr
import tempfile
import traceback
from PySide6.QtCore import QThread, Signal
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
        
        # 尝试检测是否处于调试模式
        if self.main_window and hasattr(self.main_window, 'debug_manager'):
            debug_mode = self.main_window.debug_manager._is_debug_mode()
            
        if self.mode == "pre":
            status_copy = self.installed_status.copy()
            
            for game_version, install_path in self.install_paths.items():
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
                        
                    with open(install_path, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    
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
                if not os.path.exists(install_path):
                    if debug_mode:
                        logger.debug(f"DEBUG: 哈希后检查 - {game_version} 补丁文件不存在: {install_path}")
                    continue
                    
                try:
                    expected_hash = self.plugin_hash.get(game_version, "")
                    if not expected_hash:
                        if debug_mode:
                            logger.debug(f"DEBUG: 哈希后检查 - {game_version} 没有预期哈希值，跳过哈希检查")
                        # 当没有预期哈希值时，跳过检查
                        continue
                        
                    with open(install_path, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    
                    if debug_mode:
                        logger.debug(f"DEBUG: 哈希后检查 - {game_version}")
                        logger.debug(f"DEBUG: 文件路径: {install_path}")
                        logger.debug(f"DEBUG: 预期哈希值: {expected_hash}")
                        logger.debug(f"DEBUG: 实际哈希值: {file_hash}")
                        logger.debug(f"DEBUG: 哈希匹配: {file_hash == expected_hash}")
                    
                    if file_hash != expected_hash:
                        result["passed"] = False
                        result["game"] = game_version
                        result["message"] = f"\n{game_version} 安装后的文件校验失败。\n\n文件可能已损坏或被篡改，请重新安装。\n"
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
    finished = Signal(bool, str)  # 完成信号，(成功/失败, 错误信息)
    
    def __init__(self, game_version, file_path, plugin_hash, main_window=None):
        """初始化离线哈希验证线程
        
        Args:
            game_version: 游戏版本名称
            file_path: 补丁压缩包文件路径
            plugin_hash: 插件哈希值字典
            main_window: 主窗口实例，用于访问UI和状态
        """
        super().__init__()
        self.game_version = game_version
        self.file_path = file_path
        self.plugin_hash = plugin_hash
        self.main_window = main_window
        
    def run(self):
        """运行线程"""
        debug_mode = False
        
        # 尝试检测是否处于调试模式
        if self.main_window and hasattr(self.main_window, 'debug_manager'):
            debug_mode = self.main_window.debug_manager._is_debug_mode()
            
        # 获取预期的哈希值
        expected_hash = self.plugin_hash.get(self.game_version, "")
        
        if not expected_hash:
            logger.warning(f"DEBUG: 未找到 {self.game_version} 的预期哈希值")
            self.finished.emit(False, f"未找到 {self.game_version} 的预期哈希值")
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
                self.finished.emit(False, f"补丁文件不存在: {self.file_path}")
                return
                
            # 检查文件大小
            file_size = os.path.getsize(self.file_path)
            if debug_mode:
                logger.debug(f"DEBUG: 补丁文件大小: {file_size} 字节")
                
            if file_size == 0:
                if debug_mode:
                    logger.warning(f"DEBUG: 补丁文件大小为0，无效文件")
                self.finished.emit(False, "补丁文件大小为0，无效文件")
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
                        
                    with py7zr.SevenZipFile(self.file_path, mode="r") as archive:
                        # 获取压缩包内文件列表
                        file_list = archive.getnames()
                        if debug_mode:
                            logger.debug(f"DEBUG: 压缩包内文件列表: {file_list}")
                            
                        # 解压所有文件
                        archive.extractall(path=temp_dir)
                        
                        if debug_mode:
                            logger.debug(f"DEBUG: 解压完成")
                            # 列出解压后的文件
                            extracted_files = []
                            for root, dirs, files in os.walk(temp_dir):
                                for file in files:
                                    extracted_files.append(os.path.join(root, file))
                            logger.debug(f"DEBUG: 解压后的文件列表: {extracted_files}")
                except Exception as e:
                    if debug_mode:
                        logger.error(f"DEBUG: 解压补丁文件失败: {e}")
                        logger.error(f"DEBUG: 错误类型: {type(e).__name__}")
                        logger.error(f"DEBUG: 错误堆栈: {traceback.format_exc()}")
                    self.finished.emit(False, f"解压补丁文件失败: {str(e)}")
                    return
                
                # 发送进度信号 - 50%
                self.progress.emit(50)
                
                # 获取补丁文件路径
                patch_file = None
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
                
                if not patch_file or not os.path.exists(patch_file):
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
                        
                        # 检查解压目录结构
                        logger.debug(f"DEBUG: 检查解压目录结构:")
                        for root, dirs, files in os.walk(temp_dir):
                            logger.debug(f"DEBUG: 目录: {root}")
                            logger.debug(f"DEBUG: 子目录: {dirs}")
                            logger.debug(f"DEBUG: 文件: {files}")
                    self.finished.emit(False, f"未找到解压后的补丁文件")
                    return
                
                # 发送进度信号 - 70%
                self.progress.emit(70)
                
                if debug_mode:
                    logger.debug(f"DEBUG: 找到解压后的补丁文件: {patch_file}")
                    
                # 计算补丁文件哈希值
                try:
                    # 读取文件内容并计算哈希值，同时更新进度
                    file_size = os.path.getsize(patch_file)
                    chunk_size = 1024 * 1024  # 1MB
                    hash_obj = hashlib.sha256()
                    
                    with open(patch_file, "rb") as f:
                        bytes_read = 0
                        while chunk := f.read(chunk_size):
                            hash_obj.update(chunk)
                            bytes_read += len(chunk)
                            # 计算进度 (70-95%)
                            progress = 70 + int(25 * bytes_read / file_size)
                            self.progress.emit(min(95, progress))
                    
                    file_hash = hash_obj.hexdigest()
                    
                    # 比较哈希值
                    result = file_hash.lower() == expected_hash.lower()
                    
                    # 发送进度信号 - 100%
                    self.progress.emit(100)
                    
                    if debug_mode:
                        logger.debug(f"DEBUG: 补丁文件 {patch_file} 哈希值验证: {'成功' if result else '失败'}")
                        logger.debug(f"DEBUG: 预期哈希值: {expected_hash}")
                        logger.debug(f"DEBUG: 实际哈希值: {file_hash}")
                        
                    self.finished.emit(result, "" if result else "补丁文件哈希验证失败，文件可能已损坏或被篡改")
                except Exception as e:
                    if debug_mode:
                        logger.error(f"DEBUG: 计算补丁文件哈希值失败: {e}")
                        logger.error(f"DEBUG: 错误类型: {type(e).__name__}")
                    self.finished.emit(False, f"计算补丁文件哈希值失败: {str(e)}")
        except Exception as e:
            if debug_mode:
                logger.error(f"DEBUG: 验证补丁哈希值失败: {e}")
                logger.error(f"DEBUG: 错误类型: {type(e).__name__}")
                logger.error(f"DEBUG: 错误堆栈: {traceback.format_exc()}")
            self.finished.emit(False, f"验证补丁哈希值失败: {str(e)}") 