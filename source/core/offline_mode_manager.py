import os
import hashlib
import shutil
import tempfile
import py7zr
import traceback
from PySide6.QtWidgets import QMessageBox

from data.config import PLUGIN, PLUGIN_HASH, GAME_INFO
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
            # 获取软件所在目录
            directory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        debug_mode = self._is_debug_mode()
        if debug_mode:
            logger.debug(f"DEBUG: 扫描离线补丁文件，目录: {directory}")
            
        # 要查找的补丁文件名
        patch_files = ["vol.1.7z", "vol.2.7z", "vol.3.7z", "vol.4.7z", "after.7z"]
        
        found_patches = {}
        
        # 扫描目录中的文件
        for file in os.listdir(directory):
            if file.lower() in patch_files:
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path):
                    patch_name = file.lower()
                    found_patches[patch_name] = file_path
                    if debug_mode:
                        logger.debug(f"DEBUG: 找到离线补丁文件: {patch_name} 路径: {file_path}")
                        
        self.offline_patches = found_patches
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
                return False
                
            if debug_mode:
                logger.debug("DEBUG: 已启用离线模式（调试模式下允许强制启用）")
                
        self.is_offline_mode = enabled
        
        # 更新窗口标题
        if hasattr(self.main_window, 'setWindowTitle'):
            from data.config import APP_NAME, APP_VERSION
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
        # 使用patch_detector模块验证哈希值
        return self.main_window.patch_detector.verify_patch_hash(game_version, file_path)
            
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
            
        # 创建安装任务列表
        install_tasks = []
        for game_version in selected_games:
            # 获取离线补丁文件路径
            patch_file = self.get_offline_patch_path(game_version)
            if not patch_file:
                if debug_mode:
                    logger.warning(f"DEBUG: 未找到 {game_version} 的离线补丁文件，跳过")
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
        else:
            if debug_mode:
                logger.warning("DEBUG: 没有可安装的游戏，安装流程结束")
            msgbox_frame(
                f"离线安装信息 - {self.app_name}",
                "\n没有可安装的游戏或未找到对应的离线补丁文件。\n",
                QMessageBox.StandardButton.Ok
            ).exec()
            self.main_window.setEnabled(True)
            self.main_window.ui.start_install_text.setText("开始安装")
            
        return True
        
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
            return
            
        # 获取下一个任务
        patch_file, game_folder, game_version, _7z_path, plugin_path = install_tasks.pop(0)
        
        if debug_mode:
            logger.debug(f"DEBUG: 处理离线安装任务: {game_version}")
            logger.debug(f"DEBUG: 补丁文件: {patch_file}")
            logger.debug(f"DEBUG: 游戏目录: {game_folder}")
            
        # 确保目标目录存在
        os.makedirs(os.path.dirname(_7z_path), exist_ok=True)
        
        try:
            # 复制补丁文件到缓存目录
            shutil.copy2(patch_file, _7z_path)
            
            if debug_mode:
                logger.debug(f"DEBUG: 已复制补丁文件到缓存目录: {_7z_path}")
                logger.debug(f"DEBUG: 开始验证补丁文件哈希值")
                
            # 显示哈希验证窗口 - 使用离线特定消息
            self.main_window.hash_msg_box = self.main_window.hash_manager.hash_pop_window(check_type="offline_verify", is_offline=True)
            
            # 验证补丁文件哈希
            hash_valid = self.verify_patch_hash(game_version, _7z_path)
            
            # 关闭哈希验证窗口
            if self.main_window.hash_msg_box and self.main_window.hash_msg_box.isVisible():
                self.main_window.hash_msg_box.close()
                self.main_window.hash_msg_box = None
            
            if hash_valid:
                if debug_mode:
                    logger.info(f"DEBUG: 补丁文件哈希验证成功，开始解压")
                
                # 显示解压窗口 - 使用离线特定消息
                self.main_window.hash_msg_box = self.main_window.hash_manager.hash_pop_window(check_type="offline_extraction", is_offline=True)
                
                try:
                    # 创建解压线程
                    extraction_thread = self.main_window.create_extraction_thread(
                        _7z_path, game_folder, plugin_path, game_version
                    )
                    
                    # 正确连接信号
                    extraction_thread.finished.connect(
                        lambda success, error, game_ver: self.on_extraction_thread_finished(
                            success, error, game_ver, install_tasks
                        )
                    )
                    
                    # 启动解压线程
                    extraction_thread.start()
                except Exception as e:
                    if debug_mode:
                        logger.error(f"DEBUG: 创建或启动解压线程失败: {e}")
                    
                    # 关闭解压窗口
                    if self.main_window.hash_msg_box and self.main_window.hash_msg_box.isVisible():
                        self.main_window.hash_msg_box.close()
                        self.main_window.hash_msg_box = None
                    
                    # 显示错误消息
                    msgbox_frame(
                        f"解压错误 - {self.app_name}",
                        f"\n{game_version} 的解压过程中发生错误: {str(e)}\n\n跳过此游戏的安装。\n",
                        QMessageBox.StandardButton.Ok
                    ).exec()
                    
                    # 继续下一个任务
                    self.process_next_offline_install_task(install_tasks)
            else:
                if debug_mode:
                    logger.warning(f"DEBUG: 补丁文件哈希验证失败")
                    
                # 显示错误消息
                msgbox_frame(
                    f"哈希验证失败 - {self.app_name}",
                    f"\n{game_version} 的补丁文件哈希验证失败，可能已损坏或被篡改。\n\n跳过此游戏的安装。\n",
                    QMessageBox.StandardButton.Ok
                ).exec()
                
                # 继续下一个任务
                self.process_next_offline_install_task(install_tasks)
        except Exception as e:
            if debug_mode:
                logger.error(f"DEBUG: 离线安装任务处理失败: {e}")
                
            # 显示错误消息
            msgbox_frame(
                f"安装错误 - {self.app_name}",
                f"\n{game_version} 的安装过程中发生错误: {str(e)}\n\n跳过此游戏的安装。\n",
                QMessageBox.StandardButton.Ok
            ).exec()
            
            # 继续下一个任务
            self.process_next_offline_install_task(install_tasks)
    
    def on_extraction_thread_finished(self, success, error_message, game_version, remaining_tasks):
        """解压线程完成后的处理
        
        Args:
            success: 是否解压成功
            error_message: 错误信息
            game_version: 游戏版本
            remaining_tasks: 剩余的安装任务列表
        """
        debug_mode = self._is_debug_mode()
        
        # 关闭解压窗口
        if self.main_window.hash_msg_box and self.main_window.hash_msg_box.isVisible():
            self.main_window.hash_msg_box.close()
            self.main_window.hash_msg_box = None
        
        if debug_mode:
            logger.debug(f"DEBUG: 离线解压完成，状态: {'成功' if success else '失败'}")
            if not success:
                logger.error(f"DEBUG: 错误信息: {error_message}")
        
        if not success:
            # 显示错误消息
            msgbox_frame(
                f"解压失败 - {self.app_name}",
                f"\n{game_version} 的补丁解压失败。\n\n错误信息: {error_message}\n\n跳过此游戏的安装。\n",
                QMessageBox.StandardButton.Ok
            ).exec()
            
            # 更新安装状态
            self.main_window.installed_status[game_version] = False
        else:
            # 更新安装状态
            self.main_window.installed_status[game_version] = True
            
            # 添加到已安装游戏列表
            if game_version not in self.installed_games:
                self.installed_games.append(game_version)
        
        # 处理下一个任务
        self.process_next_offline_install_task(remaining_tasks)
            
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