import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QPushButton, QHBoxLayout, 
    QAbstractItemView, QFileDialog, QMessageBox
)
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtGui import QFont
from utils import msgbox_frame
from utils.logger import setup_logger

# 初始化logger
logger = setup_logger("uninstall_handler")

class UninstallThread(QThread):
    """在后台线程中处理卸载逻辑"""
    finished = Signal(object)

    def __init__(self, handler, selected_folder):
        super().__init__()
        self.handler = handler
        self.selected_folder = selected_folder

    def run(self):
        # 在后台线程中执行耗时操作
        game_dirs = self.handler.game_detector.identify_game_directories_improved(self.selected_folder)
        self.finished.emit(game_dirs)

class UninstallHandler(QObject):
    """
    处理补丁卸载功能的类
    """
    def __init__(self, main_window):
        """
        初始化卸载处理程序
        
        Args:
            main_window: 主窗口实例，用于访问其他组件
        """
        super().__init__()
        self.main_window = main_window
        self.debug_manager = main_window.debug_manager
        self.game_detector = main_window.game_detector
        self.patch_manager = main_window.patch_manager
        self.app_name = main_window.patch_manager.app_name
        self.uninstall_thread = None
        
        # 记录初始化日志
        debug_mode = self.debug_manager._is_debug_mode() if hasattr(self.debug_manager, '_is_debug_mode') else False
        if debug_mode:
            logger.debug("DEBUG: 卸载处理程序已初始化")
    
    def handle_uninstall_button_click(self):
        """
        处理卸载补丁按钮点击事件
        打开文件选择对话框选择游戏目录，然后卸载对应游戏的补丁
        """
        # 获取游戏目录
        debug_mode = self.debug_manager._is_debug_mode()
        
        logger.info("用户点击了卸载补丁按钮")
        if debug_mode:
            logger.debug("DEBUG: 处理卸载补丁按钮点击事件")
        
        # 提示用户选择目录
        file_dialog_info = "选择游戏上级目录" if debug_mode else "选择游戏目录"
        selected_folder = QFileDialog.getExistingDirectory(self.main_window, file_dialog_info, "")
        
        if not selected_folder or selected_folder == "":
            logger.info("用户取消了目录选择")
            if debug_mode:
                logger.debug("DEBUG: 用户取消了目录选择，退出卸载流程")
            return  # 用户取消了选择
        
        logger.info(f"用户选择了目录: {selected_folder}")
        if debug_mode:
            logger.debug(f"DEBUG: 卸载功能 - 用户选择了目录: {selected_folder}")
        
        self.main_window.show_loading_dialog("正在识别游戏目录...")
        
        self.uninstall_thread = UninstallThread(self, selected_folder)
        self.uninstall_thread.finished.connect(self.on_game_detection_finished)
        self.uninstall_thread.start()

    def on_game_detection_finished(self, game_dirs):
        """游戏识别完成后的回调"""
        self.main_window.hide_loading_dialog()

        if not game_dirs:
            QMessageBox.information(
                self.main_window,
                f"提示 - {self.app_name}",
                "\n未在选择的目录中找到任何支持的游戏。\n",
            )
            return

        games_with_patch = {}
        for game_version, game_dir in game_dirs.items():
            if self.patch_manager.check_patch_installed(game_dir, game_version):
                games_with_patch[game_version] = game_dir
        
        if not games_with_patch:
            QMessageBox.information(
                self.main_window,
                f"提示 - {self.app_name}",
                "\n目录中未找到已安装补丁的游戏。\n",
            )
            return

        selected_games = self._show_game_selection_dialog(games_with_patch)
        
        if not selected_games:
            return
        
        selected_game_dirs = {game: games_with_patch[game] for game in selected_games if game in games_with_patch}
        
        game_list = '\n'.join(selected_games)
        reply = QMessageBox.question(
            self.main_window,
            f"确认卸载 - {self.app_name}",
            f"\n确定要卸载以下游戏的补丁吗？\n\n{game_list}\n",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        success_count, fail_count, results = self.patch_manager.batch_uninstall_patches(selected_game_dirs)
        self.patch_manager.show_uninstall_result(success_count, fail_count, results)
    
    def _handle_multiple_games(self, game_dirs, debug_mode):
        """
        处理多个游戏的补丁卸载
        
        Args:
            game_dirs: 游戏目录字典
            debug_mode: 是否为调试模式
        """
        if debug_mode:
            logger.debug(f"DEBUG: 卸载功能 - 在上级目录中找到以下游戏: {list(game_dirs.keys())}")
        
        # 查找已安装补丁的游戏，只处理那些已安装补丁的游戏
        logger.info("检查哪些游戏已安装补丁")
        games_with_patch = {}
        for game_version, game_dir in game_dirs.items():
            is_installed = self.patch_manager.check_patch_installed(game_dir, game_version)
            if is_installed:
                games_with_patch[game_version] = game_dir
                logger.info(f"游戏 {game_version} 已安装补丁")
                if debug_mode:
                    logger.debug(f"DEBUG: 卸载功能 - {game_version} 已安装补丁，目录: {game_dir}")
            else:
                logger.info(f"游戏 {game_version} 未安装补丁")
                if debug_mode:
                    logger.debug(f"DEBUG: 卸载功能 - {game_version} 未安装补丁，跳过")
        
        # 检查是否有已安装补丁的游戏
        if not games_with_patch:
            logger.info("未找到已安装补丁的游戏")
            if debug_mode:
                logger.debug("DEBUG: 卸载功能 - 未找到已安装补丁的游戏，显示提示消息")
                
            QMessageBox.information(
                self.main_window,
                f"提示 - {self.app_name}",
                "\n未在选择的目录中找到已安装补丁的游戏。\n请确认您选择了正确的游戏目录，并且该目录中的游戏已安装过补丁。\n",
                QMessageBox.StandardButton.Ok
            )
            return
        
        # 显示选择对话框
        logger.info("显示游戏选择对话框")
        if debug_mode:
            logger.debug(f"DEBUG: 卸载功能 - 显示游戏选择对话框，可选游戏: {list(games_with_patch.keys())}")
            
        selected_games = self._show_game_selection_dialog(games_with_patch)
        
        if not selected_games:
            logger.info("用户未选择任何游戏或取消了选择")
            if debug_mode:
                logger.debug("DEBUG: 卸载功能 - 用户未选择任何游戏或取消了选择，退出卸载流程")
            return  # 用户取消了选择
        
        logger.info(f"用户选择了以下游戏: {selected_games}")
        if debug_mode:
            logger.debug(f"DEBUG: 卸载功能 - 用户选择了以下游戏: {selected_games}")
        
        # 过滤game_dirs，只保留选中的游戏
        selected_game_dirs = {game: games_with_patch[game] for game in selected_games if game in games_with_patch}
        
        # 确认卸载
        game_list = '\n'.join(selected_games)
        logger.info("显示卸载确认对话框")
        if debug_mode:
            logger.debug(f"DEBUG: 卸载功能 - 显示卸载确认对话框，选择的游戏: {selected_games}")
            
        reply = QMessageBox.question(
            self.main_window,
            f"确认卸载 - {self.app_name}",
            f"\n确定要卸载以下游戏的补丁吗？\n\n{game_list}\n",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            logger.info("用户取消了卸载操作")
            if debug_mode:
                logger.debug("DEBUG: 卸载功能 - 用户取消了卸载操作，退出卸载流程")
            return
        
        logger.info("开始批量卸载补丁")
        if debug_mode:
            logger.debug(f"DEBUG: 卸载功能 - 开始批量卸载补丁，游戏: {list(selected_game_dirs.keys())}")
            
        # 使用批量卸载方法
        success_count, fail_count, results = self.patch_manager.batch_uninstall_patches(selected_game_dirs)
        
        logger.info(f"批量卸载完成，成功: {success_count}，失败: {fail_count}")
        if debug_mode:
            logger.debug(f"DEBUG: 卸载功能 - 批量卸载完成，成功: {success_count}，失败: {fail_count}")
            if results:
                for result in results:
                    status = "成功" if result["success"] else "失败"
                    logger.debug(f"DEBUG: 卸载结果 - {result['version']}: {status}, 消息: {result['message']}, 删除文件数: {result['files_removed']}")
        
        self.patch_manager.show_uninstall_result(success_count, fail_count, results)
    
    def _handle_single_game(self, selected_folder, debug_mode):
        """
        处理单个游戏的补丁卸载
        
        Args:
            selected_folder: 选择的游戏目录
            debug_mode: 是否为调试模式
        """
        # 未找到游戏目录，尝试将选择的目录作为游戏目录
        if debug_mode:
            logger.debug(f"DEBUG: 卸载功能 - 未在上级目录找到游戏，尝试将选择的目录视为游戏目录")
            
        logger.info("尝试识别单个游戏版本")
        game_version = self.game_detector.identify_game_version(selected_folder)
        
        if game_version:
            logger.info(f"识别为游戏: {game_version}")
            if debug_mode:
                logger.debug(f"DEBUG: 卸载功能 - 识别为游戏: {game_version}")
            
            # 检查是否已安装补丁
            logger.info(f"检查 {game_version} 是否已安装补丁")
            is_installed = self.patch_manager.check_patch_installed(selected_folder, game_version)
            
            if is_installed:
                logger.info(f"{game_version} 已安装补丁")
                if debug_mode:
                    logger.debug(f"DEBUG: 卸载功能 - {game_version} 已安装补丁")
                
                # 确认卸载
                logger.info("显示卸载确认对话框")
                if debug_mode:
                    logger.debug(f"DEBUG: 卸载功能 - 显示卸载确认对话框，游戏: {game_version}")
                    
                reply = QMessageBox.question(
                    self.main_window,
                    f"确认卸载 - {self.app_name}",
                    f"\n确定要卸载 {game_version} 的补丁吗？\n游戏目录: {selected_folder}\n",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    logger.info(f"开始卸载 {game_version} 的补丁")
                    if debug_mode:
                        logger.debug(f"DEBUG: 卸载功能 - 用户确认卸载 {game_version} 的补丁")
                    
                    # 创建单个游戏的目录字典，使用批量卸载流程
                    single_game_dir = {game_version: selected_folder}
                    
                    logger.info("执行批量卸载方法（单游戏）")
                    if debug_mode:
                        logger.debug(f"DEBUG: 卸载功能 - 执行批量卸载方法（单游戏）: {game_version}")
                        
                    success_count, fail_count, results = self.patch_manager.batch_uninstall_patches(single_game_dir)
                    
                    logger.info(f"卸载完成，成功: {success_count}，失败: {fail_count}")
                    if debug_mode:
                        logger.debug(f"DEBUG: 卸载功能 - 卸载完成，成功: {success_count}，失败: {fail_count}")
                        if results:
                            for result in results:
                                status = "成功" if result["success"] else "失败"
                                logger.debug(f"DEBUG: 卸载结果 - {result['version']}: {status}, 消息: {result['message']}, 删除文件数: {result['files_removed']}")
                    
                    self.patch_manager.show_uninstall_result(success_count, fail_count, results)
                else:
                    logger.info("用户取消了卸载操作")
                    if debug_mode:
                        logger.debug(f"DEBUG: 卸载功能 - 用户取消了卸载 {game_version} 的补丁")
            else:
                logger.info(f"{game_version} 未安装补丁")
                if debug_mode:
                    logger.debug(f"DEBUG: 卸载功能 - {game_version} 未安装补丁，显示提示消息")
                
                # 没有安装补丁
                QMessageBox.information(
                    self.main_window,
                    f"提示 - {self.app_name}",
                    f"\n未在 {game_version} 中找到已安装的补丁。\n请确认该游戏已经安装过补丁。\n",
                    QMessageBox.StandardButton.Ok
                )
        else:
            # 两种方式都未识别到游戏
            logger.info("无法识别游戏")
            if debug_mode:
                logger.debug(f"DEBUG: 卸载功能 - 无法识别游戏，显示错误消息")
                
            msg_box = msgbox_frame(
                f"错误 - {self.app_name}",
                "\n所选目录不是有效的NEKOPARA游戏目录。\n请选择包含游戏可执行文件的目录或其上级目录。\n",
                QMessageBox.StandardButton.Ok,
            )
            msg_box.exec()
    
    def _show_game_selection_dialog(self, games_with_patch):
        """
        显示游戏选择对话框
        
        Args:
            games_with_patch: 已安装补丁的游戏目录字典
            
        Returns:
            list: 选择的游戏列表
        """
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("选择要卸载的游戏补丁")
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # 添加"已安装补丁的游戏"标签
        already_installed_label = QLabel("已安装补丁的游戏:", dialog)
        already_installed_label.setFont(QFont(already_installed_label.font().family(), already_installed_label.font().pointSize(), QFont.Weight.Bold))
        layout.addWidget(already_installed_label)
        
        # 添加已安装游戏列表（可选，这里使用静态标签替代，保持一致性）
        installed_games_text = ", ".join(games_with_patch.keys())
        installed_games_label = QLabel(installed_games_text, dialog)
        layout.addWidget(installed_games_label)
        
        # 添加一些间距
        layout.addSpacing(10)
        
        # 添加"请选择要卸载补丁的游戏"标签
        info_label = QLabel("请选择要卸载补丁的游戏:", dialog)
        info_label.setFont(QFont(info_label.font().family(), info_label.font().pointSize(), QFont.Weight.Bold))
        layout.addWidget(info_label)
        
        # 添加列表控件，只显示已安装补丁的游戏
        list_widget = QListWidget(dialog)
        list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)  # 允许多选
        for game in games_with_patch.keys():
            list_widget.addItem(game)
        layout.addWidget(list_widget)
        
        # 添加全选按钮
        select_all_btn = QPushButton("全选", dialog)
        select_all_btn.clicked.connect(lambda: list_widget.selectAll())
        layout.addWidget(select_all_btn)
        
        # 添加确定和取消按钮
        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("确定", dialog)
        cancel_button = QPushButton("取消", dialog)
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        
        # 连接按钮事件
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        # 显示对话框并等待用户选择
        result = dialog.exec()
        
        if result != QDialog.DialogCode.Accepted or list_widget.selectedItems() == []:
            # 用户取消或未选择任何游戏
            return []
            
        # 获取用户选择的游戏
        return [item.text() for item in list_widget.selectedItems()] 