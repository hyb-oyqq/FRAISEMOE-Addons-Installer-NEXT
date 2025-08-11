import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QPushButton, QHBoxLayout, 
    QAbstractItemView, QRadioButton, QButtonGroup, QFileDialog, QMessageBox
)
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtGui import QFont
from utils import msgbox_frame
from utils.logger import setup_logger

# 初始化logger
logger = setup_logger("patch_toggle_handler")

class PatchToggleThread(QThread):
    """在后台线程中处理补丁切换逻辑"""
    finished = Signal(object)

    def __init__(self, handler, selected_folder):
        super().__init__()
        self.handler = handler
        self.selected_folder = selected_folder

    def run(self):
        # 在后台线程中执行耗时操作
        game_dirs = self.handler.game_detector.identify_game_directories_improved(self.selected_folder)
        self.finished.emit(game_dirs)

class PatchToggleHandler(QObject):
    """
    处理补丁启用/禁用功能的类
    """
    def __init__(self, main_window):
        """
        初始化补丁切换处理程序
        
        Args:
            main_window: 主窗口实例，用于访问其他组件
        """
        super().__init__()
        self.main_window = main_window
        self.debug_manager = main_window.debug_manager
        self.game_detector = main_window.game_detector
        self.patch_manager = main_window.patch_manager
        self.app_name = main_window.patch_manager.app_name
        self.toggle_thread = None
    
    def handle_toggle_patch_button_click(self):
        """
        处理禁/启用补丁按钮点击事件
        打开文件选择对话框选择游戏目录，然后禁用或启用对应游戏的补丁
        """
        selected_folder = QFileDialog.getExistingDirectory(self.main_window, "选择游戏上级目录", "")
        
        if not selected_folder:
            return

        self.main_window.show_loading_dialog("正在识别游戏目录并检查补丁状态...")
        
        self.toggle_thread = PatchToggleThread(self, selected_folder)
        self.toggle_thread.finished.connect(self.on_game_detection_finished)
        self.toggle_thread.start()

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
                is_disabled, _ = self.patch_manager.check_patch_disabled(game_dir, game_version)
                status = "已禁用" if is_disabled else "已启用"
                games_with_patch[game_version] = {"dir": game_dir, "status": status}
        
        if not games_with_patch:
            QMessageBox.information(
                self.main_window,
                f"提示 - {self.app_name}",
                "\n目录中未找到已安装补丁的游戏。\n",
            )
            return

        selected_games, operation = self._show_multi_game_dialog(games_with_patch)
        
        if not selected_games:
            return
        
        selected_game_dirs = {game: games_with_patch[game]["dir"] for game in selected_games if game in games_with_patch}
        
        self._execute_batch_toggle(selected_game_dirs, operation)
    
    def _handle_multiple_games(self, game_dirs, debug_mode):
        """
        处理多个游戏的补丁切换
        
        Args:
            game_dirs: 游戏目录字典
            debug_mode: 是否为调试模式
        """
        if debug_mode:
            logger.debug(f"DEBUG: 禁/启用功能 - 在上级目录中找到以下游戏: {list(game_dirs.keys())}")
        
        # 查找已安装补丁的游戏，只处理那些已安装补丁的游戏
        games_with_patch = {}
        for game_version, game_dir in game_dirs.items():
            if self.patch_manager.check_patch_installed(game_dir, game_version):
                # 检查补丁当前状态（是否禁用）
                is_disabled, disabled_path = self.patch_manager.check_patch_disabled(game_dir, game_version)
                status = "已禁用" if is_disabled else "已启用"
                games_with_patch[game_version] = {
                    "dir": game_dir,
                    "disabled": is_disabled,
                    "status": status
                }
                if debug_mode:
                    logger.debug(f"DEBUG: 禁/启用功能 - {game_version} 已安装补丁，当前状态: {status}")
        
        # 检查是否有已安装补丁的游戏
        if not games_with_patch:
            QMessageBox.information(
                self.main_window,
                f"提示 - {self.app_name}",
                "\n未在选择的目录中找到已安装补丁的游戏。\n请确认您选择了正确的游戏目录，并且该目录中的游戏已安装过补丁。\n",
                QMessageBox.StandardButton.Ok
            )
            return
        
        # 显示选择对话框
        selected_games, operation = self._show_multi_game_dialog(games_with_patch)
        
        if not selected_games:
            return  # 用户取消了操作
        
        # 过滤games_with_patch，只保留选中的游戏
        selected_game_dirs = {}
        for game in selected_games:
            if game in games_with_patch:
                selected_game_dirs[game] = games_with_patch[game]["dir"]
        
        # 确认操作
        operation_text = "禁用" if operation == "disable" else "启用" if operation == "enable" else "切换"
        game_list = '\n'.join([f"{game} ({games_with_patch[game]['status']})" for game in selected_games])
        reply = QMessageBox.question(
            self.main_window,
            f"确认{operation_text}操作 - {self.app_name}",
            f"\n确定要{operation_text}以下游戏补丁吗？\n\n{game_list}\n",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
            
        # 执行批量操作
        self._execute_batch_toggle(selected_game_dirs, operation, debug_mode)
    
    def _handle_single_game(self, selected_folder, debug_mode):
        """
        处理单个游戏的补丁切换
        
        Args:
            selected_folder: 选择的游戏目录
            debug_mode: 是否为调试模式
        """
        # 未找到游戏目录，尝试将选择的目录作为游戏目录
        if debug_mode:
            logger.debug(f"DEBUG: 禁/启用功能 - 未在上级目录找到游戏，尝试将选择的目录视为游戏目录")
            
        game_version = self.game_detector.identify_game_version(selected_folder)
        
        if game_version:
            if debug_mode:
                logger.debug(f"DEBUG: 禁/启用功能 - 识别为游戏: {game_version}")
            
            # 检查是否已安装补丁
            if self.patch_manager.check_patch_installed(selected_folder, game_version):
                # 检查补丁当前状态
                is_disabled, disabled_path = self.patch_manager.check_patch_disabled(selected_folder, game_version)
                current_status = "已禁用" if is_disabled else "已启用"
                
                # 显示单游戏操作对话框
                operation = self._show_single_game_dialog(game_version, current_status, is_disabled)
                
                if not operation:
                    return  # 用户取消了操作
                
                # 执行操作
                result = self.patch_manager.toggle_patch(selected_folder, game_version, operation=operation)
                if not result["success"]:
                    # 操作失败的消息已在toggle_patch中显示
                    pass
            else:
                # 没有安装补丁
                QMessageBox.information(
                    self.main_window,
                    f"提示 - {self.app_name}",
                    f"\n未在 {game_version} 中找到已安装的补丁。\n请确认该游戏已经安装过补丁。\n",
                    QMessageBox.StandardButton.Ok
                )
        else:
            # 两种方式都未识别到游戏
            if debug_mode:
                logger.debug(f"DEBUG: 禁/启用功能 - 无法识别游戏")
                
            msg_box = msgbox_frame(
                f"错误 - {self.app_name}",
                "\n所选目录不是有效的NEKOPARA游戏目录。\n请选择包含游戏可执行文件的目录或其上级目录。\n",
                QMessageBox.StandardButton.Ok,
            )
            msg_box.exec()
    
    def _show_multi_game_dialog(self, games_with_patch):
        """
        显示多游戏选择对话框
        
        Args:
            games_with_patch: 已安装补丁的游戏信息
            
        Returns:
            tuple: (选择的游戏列表, 操作类型)
        """
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("选择要操作的游戏补丁")
        dialog.resize(400, 400)  # 增加高度以适应新增的单选按钮
        
        layout = QVBoxLayout(dialog)
        
        # 添加"已安装补丁的游戏"标签
        already_installed_label = QLabel("已安装补丁的游戏:", dialog)
        already_installed_label.setFont(QFont(already_installed_label.font().family(), already_installed_label.font().pointSize(), QFont.Bold))
        layout.addWidget(already_installed_label)
        
        # 添加游戏列表和状态
        games_status_text = ""
        for game, info in games_with_patch.items():
            games_status_text += f"{game} ({info['status']})\n"
        games_status_label = QLabel(games_status_text.strip(), dialog)
        layout.addWidget(games_status_label)
        
        # 添加一些间距
        layout.addSpacing(10)
        
        # 添加"请选择要操作的游戏"标签
        info_label = QLabel("请选择要操作的游戏:", dialog)
        info_label.setFont(QFont(info_label.font().family(), info_label.font().pointSize(), QFont.Bold))
        layout.addWidget(info_label)
        
        # 添加列表控件，只显示已安装补丁的游戏
        list_widget = QListWidget(dialog)
        list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)  # 允许多选
        for game, info in games_with_patch.items():
            list_widget.addItem(f"{game} ({info['status']})")
        layout.addWidget(list_widget)
        
        # 添加全选按钮
        select_all_btn = QPushButton("全选", dialog)
        select_all_btn.clicked.connect(lambda: list_widget.selectAll())
        layout.addWidget(select_all_btn)
        
        # 添加操作选择单选按钮
        operation_label = QLabel("请选择要执行的操作:", dialog)
        operation_label.setFont(QFont(operation_label.font().family(), operation_label.font().pointSize(), QFont.Bold))
        layout.addWidget(operation_label)
        
        # 创建单选按钮组
        radio_button_group = QButtonGroup(dialog)
        
        # 添加"自动切换状态"单选按钮（默认选中）
        auto_toggle_radio = QRadioButton("自动切换状态（禁用<->启用）", dialog)
        auto_toggle_radio.setChecked(True)
        radio_button_group.addButton(auto_toggle_radio, 0)
        layout.addWidget(auto_toggle_radio)
        
        # 添加"全部禁用"单选按钮
        disable_all_radio = QRadioButton("禁用选中的补丁", dialog)
        radio_button_group.addButton(disable_all_radio, 1)
        layout.addWidget(disable_all_radio)
        
        # 添加"全部启用"单选按钮
        enable_all_radio = QRadioButton("启用选中的补丁", dialog)
        radio_button_group.addButton(enable_all_radio, 2)
        layout.addWidget(enable_all_radio)
        
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
            return [], None
            
        # 获取用户选择的游戏
        selected_items = [item.text() for item in list_widget.selectedItems()]
        selected_games = []
        
        # 从选中项文本中提取游戏名称
        for item in selected_items:
            # 去除状态后缀 " (已启用)" 或 " (已禁用)"
            game_name = item.split(" (")[0]
            selected_games.append(game_name)
        
        # 获取选中的操作类型
        operation = None
        if radio_button_group.checkedId() == 1:  # 禁用选中的补丁
            operation = "disable"
        elif radio_button_group.checkedId() == 2:  # 启用选中的补丁
            operation = "enable"
        # 否则为None，表示自动切换状态
        
        return selected_games, operation
    
    def _show_single_game_dialog(self, game_version, current_status, is_disabled):
        """
        显示单游戏操作对话框
        
        Args:
            game_version: 游戏版本
            current_status: 当前补丁状态
            is_disabled: 是否已禁用
            
        Returns:
            str: 操作类型，"enable"或"disable"，或None表示取消
        """
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle(f"{game_version} 补丁操作")
        dialog.resize(300, 200)
        
        layout = QVBoxLayout(dialog)
        
        # 添加当前状态标签
        status_label = QLabel(f"当前补丁状态: {current_status}", dialog)
        status_label.setFont(QFont(status_label.font().family(), status_label.font().pointSize(), QFont.Bold))
        layout.addWidget(status_label)
        
        # 添加操作选择单选按钮
        operation_label = QLabel("请选择要执行的操作:", dialog)
        layout.addWidget(operation_label)
        
        # 创建单选按钮组
        radio_button_group = QButtonGroup(dialog)
        
        # 添加可选操作
        if is_disabled:
            # 当前是禁用状态，显示启用选项
            enable_radio = QRadioButton("启用补丁", dialog)
            enable_radio.setChecked(True)
            radio_button_group.addButton(enable_radio, 0)
            layout.addWidget(enable_radio)
        else:
            # 当前是启用状态，显示禁用选项
            disable_radio = QRadioButton("禁用补丁", dialog)
            disable_radio.setChecked(True)
            radio_button_group.addButton(disable_radio, 0)
            layout.addWidget(disable_radio)
        
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
        
        if result != QDialog.DialogCode.Accepted:
            # 用户取消
            return None
        
        # 根据当前状态确定操作
        return "enable" if is_disabled else "disable"
    
    def _execute_batch_toggle(self, selected_game_dirs, operation, debug_mode):
        """
        执行批量补丁切换操作
        
        Args:
            selected_game_dirs: 选择的游戏目录
            operation: 操作类型
            debug_mode: 是否为调试模式
        """
        success_count = 0
        fail_count = 0
        results = []
        
        for game_version, game_dir in selected_game_dirs.items():
            try:
                # 使用静默模式进行操作
                result = self.patch_manager.toggle_patch(game_dir, game_version, operation=operation, silent=True)
                
                if result["success"]:
                    success_count += 1
                else:
                    fail_count += 1
                
                results.append({
                    "version": game_version,
                    "success": result["success"],
                    "message": result["message"],
                    "action": result["action"]
                })
                    
            except Exception as e:
                if debug_mode:
                    logger.error(f"DEBUG: 切换 {game_version} 补丁状态时出错: {str(e)}")
                fail_count += 1
                results.append({
                    "version": game_version,
                    "success": False,
                    "message": f"操作出错: {str(e)}",
                    "action": "none"
                })
        
        # 显示操作结果
        self.patch_manager.show_toggle_result(success_count, fail_count, results) 