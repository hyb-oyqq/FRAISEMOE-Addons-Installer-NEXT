import os
import hashlib
import tempfile
import py7zr
import traceback
from utils.logger import setup_logger
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QTimer, QThread, Signal
from config.config import PLUGIN_HASH, APP_NAME

# 初始化logger
logger = setup_logger("patch_detector")

class PatchCheckThread(QThread):
    """用于在后台线程中执行补丁检查的线程"""
    finished = Signal(bool)  # (is_installed)

    def __init__(self, checker_func, *args):
        super().__init__()
        self.checker_func = checker_func
        self.args = args

    def run(self):
        result = self.checker_func(*self.args)
        self.finished.emit(result)

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
        self._load_game_info()
        self.patch_check_thread = None

    def _load_game_info(self):
        """从配置中加载游戏信息和补丁哈希值"""
        try:
            from config.config import GAME_INFO, PLUGIN_HASH
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
                    return self.main_window.debug_manager._is_debug_mode()
                elif hasattr(self.main_window, 'config'):
                    return self.main_window.config.get('debug_mode', False)
            return False
        except Exception:
            return False

    def check_patch_installed_async(self, game_dir, game_version, callback):
        """异步检查游戏是否已安装补丁"""
        def on_finished(is_installed):
            callback(is_installed)
            self.patch_check_thread = None

        self.patch_check_thread = PatchCheckThread(self._check_patch_installed_sync, game_dir, game_version)
        self.patch_check_thread.finished.connect(on_finished)
        self.patch_check_thread.start()

    def _check_patch_installed_sync(self, game_dir, game_version):
        """同步检查游戏是否已安装补丁（在工作线程中运行）"""
        debug_mode = self._is_debug_mode()
        
        if debug_mode:
            logger.debug(f"DEBUG: 检查 {game_version} 是否已安装补丁，目录: {game_dir}")
        
        if game_version not in self.game_info:
            if debug_mode:
                logger.debug(f"DEBUG: {game_version} 不在支持的游戏列表中，跳过检查")
            return False
            
        install_path_base = os.path.basename(self.game_info[game_version]["install_path"])
        patch_file_path = os.path.join(game_dir, install_path_base)
        
        # 检查补丁文件和禁用的补丁文件
        if os.path.exists(patch_file_path) or os.path.exists(f"{patch_file_path}.fain"):
            return True

        return False

    def check_patch_installed(self, game_dir, game_version):
        """检查游戏是否已安装补丁（此方法可能导致阻塞，推荐使用异步版本）"""
        return self._check_patch_installed_sync(game_dir, game_version)

    def check_patch_disabled(self, game_dir, game_version):
        """检查游戏的补丁是否已被禁用"""
        debug_mode = self._is_debug_mode()
        
        if game_version not in self.game_info:
            return False, None
            
        install_path_base = os.path.basename(self.game_info[game_version]["install_path"])
        patch_file_path = os.path.join(game_dir, install_path_base)
        disabled_path = f"{patch_file_path}.fain"
        
        if os.path.exists(disabled_path):
            if debug_mode:
                logger.debug(f"找到禁用的补丁文件: {disabled_path}")
            return True, disabled_path
                
        if debug_mode:
            logger.debug(f"{game_version} 在 {game_dir} 的补丁未被禁用")
            
        return False, None
            
    def detect_installable_games(self, game_dirs):
        """检测可安装补丁的游戏"""
        debug_mode = self._is_debug_mode()
        
        if debug_mode:
            logger.debug(f"开始检测可安装补丁的游戏，游戏目录: {game_dirs}")
            
        already_installed_games = []
        installable_games = []
        disabled_patch_games = []
        
        for game_version, game_dir in game_dirs.items():
            is_patch_installed = self.check_patch_installed(game_dir, game_version)
            hash_check_passed = self.main_window.installed_status.get(game_version, False)
            
            if is_patch_installed or hash_check_passed:
                if debug_mode:
                    logger.debug(f"{game_version} 已安装补丁，不需要再次安装")
                    logger.debug(f"文件检查结果: {is_patch_installed}, 哈希检查结果: {hash_check_passed}")
                already_installed_games.append(game_version)
                self.main_window.installed_status[game_version] = True
            else:
                is_disabled, disabled_path = self.check_patch_disabled(game_dir, game_version)
                if is_disabled:
                    if debug_mode:
                        logger.debug(f"{game_version} 存在被禁用的补丁: {disabled_path}")
                    disabled_patch_games.append(game_version)
                else:
                    if debug_mode:
                        logger.debug(f"{game_version} 未安装补丁，可以安装")
                        logger.debug(f"文件检查结果: {is_patch_installed}, 哈希检查结果: {hash_check_passed}")
                    installable_games.append(game_version)
                    
        if debug_mode:
            logger.debug(f"检测结果 - 已安装补丁: {already_installed_games}")
            logger.debug(f"检测结果 - 可安装补丁: {installable_games}")
            logger.debug(f"检测结果 - 禁用补丁: {disabled_patch_games}")
            
        return already_installed_games, installable_games, disabled_patch_games
        
    def verify_patch_hash(self, game_version, file_path):
        """验证补丁文件的哈希值"""
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
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                return False
                
            with tempfile.TemporaryDirectory() as temp_dir:
                if debug_mode:
                    logger.debug(f"DEBUG: 创建临时目录: {temp_dir}")
                    
                try:
                    with py7zr.SevenZipFile(file_path, mode="r") as archive:
                        archive.extractall(path=temp_dir)
                except Exception as e:
                    if debug_mode:
                        logger.error(f"DEBUG: 解压补丁文件失败: {e}")
                    return False
                
                patch_file = self._find_patch_file_in_temp_dir(temp_dir, game_version)
                
                if not patch_file or not os.path.exists(patch_file):
                    if debug_mode:
                        logger.warning(f"DEBUG: 未找到解压后的补丁文件")
                    return False
                
                if debug_mode:
                    logger.debug(f"DEBUG: 找到解压后的补丁文件: {patch_file}")
                    
                try:
                    with open(patch_file, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    
                    result = file_hash.lower() == expected_hash.lower()
                    
                    if debug_mode:
                        logger.debug(f"DEBUG: 补丁文件 {patch_file} 哈希值验证: {'成功' if result else '失败'}")
                        
                    return result
                except Exception as e:
                    if debug_mode:
                        logger.error(f"DEBUG: 计算补丁文件哈希值失败: {e}")
                    return False
        except Exception as e:
            if debug_mode:
                logger.error(f"DEBUG: 验证补丁哈希值失败: {e}")
            return False

    def _find_patch_file_in_temp_dir(self, temp_dir, game_version):
        """在临时目录中查找解压后的补丁文件"""
        game_patch_map = {
            "Vol.1": os.path.join("vol.1", "adultsonly.xp3"),
            "Vol.2": os.path.join("vol.2", "adultsonly.xp3"),
            "Vol.3": os.path.join("vol.3", "update00.int"),
            "Vol.4": os.path.join("vol.4", "vol4adult.xp3"),
            "After": os.path.join("after", "afteradult.xp3"),
        }
        
        for version_keyword, relative_path in game_patch_map.items():
            if version_keyword in game_version:
                return os.path.join(temp_dir, relative_path)

        # 如果没有找到，则进行通用搜索
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.xp3') or file.endswith('.int'):
                    return os.path.join(root, file)
        return None

    def create_hash_thread(self, mode, install_paths):
        from workers.hash_thread import HashThread
        return HashThread(mode, install_paths, PLUGIN_HASH, self.main_window.installed_status, self.main_window)
        
    def after_hash_compare(self):
        is_offline = self.main_window.offline_mode_manager.is_in_offline_mode()
        
        self.main_window.close_hash_msg_box()
        self.main_window.hash_msg_box = self.main_window.hash_manager.hash_pop_window(check_type="after", is_offline=is_offline)

        install_paths = self.main_window.download_manager.get_install_paths()
        
        self.main_window.hash_thread = self.create_hash_thread("after", install_paths)
        self.main_window.hash_thread.after_finished.connect(self.on_after_hash_finished)
        self.main_window.hash_thread.start()
    
    def on_after_hash_finished(self, result):
        self.main_window.close_hash_msg_box()

        if not result["passed"]:
            self.main_window.setEnabled(True)
            game = result.get("game", "未知游戏")
            message = result.get("message", "发生未知错误。")
            QMessageBox.critical(self.main_window, f"文件校验失败 - {APP_NAME}", message)

        self.main_window.setEnabled(True)
        self.main_window.ui_manager.set_install_button_state("ready")
        QTimer.singleShot(100, self.main_window.show_result)
        
    def on_offline_pre_hash_finished(self, updated_status, game_dirs):
        self.main_window.installed_status = updated_status
        
        if self.main_window.hash_msg_box and self.main_window.hash_msg_box.isVisible():
            self.main_window.hash_msg_box.accept()
            self.main_window.hash_msg_box = None
            
        self.main_window.setEnabled(True)
        
        already_installed_games, installable_games, disabled_patch_games = self.detect_installable_games(game_dirs)
            
        status_message = ""
        if already_installed_games:
            status_message += f"已安装补丁的游戏：\n{chr(10).join(already_installed_games)}\n\n"
            
        if disabled_patch_games:
            disabled_msg = f"检测到以下游戏的补丁已被禁用：\n{chr(10).join(disabled_patch_games)}\n\n是否要启用这些补丁？"
            
            from PySide6 import QtWidgets
            reply = QtWidgets.QMessageBox.question(
                self.main_window, 
                f"检测到禁用补丁 - {APP_NAME}", 
                disabled_msg,
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                disabled_game_dirs = {game: game_dirs[game] for game in disabled_patch_games}
                
                success_count, fail_count, results = self.main_window.patch_manager.batch_toggle_patches(
                    disabled_game_dirs, 
                    operation="enable"
                )
                
                self.main_window.patch_manager.show_toggle_result(success_count, fail_count, results)
                
                for game_version in disabled_patch_games:
                    self.main_window.installed_status[game_version] = True
                    if game_version in installable_games:
                        installable_games.remove(game_version)
                    if game_version not in already_installed_games:
                        already_installed_games.append(game_version)
            else:
                installable_games.extend(disabled_patch_games)

        if disabled_patch_games:
            status_message += f"禁用补丁的游戏：\n{chr(10).join(disabled_patch_games)}\n\n"
            
        if not installable_games:
            if already_installed_games:
                QMessageBox.information(
                    self.main_window,
                    f"信息 - {APP_NAME}",
                    f"\n所有游戏已安装补丁，无需重复安装。\n\n{status_message}",
                )
            else:
                QMessageBox.warning(
                    self.main_window,
                    f"警告 - {APP_NAME}",
                    "\n未检测到任何需要安装补丁的游戏。\n\n请确保游戏文件夹位于选择的目录中。\n",
                )
                
            self.main_window.ui_manager.set_install_button_state("ready")
            return
            
        from PySide6 import QtWidgets
        dialog = QtWidgets.QDialog(self.main_window)
        dialog.setWindowTitle(f"选择要安装的游戏 - {APP_NAME}")
        dialog.setMinimumWidth(300)
        
        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("请选择要安装补丁的游戏：")
        layout.addWidget(label)
        
        list_widget = QtWidgets.QListWidget()
        list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        
        for game in installable_games:
            item = QtWidgets.QListWidgetItem(game)
            list_widget.addItem(item)
            item.setSelected(True)
            
        layout.addWidget(list_widget)
        
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | 
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        result = dialog.exec()
        if result != QtWidgets.QDialog.DialogCode.Accepted or not list_widget.selectedItems():
            self.main_window.ui_manager.set_install_button_state("ready")
            return
            
        selected_games = [item.text() for item in list_widget.selectedItems()]
        
        self.main_window.offline_mode_manager.install_offline_patches(selected_games) 