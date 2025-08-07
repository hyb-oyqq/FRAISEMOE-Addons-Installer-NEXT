import os
import hashlib
import tempfile
import py7zr
import traceback
from utils.logger import setup_logger
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QTimer
from data.config import PLUGIN_HASH, APP_NAME
from workers.hash_thread import HashThread

# 初始化logger
logger = setup_logger("patch_detector")

class PatchDetector:
    """补丁检测与校验模块，用于统一处理在线和离线模式下的补丁检测和校验"""
    
    def __init__(self, main_window):
        """初始化补丁检测器
        
        Args:
            main_window: 主窗口实例，用于访问UI和状态
        """
        self.main_window = main_window
        self.app_name = main_window.APP_NAME if hasattr(main_window, 'APP_NAME') else ""
        self.game_info = {}
        self.plugin_hash = {}
        
        # 从配置中加载游戏信息和补丁哈希值
        self._load_game_info()
        
    def _load_game_info(self):
        """从配置中加载游戏信息和补丁哈希值"""
        try:
            from data.config import GAME_INFO, PLUGIN_HASH
            self.game_info = GAME_INFO
            self.plugin_hash = PLUGIN_HASH
        except ImportError:
            logger.error("无法加载游戏信息或补丁哈希值配置")
            
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
            
    def check_patch_installed(self, game_dir, game_version):
        """检查游戏是否已安装补丁
        
        Args:
            game_dir: 游戏目录路径
            game_version: 游戏版本
            
        Returns:
            bool: 如果已安装补丁或有被禁用的补丁文件返回True，否则返回False
        """
        debug_mode = self._is_debug_mode()
        
        if game_version not in self.game_info:
            return False
            
        # 获取可能的补丁文件路径
        install_path_base = os.path.basename(self.game_info[game_version]["install_path"])
        patch_file_path = os.path.join(game_dir, install_path_base)
        
        # 尝试查找补丁文件，支持不同大小写
        patch_files_to_check = [
            patch_file_path,
            patch_file_path.lower(),
            patch_file_path.upper(),
            patch_file_path.replace("_", ""),
            patch_file_path.replace("_", "-"),
        ]
        
        # 查找补丁文件
        for patch_path in patch_files_to_check:
            if os.path.exists(patch_path):
                if debug_mode:
                    logger.debug(f"找到补丁文件: {patch_path}")
                return True
            # 检查是否存在被禁用的补丁文件（带.fain后缀）
            disabled_path = f"{patch_path}.fain"
            if os.path.exists(disabled_path):
                if debug_mode:
                    logger.debug(f"找到被禁用的补丁文件: {disabled_path}")
                return True
                
        # 检查是否有补丁文件夹
        patch_folders_to_check = [
            os.path.join(game_dir, "patch"),
            os.path.join(game_dir, "Patch"),
            os.path.join(game_dir, "PATCH"),
        ]
        
        for patch_folder in patch_folders_to_check:
            if os.path.exists(patch_folder):
                if debug_mode:
                    logger.debug(f"找到补丁文件夹: {patch_folder}")
                return True
                
        # 检查game/patch文件夹
        game_folders = ["game", "Game", "GAME"]
        patch_folders = ["patch", "Patch", "PATCH"]
        
        for game_folder in game_folders:
            for patch_folder in patch_folders:
                game_patch_folder = os.path.join(game_dir, game_folder, patch_folder)
                if os.path.exists(game_patch_folder):
                    if debug_mode:
                        logger.debug(f"找到game/patch文件夹: {game_patch_folder}")
                    return True
        
        # 检查配置文件
        config_files = ["config.json", "Config.json", "CONFIG.JSON"]
        script_files = ["scripts.json", "Scripts.json", "SCRIPTS.JSON"]
        
        for game_folder in game_folders:
            game_path = os.path.join(game_dir, game_folder)
            if os.path.exists(game_path):
                # 检查配置文件
                for config_file in config_files:
                    config_path = os.path.join(game_path, config_file)
                    if os.path.exists(config_path):
                        if debug_mode:
                            logger.debug(f"找到配置文件: {config_path}")
                        return True
                
                # 检查脚本文件
                for script_file in script_files:
                    script_path = os.path.join(game_path, script_file)
                    if os.path.exists(script_path):
                        if debug_mode:
                            logger.debug(f"找到脚本文件: {script_path}")
                        return True
        
        # 没有找到补丁文件或文件夹
        if debug_mode:
            logger.debug(f"{game_version} 在 {game_dir} 中没有安装补丁")
        return False
        
    def check_patch_disabled(self, game_dir, game_version):
        """检查游戏的补丁是否已被禁用
        
        Args:
            game_dir: 游戏目录路径
            game_version: 游戏版本
            
        Returns:
            bool: 如果补丁被禁用返回True，否则返回False
            str: 禁用的补丁文件路径，如果没有禁用返回None
        """
        debug_mode = self._is_debug_mode()
        
        if game_version not in self.game_info:
            return False, None
            
        # 获取可能的补丁文件路径
        install_path_base = os.path.basename(self.game_info[game_version]["install_path"])
        patch_file_path = os.path.join(game_dir, install_path_base)
        
        # 检查是否存在禁用的补丁文件（.fain后缀）
        disabled_patch_files = [
            f"{patch_file_path}.fain",
            f"{patch_file_path.lower()}.fain",
            f"{patch_file_path.upper()}.fain",
            f"{patch_file_path.replace('_', '')}.fain",
            f"{patch_file_path.replace('_', '-')}.fain",
        ]
        
        # 检查是否有禁用的补丁文件
        for disabled_path in disabled_patch_files:
            if os.path.exists(disabled_path):
                if debug_mode:
                    logger.debug(f"找到禁用的补丁文件: {disabled_path}")
                return True, disabled_path
                
        if debug_mode:
            logger.debug(f"{game_version} 在 {game_dir} 的补丁未被禁用")
            
        return False, None
            
    def detect_installable_games(self, game_dirs):
        """检测可安装补丁的游戏
        
        Args:
            game_dirs: 游戏版本到游戏目录的映射字典
            
        Returns:
            tuple: (已安装补丁的游戏列表, 可安装补丁的游戏列表, 禁用补丁的游戏列表)
        """
        debug_mode = self._is_debug_mode()
        
        if debug_mode:
            logger.debug(f"开始检测可安装补丁的游戏，游戏目录: {game_dirs}")
            
        already_installed_games = []
        installable_games = []
        disabled_patch_games = []
        
        for game_version, game_dir in game_dirs.items():
            # 首先通过文件检查确认补丁是否已安装
            is_patch_installed = self.check_patch_installed(game_dir, game_version)
            # 同时考虑哈希检查结果
            hash_check_passed = self.main_window.installed_status.get(game_version, False)
            
            # 如果补丁文件存在或哈希检查通过，认为已安装
            if is_patch_installed or hash_check_passed:
                if debug_mode:
                    logger.info(f"DEBUG: {game_version} 已安装补丁，不需要再次安装")
                    logger.info(f"DEBUG: 文件检查结果: {is_patch_installed}, 哈希检查结果: {hash_check_passed}")
                already_installed_games.append(game_version)
                # 更新安装状态
                self.main_window.installed_status[game_version] = True
            else:
                # 检查是否存在被禁用的补丁
                is_disabled, disabled_path = self.check_patch_disabled(game_dir, game_version)
                if is_disabled:
                    if debug_mode:
                        logger.info(f"DEBUG: {game_version} 存在被禁用的补丁: {disabled_path}")
                    disabled_patch_games.append(game_version)
                else:
                    if debug_mode:
                        logger.info(f"DEBUG: {game_version} 未安装补丁，可以安装")
                        logger.info(f"DEBUG: 文件检查结果: {is_patch_installed}, 哈希检查结果: {hash_check_passed}")
                    installable_games.append(game_version)
                    
        if debug_mode:
            logger.debug(f"检测结果 - 已安装补丁: {already_installed_games}")
            logger.debug(f"检测结果 - 可安装补丁: {installable_games}")
            logger.debug(f"检测结果 - 禁用补丁: {disabled_patch_games}")
            
        return already_installed_games, installable_games, disabled_patch_games
        
    def verify_patch_hash(self, game_version, file_path):
        """验证补丁文件的哈希值
        
        Args:
            game_version: 游戏版本名称
            file_path: 补丁压缩包文件路径
            
        Returns:
            bool: 哈希值是否匹配
        """
        # 获取预期的哈希值
        expected_hash = None
        
        # 直接使用完整游戏名称作为键
        expected_hash = self.plugin_hash.get(game_version, "")
            
        if not expected_hash:
            logger.warning(f"DEBUG: 未找到 {game_version} 的预期哈希值")
            return False
            
        debug_mode = self._is_debug_mode()
        
        if debug_mode:
            logger.debug(f"DEBUG: 开始验证补丁文件: {file_path}")
            logger.debug(f"DEBUG: 游戏版本: {game_version}")
            logger.debug(f"DEBUG: 预期哈希值: {expected_hash}")
            
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                if debug_mode:
                    logger.warning(f"DEBUG: 补丁文件不存在: {file_path}")
                return False
                
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if debug_mode:
                logger.debug(f"DEBUG: 补丁文件大小: {file_size} 字节")
                
            if file_size == 0:
                if debug_mode:
                    logger.warning(f"DEBUG: 补丁文件大小为0，无效文件")
                return False
                
            # 创建临时目录用于解压文件
            with tempfile.TemporaryDirectory() as temp_dir:
                if debug_mode:
                    logger.debug(f"DEBUG: 创建临时目录: {temp_dir}")
                    
                # 解压补丁文件
                try:
                    if debug_mode:
                        logger.debug(f"DEBUG: 开始解压文件: {file_path}")
                        
                    with py7zr.SevenZipFile(file_path, mode="r") as archive:
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
                    return False
                
                # 获取补丁文件路径
                patch_file = None
                if "Vol.1" in game_version:
                    patch_file = os.path.join(temp_dir, "vol.1", "adultsonly.xp3")
                elif "Vol.2" in game_version:
                    patch_file = os.path.join(temp_dir, "vol.2", "adultsonly.xp3")
                elif "Vol.3" in game_version:
                    patch_file = os.path.join(temp_dir, "vol.3", "update00.int")
                elif "Vol.4" in game_version:
                    patch_file = os.path.join(temp_dir, "vol.4", "vol4adult.xp3")
                elif "After" in game_version:
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
                    return False
                
                if debug_mode:
                    logger.debug(f"DEBUG: 找到解压后的补丁文件: {patch_file}")
                    
                # 计算补丁文件哈希值
                try:
                    with open(patch_file, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    
                    # 比较哈希值
                    result = file_hash.lower() == expected_hash.lower()
                    
                    if debug_mode:
                        logger.debug(f"DEBUG: 补丁文件 {patch_file} 哈希值验证: {'成功' if result else '失败'}")
                        logger.debug(f"DEBUG: 预期哈希值: {expected_hash}")
                        logger.debug(f"DEBUG: 实际哈希值: {file_hash}")
                        
                    return result
                except Exception as e:
                    if debug_mode:
                        logger.error(f"DEBUG: 计算补丁文件哈希值失败: {e}")
                        logger.error(f"DEBUG: 错误类型: {type(e).__name__}")
                    return False
        except Exception as e:
            if debug_mode:
                logger.error(f"DEBUG: 验证补丁哈希值失败: {e}")
                logger.error(f"DEBUG: 错误类型: {type(e).__name__}")
                logger.error(f"DEBUG: 错误堆栈: {traceback.format_exc()}")
            return False 

    def create_hash_thread(self, mode, install_paths):
        """创建哈希检查线程
        
        Args:
            mode: 检查模式，"pre"或"after"
            install_paths: 安装路径字典
            
        Returns:
            HashThread: 哈希检查线程实例
        """
        return HashThread(mode, install_paths, PLUGIN_HASH, self.main_window.installed_status, self.main_window)
        
    def after_hash_compare(self):
        """进行安装后哈希比较"""
        # 禁用窗口已在安装流程开始时完成
        
        # 检查是否处于离线模式
        is_offline = False
        if hasattr(self.main_window, 'offline_mode_manager'):
            is_offline = self.main_window.offline_mode_manager.is_in_offline_mode()
        
        self.main_window.hash_msg_box = self.main_window.hash_manager.hash_pop_window(check_type="after", is_offline=is_offline)

        install_paths = self.main_window.download_manager.get_install_paths()
        
        self.main_window.hash_thread = self.create_hash_thread("after", install_paths)
        self.main_window.hash_thread.after_finished.connect(self.on_after_hash_finished)
        self.main_window.hash_thread.start()
    
    def on_after_hash_finished(self, result):
        """哈希比较完成后的处理
        
        Args:
            result: 哈希比较结果
        """
        # 确保哈希检查窗口关闭，无论是否还在显示
        if self.main_window.hash_msg_box:
            try:
                if self.main_window.hash_msg_box.isVisible():
                    self.main_window.hash_msg_box.close()
                else:
                    # 如果窗口已经不可见但没有关闭，也要尝试关闭
                    self.main_window.hash_msg_box.close()
            except:
                pass  # 忽略任何关闭窗口时的错误
            self.main_window.hash_msg_box = None

        if not result["passed"]:
            # 启用窗口以显示错误消息
            self.main_window.setEnabled(True)
            
            game = result.get("game", "未知游戏")
            message = result.get("message", "发生未知错误。")
            msg_box = QMessageBox.critical(
                self.main_window,
                f"文件校验失败 - {APP_NAME}",
                message,
                QMessageBox.StandardButton.Ok,
            )

        # 恢复窗口状态
        self.main_window.setEnabled(True)
        self.main_window.ui.start_install_text.setText("开始安装")
        
        # 添加短暂延迟确保UI更新
        QTimer.singleShot(100, self.main_window.show_result)
        
    def on_offline_pre_hash_finished(self, updated_status, game_dirs):
        """离线模式下的哈希预检查完成处理
        
        Args:
            updated_status: 更新后的安装状态
            game_dirs: 识别到的游戏目录
        """
        # 更新安装状态
        self.main_window.installed_status = updated_status
        
        # 关闭哈希检查窗口
        if self.main_window.hash_msg_box and self.main_window.hash_msg_box.isVisible():
            self.main_window.hash_msg_box.accept()
            self.main_window.hash_msg_box = None
            
        # 重新启用主窗口
        self.main_window.setEnabled(True)
        
        # 使用patch_detector检测可安装的游戏
        already_installed_games, installable_games, disabled_patch_games = self.detect_installable_games(game_dirs)
        
        debug_mode = self._is_debug_mode()
            
        status_message = ""
        if already_installed_games:
            status_message += f"已安装补丁的游戏：\n{chr(10).join(already_installed_games)}\n\n"
            
        # 处理禁用补丁的情况
        if disabled_patch_games:
            # 构建提示消息
            disabled_msg = f"检测到以下游戏的补丁已被禁用：\n{chr(10).join(disabled_patch_games)}\n\n是否要启用这些补丁？"
            
            from PySide6 import QtWidgets
            reply = QtWidgets.QMessageBox.question(
                self.main_window, 
                f"检测到禁用补丁 - {APP_NAME}", 
                disabled_msg,
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                # 用户选择启用补丁
                if debug_mode:
                    logger.debug(f"DEBUG: 用户选择启用被禁用的补丁")
                
                # 为每个禁用的游戏创建目录映射
                disabled_game_dirs = {game: game_dirs[game] for game in disabled_patch_games}
                
                # 批量启用补丁
                success_count, fail_count, results = self.main_window.patch_manager.batch_toggle_patches(
                    disabled_game_dirs, 
                    operation="enable"
                )
                
                # 显示启用结果
                self.main_window.patch_manager.show_toggle_result(success_count, fail_count, results)
                
                # 更新安装状态
                for game_version in disabled_patch_games:
                    self.main_window.installed_status[game_version] = True
                    if game_version in installable_games:
                        installable_games.remove(game_version)
                    if game_version not in already_installed_games:
                        already_installed_games.append(game_version)
            else:
                if debug_mode:
                    logger.info(f"DEBUG: 用户选择不启用被禁用的补丁，这些游戏将被添加到可安装列表")
                # 用户选择不启用，将这些游戏视为可以安装补丁
                installable_games.extend(disabled_patch_games)

        # 更新status_message
        if disabled_patch_games:
            status_message += f"禁用补丁的游戏：\n{chr(10).join(disabled_patch_games)}\n\n"
            
        if not installable_games:
            # 没有可安装的游戏，显示信息并重置UI
            if already_installed_games:
                # 有已安装的游戏，显示已安装信息
                QMessageBox.information(
                    self.main_window,
                    f"信息 - {APP_NAME}",
                    f"\n所有游戏已安装补丁，无需重复安装。\n\n{status_message}",
                    QMessageBox.StandardButton.Ok,
                )
            else:
                # 没有已安装的游戏，可能是未检测到游戏
                QMessageBox.warning(
                    self.main_window,
                    f"警告 - {APP_NAME}",
                    "\n未检测到任何需要安装补丁的游戏。\n\n请确保游戏文件夹位于选择的目录中。\n",
                    QMessageBox.StandardButton.Ok,
                )
                
            self.main_window.ui.start_install_text.setText("开始安装")
            return
            
        # 显示游戏选择对话框
        from PySide6 import QtWidgets
        dialog = QtWidgets.QDialog(self.main_window)
        dialog.setWindowTitle(f"选择要安装的游戏 - {APP_NAME}")
        dialog.setMinimumWidth(300)
        
        layout = QtWidgets.QVBoxLayout()
        
        # 添加说明标签
        label = QtWidgets.QLabel("请选择要安装补丁的游戏：")
        layout.addWidget(label)
        
        # 添加游戏列表
        list_widget = QtWidgets.QListWidget()
        list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        
        for game in installable_games:
            item = QtWidgets.QListWidgetItem(game)
            list_widget.addItem(item)
            item.setSelected(True)  # 默认全选
            
        layout.addWidget(list_widget)
        
        # 添加按钮
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | 
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        # 显示对话框
        result = dialog.exec()
        if result != QtWidgets.QDialog.DialogCode.Accepted or list_widget.selectedItems() == []:
            self.main_window.ui.start_install_text.setText("开始安装")
            return
            
        # 获取用户选择的游戏
        selected_games = [item.text() for item in list_widget.selectedItems()]
        
        # 开始安装
        if debug_mode:
            logger.debug(f"DEBUG: 用户选择了以下游戏进行安装: {selected_games}")
            
        # 调用离线模式管理器安装补丁
        self.main_window.offline_mode_manager.install_offline_patches(selected_games) 