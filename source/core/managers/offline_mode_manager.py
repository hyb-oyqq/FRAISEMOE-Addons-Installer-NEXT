import os
import hashlib
import shutil
import tempfile
import py7zr
import traceback
from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

from config.config import PLUGIN, PLUGIN_HASH, GAME_INFO
from utils import msgbox_frame
from utils.logger import setup_logger

# 初始化logger
logger = setup_logger("offline_mode_manager")

class OfflineModeManager:
    """离线模式管理器，用于管理离线模式下的补丁安装和检测"""
    
    def __init__(self, main_window):
        """初始化离线模式管理器
        
        Args:
            main_window: 主窗口实例，用于访问UI和状态
        """
        self.main_window = main_window
        self.app_name = main_window.APP_NAME if hasattr(main_window, 'APP_NAME') else ""
        self.offline_patches = {}  # 存储离线补丁信息 {补丁名称: 文件路径}
        self.is_offline_mode = False
        self.installed_games = []  # 跟踪本次实际安装的游戏
        # 保持对哈希线程的引用，避免运行中被销毁
        self.hash_thread = None
        # 解压线程与进度窗口引用，避免运行中被销毁，且确保UI可更新
        self.extraction_thread = None
        self.extraction_progress_window = None
        
    def _is_debug_mode(self):
        """检查是否处于调试模式
        
        Returns:
            bool: 是否处于调试模式
        """
        try:
            if hasattr(self.main_window, 'debug_manager') and self.main_window.debug_manager:
                if hasattr(self.main_window.debug_manager, '_is_debug_mode'):
                    # 尝试直接从debug_manager获取状态
                    return self.main_window.debug_manager._is_debug_mode()
                elif hasattr(self.main_window, 'config'):
                    # 如果debug_manager还没准备好，尝试从配置中获取
                    return self.main_window.config.get('debug_mode', False)
            # 如果以上都不可行，返回False
            return False
        except Exception:
            # 捕获任何异常，默认返回False
            return False
        
    def scan_for_offline_patches(self, directory=None):
        """扫描指定目录（默认为软件所在目录）查找离线补丁文件
        
        Args:
            directory: 要扫描的目录，如果为None则使用软件所在目录
            
        Returns:
            dict: 找到的补丁文件 {补丁名称: 文件路径}
        """
        if directory is None:
            # 获取软件所在目录 - 直接使用最简单的方式
            try:
                import sys
                
                if getattr(sys, 'frozen', False):
                    # 如果是PyInstaller打包的环境，使用可执行文件所在目录
                    directory = os.path.dirname(sys.executable)
                else:
                    # 直接取当前工作目录
                    directory = os.getcwd()
                    
                    # 对于开发环境的特殊处理：
                    # 如果当前目录路径中包含'source'，则可能是在开发模式下从source目录运行
                    # 尝试找到项目根目录
                    if 'source' in directory:
                        # 尝试向上一级查找补丁文件
                        parent_dir = os.path.dirname(directory)
                        # 看看父目录是否存在补丁文件
                        potential_patches = ["vol.1.7z", "vol.2.7z", "vol.3.7z", "vol.4.7z", "after.7z"]
                        for patch_file in potential_patches:
                            if os.path.exists(os.path.join(parent_dir, patch_file)):
                                # 如果在父目录找到了补丁文件，使用父目录作为扫描目录
                                directory = parent_dir
                                break
                
                if self._is_debug_mode():
                    logger.debug(f"DEBUG: 使用目录 {directory} 扫描离线补丁文件")
                    current_dir = os.getcwd()
                    logger.debug(f"DEBUG: 当前工作目录: {current_dir}")
                    logger.debug(f"DEBUG: 是否为打包环境: {getattr(sys, 'frozen', False)}")
                    if getattr(sys, 'frozen', False):
                        logger.debug(f"DEBUG: 可执行文件路径: {sys.executable}")
            except Exception as e:
                # 如果出现异常，使用当前工作目录
                directory = os.getcwd()
                if self._is_debug_mode():
                    logger.debug(f"DEBUG: 路径计算出错，使用工作目录: {directory}, 错误: {e}")
            
        debug_mode = self._is_debug_mode()
        
        # 无论是否为调试模式，都记录扫描操作
        logger.info(f"扫描离线补丁文件，目录: {directory}")
            
        # 要查找的补丁文件名
        patch_files = ["vol.1.7z", "vol.2.7z", "vol.3.7z", "vol.4.7z", "after.7z"]
        
        # 尝试多个可能的目录位置，从指定目录开始，然后是其父目录
        search_dirs = [directory]
        
        # 添加可能的父目录
        current = directory
        for i in range(3):  # 最多向上查找3层目录
            parent = os.path.dirname(current)
            if parent and parent != current:  # 确保不是根目录
                search_dirs.append(parent)
                current = parent
            else:
                break

        # 添加工作目录（如果与指定目录不同）
        work_dir = os.getcwd()
        if work_dir not in search_dirs:
            search_dirs.append(work_dir)
            
        if debug_mode:
            logger.debug(f"DEBUG: 将在以下目录中查找补丁文件: {search_dirs}")
        
        found_patches = {}
        
        # 扫描所有可能的目录查找补丁文件
        try:
            # 首先尝试在指定目录查找
            for search_dir in search_dirs:
                if debug_mode:
                    logger.debug(f"DEBUG: 正在搜索目录: {search_dir}")
                    
                if not os.path.exists(search_dir):
                    if debug_mode:
                        logger.debug(f"DEBUG: 目录不存在，跳过: {search_dir}")
                    continue
                    
                for file in os.listdir(search_dir):
                    if file.lower() in patch_files:
                        file_path = os.path.join(search_dir, file)
                        if os.path.isfile(file_path):
                            patch_name = file.lower()
                            found_patches[patch_name] = file_path
                            # 无论是否为调试模式，都记录找到的补丁文件
                            logger.info(f"找到离线补丁文件: {patch_name} 路径: {file_path}")
                            if debug_mode:
                                logger.debug(f"DEBUG: 找到离线补丁文件: {patch_name} 路径: {file_path}")
                
                # 如果在当前目录找到了补丁文件，停止继续查找
                if found_patches:
                    if debug_mode:
                        logger.debug(f"DEBUG: 在目录 {search_dir} 找到补丁文件，停止继续搜索")
                    break
                    
        except Exception as e:
            logger.error(f"扫描目录时出错: {str(e)}")
                        
        self.offline_patches = found_patches
        
        # 记录扫描结果
        if found_patches:
            logger.info(f"共找到 {len(found_patches)} 个离线补丁文件: {list(found_patches.keys())}")
        else:
            logger.info("未找到任何离线补丁文件")
            
        return found_patches
        
    def has_offline_patches(self):
        """检查是否有可用的离线补丁文件
        
        Returns:
            bool: 是否有可用的离线补丁
        """
        if not self.offline_patches:
            self.scan_for_offline_patches()
            
        return len(self.offline_patches) > 0
        
    def set_offline_mode(self, enabled):
        """设置离线模式状态
        
        Args:
            enabled: 是否启用离线模式
            
        Returns:
            bool: 是否成功设置离线模式
        """
        debug_mode = self._is_debug_mode()
        
        if enabled:
            # 检查是否有离线补丁文件
            if not self.has_offline_patches() and not debug_mode:
                msgbox_frame(
                    f"离线模式错误 - {self.app_name}",
                    "\n未找到任何离线补丁文件，无法启用离线模式。\n\n请将补丁文件放置在软件所在目录后再尝试。\n",
                    QMessageBox.StandardButton.Ok
                ).exec()
                logger.warning("尝试启用离线模式失败：未找到任何离线补丁文件")
                return False
                
            if debug_mode:
                logger.debug("DEBUG: 已启用离线模式（调试模式下允许强制启用）")
                
        self.is_offline_mode = enabled
        
        # 更新窗口标题
        if hasattr(self.main_window, 'setWindowTitle'):
            from config.config import APP_NAME, APP_VERSION
            mode_indicator = "[离线模式]" if enabled else "[在线模式]"
            self.main_window.setWindowTitle(f"{APP_NAME} v{APP_VERSION} {mode_indicator}")
            
            # 同时更新UI中的标题标签
            if hasattr(self.main_window, 'ui') and hasattr(self.main_window.ui, 'title_label'):
                self.main_window.ui.title_label.setText(f"{APP_NAME} v{APP_VERSION} {mode_indicator}")
                
        # 同步更新UI菜单中的模式选择状态
        if hasattr(self.main_window, 'ui_manager'):
            ui_manager = self.main_window.ui_manager
            if hasattr(ui_manager, 'online_mode_action') and hasattr(ui_manager, 'offline_mode_action'):
                ui_manager.online_mode_action.setChecked(not enabled)
                ui_manager.offline_mode_action.setChecked(enabled)
        
        # 无论是否为调试模式，都记录离线模式状态变化
        logger.info(f"离线模式已{'启用' if enabled else '禁用'}")
        if debug_mode:
            logger.debug(f"DEBUG: 离线模式已{'启用' if enabled else '禁用'}")
            
        return True
        
    def get_offline_patch_path(self, game_version):
        """根据游戏版本获取对应的离线补丁文件路径
        
        Args:
            game_version: 游戏版本名称，如"NEKOPARA Vol.1"
            
        Returns:
            str: 离线补丁文件路径，如果没有找到则返回None
        """
        # 确保已扫描过补丁文件
        if not self.offline_patches:
            self.scan_for_offline_patches()
            
        # 根据游戏版本获取对应的补丁文件名
        patch_file = None
        
        if "Vol.1" in game_version:
            patch_file = "vol.1.7z"
        elif "Vol.2" in game_version:
            patch_file = "vol.2.7z"
        elif "Vol.3" in game_version:
            patch_file = "vol.3.7z"
        elif "Vol.4" in game_version:
            patch_file = "vol.4.7z"
        elif "After" in game_version:
            patch_file = "after.7z"
            
        # 检查是否有对应的补丁文件
        if patch_file and patch_file in self.offline_patches:
            return self.offline_patches[patch_file]
            
        return None
        
    def prepare_offline_patch(self, game_version, target_path):
        """准备离线补丁文件，复制到缓存目录
        
        Args:
            game_version: 游戏版本名称
            target_path: 目标路径（通常是缓存目录中的路径）
            
        Returns:
            bool: 是否成功准备补丁文件
        """
        source_path = self.get_offline_patch_path(game_version)
        
        if not source_path:
            return False
            
        debug_mode = self._is_debug_mode()
        
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # 复制文件
            shutil.copy2(source_path, target_path)
            
            if debug_mode:
                logger.debug(f"DEBUG: 已复制离线补丁文件 {source_path} 到 {target_path}")
                
            return True
        except Exception as e:
            if debug_mode:
                logger.error(f"DEBUG: 复制离线补丁文件失败: {e}")
            return False
            
    def verify_patch_hash(self, game_version, file_path):
        """验证补丁文件的哈希值，使用patch_detector模块
        
        Args:
            game_version: 游戏版本名称
            file_path: 补丁压缩包文件路径
            
        Returns:
            bool: 哈希值是否匹配
        """
        debug_mode = self._is_debug_mode()
        
        if debug_mode:
            logger.debug(f"DEBUG: 开始验证补丁文件哈希: {file_path}")
            
        # 创建进度对话框
        from utils.helpers import ProgressHashVerifyDialog
        from config.config import PLUGIN_HASH
        from workers.hash_thread import OfflineHashVerifyThread
        
        # 创建并显示进度对话框
        progress_dialog = ProgressHashVerifyDialog(
            f"验证补丁文件 - {self.app_name}",
            f"正在验证 {game_version} 的补丁文件完整性...",
            self.main_window
        )
        
        # 创建哈希验证线程
        hash_thread = OfflineHashVerifyThread(game_version, file_path, PLUGIN_HASH, self.main_window)
        
        # 连接信号
        hash_thread.progress.connect(progress_dialog.update_progress)
        hash_thread.finished.connect(lambda result, error, extracted_path: self._on_hash_verify_finished(result, error, extracted_path, progress_dialog))
        
        # 启动线程
        hash_thread.start()
        
        # 显示对话框，阻塞直到对话框关闭
        result = progress_dialog.exec()
        
        # 如果用户取消了验证，停止线程
        if result == ProgressHashVerifyDialog.Rejected and hash_thread.isRunning():
            if debug_mode:
                logger.debug(f"DEBUG: 用户取消了哈希验证")
            hash_thread.terminate()
            hash_thread.wait()
            return False
            
        # 返回对话框中存储的验证结果
        return hasattr(progress_dialog, 'hash_result') and progress_dialog.hash_result
        
    def _on_hash_verify_finished(self, result, error, extracted_path, dialog):
        """哈希验证线程完成后的回调
        
        Args:
            result: 验证结果
            error: 错误信息
            extracted_path: 解压后的补丁文件路径，如果哈希验证成功则包含此路径
            dialog: 进度对话框
        """
        debug_mode = self._is_debug_mode()
        
        # 存储结果到对话框，以便在exec()返回后获取
        dialog.hash_result = result
        
        if result:
            if debug_mode:
                logger.debug(f"DEBUG: 哈希验证成功")
                if extracted_path:
                    logger.debug(f"DEBUG: 解压后的补丁文件路径: {extracted_path}")
            dialog.set_status("验证成功")
            # 短暂延时后关闭对话框
            QTimer.singleShot(500, dialog.accept)
        else:
            if debug_mode:
                logger.debug(f"DEBUG: 哈希验证失败: {error}")
            dialog.set_status(f"验证失败: {error}")
            dialog.set_message("补丁文件验证失败，可能已损坏或被篡改。")
            # 将取消按钮改为关闭按钮
            dialog.cancel_button.setText("关闭")
            # 不自动关闭，让用户查看错误信息
            
    def _on_offline_install_hash_finished(self, result, error, extracted_path, dialog, game_version, _7z_path, game_folder, plugin_path, install_tasks):
        """离线安装哈希验证线程完成后的回调
        
        Args:
            result: 验证结果
            error: 错误信息
            extracted_path: 解压后的补丁文件路径
            dialog: 进度对话框
            game_version: 游戏版本
            _7z_path: 7z文件路径
            game_folder: 游戏文件夹路径
            plugin_path: 插件路径
            install_tasks: 剩余的安装任务列表
        """
        debug_mode = self._is_debug_mode()
        
        # 导入所需模块
        from config.config import GAME_INFO, PLUGIN
        
        # 存储结果到对话框，以便在exec()返回后获取
        dialog.hash_result = result
        
        # 关闭哈希验证窗口
        self.main_window.close_hash_msg_box()
            
        if not result:
            # 哈希验证失败
            if debug_mode:
                logger.warning(f"DEBUG: 补丁文件哈希验证失败: {error}")
                
            # 显示错误消息
            msgbox_frame(
                f"哈希验证失败 - {self.app_name}",
                f"\n{game_version} 的补丁文件哈希验证失败，可能已损坏或被篡改。\n\n跳过此游戏的安装。\n",
                QMessageBox.StandardButton.Ok
            ).exec()
            
            # 继续下一个任务
            self.process_next_offline_install_task(install_tasks)
            return
            
        # 哈希验证成功，直接进行安装
        if debug_mode:
            logger.debug(f"DEBUG: 哈希验证成功，开始安装")
                
        # 显示安装进度窗口
        self.main_window.hash_msg_box = self.main_window.hash_manager.hash_pop_window(check_type="offline_installation", is_offline=True)
        
        try:
            # 确保游戏目录存在
            os.makedirs(game_folder, exist_ok=True)
            
            # 根据游戏版本确定目标文件名
            target_filename = None
            if "Vol.1" in game_version:
                target_filename = "adultsonly.xp3"
            elif "Vol.2" in game_version:
                target_filename = "adultsonly.xp3"
            elif "Vol.3" in game_version:
                target_filename = "update00.int"
            elif "Vol.4" in game_version:
                target_filename = "vol4adult.xp3"
            elif "After" in game_version:
                target_filename = "afteradult.xp3"
                
            if not target_filename:
                raise ValueError(f"未知的游戏版本: {game_version}")
            
            # 直接解压文件到游戏目录
            import py7zr
            
            if debug_mode:
                logger.debug(f"DEBUG: 直接解压文件 {_7z_path} 到游戏目录 {game_folder}")
            
            # 解压文件
            with py7zr.SevenZipFile(_7z_path, mode="r") as archive:
                # 获取压缩包内的文件列表
                file_list = archive.getnames()
                if debug_mode:
                    logger.debug(f"DEBUG: 压缩包内文件列表: {file_list}")
                
                # 解析压缩包内的文件结构
                target_file_in_archive = None
                for file_path in file_list:
                    if target_filename in file_path:
                        target_file_in_archive = file_path
                        break
                
                if not target_file_in_archive:
                    if debug_mode:
                        logger.warning(f"DEBUG: 在压缩包中未找到目标文件 {target_filename}")
                    raise FileNotFoundError(f"在压缩包中未找到目标文件 {target_filename}")
                
                # 准备解压特定文件到游戏目录
                target_path = os.path.join(game_folder, target_filename)
                
                # 创建一个临时目录用于解压单个文件
                with tempfile.TemporaryDirectory() as temp_dir:
                    # 解压特定文件到临时目录
                    archive.extract(path=temp_dir, targets=[target_file_in_archive])
                    
                    # 找到解压后的文件
                    extracted_file_path = os.path.join(temp_dir, target_file_in_archive)
                    
                    # 复制到目标位置
                    shutil.copy2(extracted_file_path, target_path)
                    
                    if debug_mode:
                        logger.debug(f"DEBUG: 已解压并复制文件到 {target_path}")
                    
                    # 对于NEKOPARA After，还需要复制签名文件
                    if game_version == "NEKOPARA After":
                        sig_filename = f"{target_filename}.sig"
                        sig_file_in_archive = None
                        
                        # 查找签名文件
                        for file_path in file_list:
                            if sig_filename in file_path:
                                sig_file_in_archive = file_path
                                break
                        
                        if sig_file_in_archive:
                            # 解压签名文件
                            archive.extract(path=temp_dir, targets=[sig_file_in_archive])
                            extracted_sig_path = os.path.join(temp_dir, sig_file_in_archive)
                            sig_target = os.path.join(game_folder, sig_filename)
                            shutil.copy2(extracted_sig_path, sig_target)
                            
                            if debug_mode:
                                logger.debug(f"DEBUG: 已解压并复制签名文件到 {sig_target}")
                        else:
                            if debug_mode:
                                logger.warning(f"DEBUG: 未找到签名文件 {sig_filename}")
            
            # 进行安装后的哈希校验
            self._perform_hash_check(game_version, install_tasks)
            
        except Exception as e:
            if debug_mode:
                logger.error(f"DEBUG: 安装补丁文件失败: {e}")
                import traceback
                logger.error(f"DEBUG: 错误堆栈: {traceback.format_exc()}")
                
            # 关闭安装进度窗口
            self.main_window.close_hash_msg_box()
                
            # 显示错误消息
            msgbox_frame(
                f"安装错误 - {self.app_name}",
                f"\n{game_version} 的安装过程中发生错误: {str(e)}\n\n跳过此游戏的安装。\n",
                QMessageBox.StandardButton.Ok
            ).exec()
            
            # 继续下一个任务
            self.process_next_offline_install_task(install_tasks)
            
    def _perform_hash_check(self, game_version, install_tasks):
        """安装完成后进行哈希校验
        
        Args:
            game_version: 游戏版本
            install_tasks: 剩余的安装任务列表
        """
        debug_mode = self._is_debug_mode()
        
        # 导入所需模块
        from config.config import GAME_INFO, PLUGIN_HASH
        from workers.hash_thread import HashThread
        
        # 获取安装路径
        install_paths = {}
        game_dirs = self.main_window.game_detector.identify_game_directories_improved(
            self.main_window.download_manager.selected_folder
        )
        
        for game, info in GAME_INFO.items():
            if game in game_dirs and game == game_version:
                game_dir = game_dirs[game]
                install_path = os.path.join(game_dir, os.path.basename(info["install_path"]))
                install_paths[game] = install_path
                break
        
        if not install_paths:
            # 如果找不到安装路径，直接认为安装成功
            logger.warning(f"未找到 {game_version} 的安装路径，跳过哈希校验")
            self.main_window.installed_status[game_version] = True
            
            # 添加到已安装游戏列表
            if game_version not in self.installed_games:
                self.installed_games.append(game_version)
                
            # 关闭安装进度窗口
            self.main_window.close_hash_msg_box()
                
            # 继续下一个任务
            self.process_next_offline_install_task(install_tasks)
            return
            
        # 关闭可能存在的哈希校验窗口，然后创建新窗口
        self.main_window.close_hash_msg_box()
        
        # 显示哈希校验窗口
        self.main_window.hash_msg_box = self.main_window.hash_manager.hash_pop_window(check_type="post", is_offline=True)
        
        # 直接创建并启动哈希线程进行校验，而不是通过主窗口
        hash_thread = HashThread(
            "after", 
            install_paths, 
            PLUGIN_HASH, 
            self.main_window.installed_status,
            self.main_window
        )
        hash_thread.after_finished.connect(
            lambda result: self._on_hash_check_finished(result, game_version, install_tasks)
        )
        
        # 保存引用以便后续使用
        self.hash_thread = hash_thread
        try:
            self.hash_thread.finished.connect(lambda: setattr(self, 'hash_thread', None))
        except Exception:
            pass
        hash_thread.start()
        
    def _on_hash_check_finished(self, result, game_version, install_tasks):
        """哈希校验完成后的处理
        
        Args:
            result: 校验结果，包含通过状态、游戏版本和消息
            game_version: 游戏版本
            install_tasks: 剩余的安装任务列表
        """
        debug_mode = self._is_debug_mode()
        
        # 关闭哈希检查窗口
        self.main_window.close_hash_msg_box()
            
        if not result["passed"]:
            # 记录校验失败信息
            logger.error(f"===== {game_version} 哈希校验失败 =====")
            logger.error(f"校验失败消息: {result.get('message', '无错误消息')}")
            
            # 校验失败，删除已解压的文件并提示重新安装
            error_message = result["message"]
            
            # 获取安装路径
            install_path = None
            game_dirs = self.main_window.game_detector.identify_game_directories_improved(
                self.main_window.download_manager.selected_folder
            )
            
            from config.config import GAME_INFO
            if game_version in game_dirs and game_version in GAME_INFO:
                game_dir = game_dirs[game_version]
                install_path = os.path.join(game_dir, os.path.basename(GAME_INFO[game_version]["install_path"]))
                logger.info(f"找到安装路径: {install_path}")
                
                # 记录安装路径的文件信息
                if os.path.exists(install_path):
                    file_size = os.path.getsize(install_path)
                    logger.info(f"文件存在，大小: {file_size} 字节")
                    
                    # 检查是否为NEKOPARA After，记录签名文件信息
                    if game_version == "NEKOPARA After":
                        sig_path = f"{install_path}.sig"
                        if os.path.exists(sig_path):
                            sig_size = os.path.getsize(sig_path)
                            logger.info(f"签名文件存在: {sig_path}, 大小: {sig_size} 字节")
                        else:
                            logger.info(f"签名文件不存在: {sig_path}")
                else:
                    logger.warning(f"文件不存在: {install_path}")
            else:
                logger.warning(f"未找到 {game_version} 的安装路径")
            
            # 如果找到安装路径，尝试删除已解压的文件
            if install_path and os.path.exists(install_path):
                try:
                    os.remove(install_path)
                    logger.info(f"已删除校验失败的文件: {install_path}")
                    
                    # 检查是否为NEKOPARA After，同时删除签名文件
                    if game_version == "NEKOPARA After":
                        sig_path = f"{install_path}.sig"
                        if os.path.exists(sig_path):
                            os.remove(sig_path)
                            logger.info(f"已删除签名文件: {sig_path}")
                except Exception as e:
                    logger.error(f"删除文件失败: {e}")
            
            # 显示错误消息
            msgbox_frame(
                f"校验失败 - {self.app_name}",
                f"{error_message}\n\n跳过此游戏的安装。",
                QMessageBox.StandardButton.Ok
            ).exec()
            
            # 更新安装状态
            self.main_window.installed_status[game_version] = False
        else:
            # 校验通过，更新安装状态
            self.main_window.installed_status[game_version] = True
            logger.info(f"===== {game_version} 哈希校验通过 =====")
            
            # 添加到已安装游戏列表
            if game_version not in self.installed_games:
                self.installed_games.append(game_version)
                
            # 显示安装成功消息
            if debug_mode:
                logger.debug(f"DEBUG: {game_version} 安装成功并通过哈希校验")
        
        # 继续处理下一个任务
        self.process_next_offline_install_task(install_tasks)
        
    def _on_extraction_finished_with_hash_check(self, success, error_message, game_version, install_tasks):
        """解压完成后进行哈希校验（后台线程回调）"""
        # 关闭解压进度窗口
        try:
            if self.extraction_progress_window and self.extraction_progress_window.isVisible():
                self.extraction_progress_window.close()
        except Exception:
            pass
        self.extraction_progress_window = None
        
        # 清理线程引用
        self.extraction_thread = None
        
        if not success:
            # 解压失败，提示并继续下一个任务
            msgbox_frame(
                f"安装错误 - {self.app_name}",
                error_message or f"\n{game_version} 的安装过程中发生错误。\n",
                QMessageBox.StandardButton.Ok
            ).exec()
            self.process_next_offline_install_task(install_tasks)
            return
        
        # 解压成功，进入安装后哈希校验
        self._perform_hash_check(game_version, install_tasks)
        
    def on_extraction_thread_finished(self, success, error_message, game_version, install_tasks):
        """解压线程完成后的处理（兼容旧版本）
        
        Args:
            success: 是否解压成功
            error_message: 错误信息
            game_version: 游戏版本
            install_tasks: 剩余的安装任务列表
        """
        # 这个方法已不再使用，但为了兼容性，我们直接处理下一个任务
        if success:
            # 更新安装状态
            self.main_window.installed_status[game_version] = True
            
            # 添加到已安装游戏列表
            if game_version not in self.installed_games:
                self.installed_games.append(game_version)
        else:
            # 更新安装状态
            self.main_window.installed_status[game_version] = False
            
            # 显示错误消息
            debug_mode = self._is_debug_mode()
            if debug_mode:
                logger.error(f"DEBUG: 解压失败: {error_message}")
                
        # 继续下一个任务
        self.process_next_offline_install_task(install_tasks)
            
    def install_offline_patches(self, selected_games):
        """直接安装离线补丁，完全绕过下载模块
        
        Args:
            selected_games: 用户选择安装的游戏列表
            
        Returns:
            bool: 是否成功启动安装流程
        """
        debug_mode = self._is_debug_mode()
        
        if debug_mode:
            logger.debug(f"DEBUG: 开始离线安装流程，选择的游戏: {selected_games}")
            
        if not self.is_in_offline_mode():
            if debug_mode:
                logger.warning("DEBUG: 当前不是离线模式，无法使用离线安装")
            return False
            
        # 确保已扫描过补丁文件
        if not self.offline_patches:
            self.scan_for_offline_patches()
            
        if not self.offline_patches:
            if debug_mode:
                logger.warning("DEBUG: 未找到任何离线补丁文件")
            msgbox_frame(
                f"离线安装错误 - {self.app_name}",
                "\n未找到任何离线补丁文件，无法进行离线安装。\n\n请将补丁文件放置在软件所在目录后再尝试。\n",
                QMessageBox.StandardButton.Ok
            ).exec()
            return False
            
        # 获取游戏目录
        game_dirs = self.main_window.game_detector.identify_game_directories_improved(
            self.main_window.download_manager.selected_folder
        )
        
        if not game_dirs:
            if debug_mode:
                logger.warning("DEBUG: 未识别到任何游戏目录")
            return False
            
        self.main_window.setEnabled(False)
        
        # 重置已安装游戏列表
        self.installed_games = []
        
        # 设置到主窗口，供结果显示使用
        self.main_window.download_queue_history = selected_games
        
        # 记录未找到离线补丁文件的游戏
        self.missing_offline_patches = []
            
        # 创建安装任务列表
        install_tasks = []
        for game_version in selected_games:
            # 获取离线补丁文件路径
            patch_file = self.get_offline_patch_path(game_version)
            if not patch_file:
                if debug_mode:
                    logger.warning(f"DEBUG: 未找到 {game_version} 的离线补丁文件，跳过")
                # 记录未找到离线补丁文件的游戏
                self.missing_offline_patches.append(game_version)
                continue
                
            # 获取游戏目录
            game_folder = game_dirs.get(game_version)
            if not game_folder:
                if debug_mode:
                    logger.warning(f"DEBUG: 未找到 {game_version} 的游戏目录，跳过")
                continue
                
            # 获取目标路径
            if "Vol.1" in game_version:
                _7z_path = os.path.join(PLUGIN, "vol.1.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
            elif "Vol.2" in game_version:
                _7z_path = os.path.join(PLUGIN, "vol.2.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
            elif "Vol.3" in game_version:
                _7z_path = os.path.join(PLUGIN, "vol.3.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
            elif "Vol.4" in game_version:
                _7z_path = os.path.join(PLUGIN, "vol.4.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
            elif "After" in game_version:
                _7z_path = os.path.join(PLUGIN, "after.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
            else:
                if debug_mode:
                    logger.warning(f"DEBUG: {game_version} 不是支持的游戏版本，跳过")
                continue
                
            # 添加到安装任务列表
            install_tasks.append((patch_file, game_folder, game_version, _7z_path, plugin_path))
        
        # 开始执行第一个安装任务
        if install_tasks:
            if debug_mode:
                logger.info(f"DEBUG: 开始离线安装流程，安装游戏数量: {len(install_tasks)}")
            self.process_next_offline_install_task(install_tasks)
            return True
        else:
            if debug_mode:
                logger.warning("DEBUG: 没有可安装的游戏，安装流程结束")
                
            # 如果没有找到任何可安装的游戏，显示一般消息
            msgbox_frame(
                f"离线安装信息 - {self.app_name}",
                "\n没有可安装的游戏或未找到对应的离线补丁文件。\n",
                QMessageBox.StandardButton.Ok
            ).exec()
            self.main_window.setEnabled(True)
            self.main_window.ui.start_install_text.setText("开始安装")
            
        return True
        
    def _start_online_download(self, games_to_download):
        """启动在线下载流程
        
        Args:
            games_to_download: 要下载的游戏列表
        """
        debug_mode = self._is_debug_mode()
        if debug_mode:
            logger.debug(f"DEBUG: 启动在线下载流程，游戏列表: {games_to_download}")
        
        # 确保下载管理器已初始化
        if hasattr(self.main_window, 'download_manager'):
            # 使用直接下载方法，绕过补丁判断
            self.main_window.download_manager.direct_download_action(games_to_download)
        else:
            if debug_mode:
                logger.error("DEBUG: 下载管理器未初始化，无法启动下载流程")
            # 显示错误消息
            msgbox_frame(
                f"错误 - {self.app_name}",
                "\n下载管理器未初始化，无法启动下载流程。\n",
                QMessageBox.StandardButton.Ok
            ).exec()
            
    def process_next_offline_install_task(self, install_tasks):
        """处理下一个离线安装任务
        
        Args:
            install_tasks: 安装任务列表，每个任务是一个元组 (patch_file, game_folder, game_version, _7z_path, plugin_path)
        """
        debug_mode = self._is_debug_mode()
        
        if not install_tasks:
            # 所有任务完成，进行后检查
            if debug_mode:
                logger.info("DEBUG: 所有离线安装任务完成，进行后检查")
                
            # 使用patch_detector进行安装后哈希比较
            self.main_window.patch_detector.after_hash_compare()
            
            # 检查是否有未找到离线补丁文件的游戏
            if hasattr(self, 'missing_offline_patches') and self.missing_offline_patches:
                if debug_mode:
                    logger.debug(f"DEBUG: 有未找到离线补丁文件的游戏: {self.missing_offline_patches}")
                
                # 先显示已安装的结果
                if self.installed_games:
                    installed_msg = f"已成功安装以下补丁：\n\n{chr(10).join(self.installed_games)}\n\n"
                else:
                    installed_msg = ""
                
                # 在安装完成后询问用户是否切换到在线模式
                self._show_missing_patches_dialog(installed_msg)
            else:
                # 恢复UI状态
                self.main_window.setEnabled(True)
                self.main_window.ui.start_install_text.setText("开始安装")
                
            return
            
        # 获取下一个任务
        patch_file, game_folder, game_version, _7z_path, plugin_path = install_tasks.pop(0)
        
        if debug_mode:
            logger.debug(f"DEBUG: 处理离线安装任务: {game_version}")
            logger.debug(f"DEBUG: 补丁文件: {patch_file}")
            logger.debug(f"DEBUG: 游戏目录: {game_folder}")
            
        # 使用后台线程进行解压，避免阻塞UI
        try:
            # 确保游戏目录存在
            os.makedirs(game_folder, exist_ok=True)

            # 创建非阻塞的解压进度窗口
            self.extraction_progress_window = self.main_window.create_extraction_progress_window()
            try:
                self.extraction_progress_window.show()
                QtWidgets.QApplication.processEvents()
            except Exception:
                pass

            # 启动解压线程
            self.extraction_thread = self.main_window.create_extraction_thread(
                patch_file, game_folder, plugin_path, game_version
            )

            # 连接进度更新到窗口控件
            if self.extraction_thread and self.extraction_progress_window:
                self.extraction_thread.progress.connect(
                    lambda percent, status: (
                        self.extraction_progress_window.progress_bar.setValue(percent),
                        self.extraction_progress_window.status_label.setText(status)
                    )
                )

            # 完成后进入哈希校验
            self.extraction_thread.finished.connect(
                lambda success, error, gv: self._on_extraction_finished_with_hash_check(success, error, gv, install_tasks)
            )

            # 线程结束时清理引用
            try:
                self.extraction_thread.finished.connect(lambda *_: setattr(self, 'extraction_thread', None))
            except Exception:
                pass

            self.extraction_thread.start()

        except Exception as e:
            if debug_mode:
                logger.error(f"DEBUG: 离线安装任务处理失败: {e}")
                logger.error(f"DEBUG: 错误堆栈: {traceback.format_exc()}")

            # 关闭可能存在的解压进度窗口
            try:
                if self.extraction_progress_window and self.extraction_progress_window.isVisible():
                    self.extraction_progress_window.close()
            except Exception:
                pass
            self.extraction_progress_window = None

            # 显示错误消息
            msgbox_frame(
                f"安装错误 - {self.app_name}",
                f"\n{game_version} 的安装过程中发生错误: {str(e)}\n\n跳过此游戏的安装。\n",
                QMessageBox.StandardButton.Ok
            ).exec()

            # 继续下一个任务
            self.process_next_offline_install_task(install_tasks)
            
    def is_offline_mode_available(self):
        """检查是否可以使用离线模式
        
        Returns:
            bool: 是否可以使用离线模式
        """
        # 在调试模式下始终允许离线模式
        if self._is_debug_mode():
            return True
            
        # 检查是否有离线补丁文件
        return self.has_offline_patches()
        
    def is_in_offline_mode(self):
        """检查当前是否处于离线模式
        
        Returns:
            bool: 是否处于离线模式
        """
        return self.is_offline_mode 

    def _show_missing_patches_dialog(self, installed_msg):
        """显示缺少离线补丁文件的对话框
        
        Args:
            installed_msg: 已安装的补丁信息
        """
        debug_mode = self._is_debug_mode()
        
        # 在安装完成后询问用户是否切换到在线模式
        msg_box = msgbox_frame(
            f"离线安装完成 - {self.app_name}",
            f"\n{installed_msg}以下游戏未找到对应的离线补丁文件：\n\n{chr(10).join(self.missing_offline_patches)}\n\n是否切换到在线模式继续安装？\n",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        result = msg_box.exec()
        
        if result == QMessageBox.StandardButton.Yes:
            if debug_mode:
                logger.debug("DEBUG: 用户选择切换到在线模式")
            
            # 切换到在线模式
            if hasattr(self.main_window, 'ui_manager'):
                self.main_window.ui_manager.switch_work_mode("online")
                
                # 直接启动下载流程
                self.main_window.setEnabled(True)
                # 保存当前选择的游戏列表，以便在线模式使用
                missing_games = self.missing_offline_patches.copy()
                # 启动下载流程
                QTimer.singleShot(500, lambda: self._start_online_download(missing_games))
        else:
            if debug_mode:
                logger.debug("DEBUG: 用户选择不切换到在线模式")
            
            # 恢复UI状态
            self.main_window.setEnabled(True)
            self.main_window.ui.start_install_text.setText("开始安装") 