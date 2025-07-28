from PySide6.QtGui import QIcon, QAction, QFont
from PySide6.QtWidgets import QMessageBox, QMainWindow
from PySide6.QtCore import Qt
import webbrowser

from utils import load_base64_image, msgbox_frame
from data.config import APP_NAME, APP_VERSION

class UIManager:
    def __init__(self, main_window):
        """初始化UI管理器
        
        Args:
            main_window: 主窗口实例，用于设置UI元素
        """
        self.main_window = main_window
        # 使用getattr获取ui属性，如果不存在则为None
        self.ui = getattr(main_window, 'ui', None)
        self.debug_action = None
        
    def setup_ui(self):
        """设置UI元素，包括窗口图标、标题和菜单"""
        # 设置窗口图标
        import os
        from utils import resource_path
        icon_path = resource_path(os.path.join("IMG", "ICO", "icon.png"))
        if os.path.exists(icon_path):
            self.main_window.setWindowIcon(QIcon(icon_path))

        # 设置窗口标题
        self.main_window.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        
        # 设置菜单
        self._setup_help_menu()
        self._setup_settings_menu()
    
    def _setup_help_menu(self):
        """设置"帮助"菜单"""
        if not self.ui or not hasattr(self.ui, 'menu_2'):
            return

        # 创建菜单项
        project_home_action = QAction("项目主页", self.main_window)
        project_home_action.triggered.connect(self.open_project_home_page)
        
        about_action = QAction("关于", self.main_window)
        about_action.triggered.connect(self.show_about_dialog)
        
        # 添加到菜单
        self.ui.menu_2.addAction(project_home_action)
        self.ui.menu_2.addAction(about_action)
        
        # 连接按钮点击事件，如果使用按钮式菜单
        if hasattr(self.ui, 'help_btn'):
            # 按钮已经连接到显示菜单，不需要额外处理
            pass
    
    def _setup_settings_menu(self):
        """设置"设置"菜单"""
        if not self.ui or not hasattr(self.ui, 'menu'):
            return

        # 创建菜单项
        self.debug_action = QAction("Debug模式", self.main_window, checkable=True)
        
        # 安全地获取config属性
        config = getattr(self.main_window, 'config', {})
        debug_mode = False
        if isinstance(config, dict):
            debug_mode = config.get("debug_mode", False)
        
        self.debug_action.setChecked(debug_mode)
        
        # 安全地连接toggle_debug_mode方法
        if hasattr(self.main_window, 'toggle_debug_mode'):
            self.debug_action.triggered.connect(self.main_window.toggle_debug_mode)
            
        # 添加到菜单
        self.ui.menu.addAction(self.debug_action)

        # 为未来功能预留的"切换下载源"按钮
        self.switch_source_action = QAction("切换下载源", self.main_window)
        self.switch_source_action.setEnabled(False)  # 暂时禁用
        self.ui.menu.addAction(self.switch_source_action)
        
        # 添加分隔符
        self.ui.menu.addSeparator()
        
        # 连接按钮点击事件，如果使用按钮式菜单
        if hasattr(self.ui, 'settings_btn'):
            # 按钮已经连接到显示菜单，不需要额外处理
            pass

    def open_project_home_page(self):
        """打开项目主页"""
        webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT")

    def show_about_dialog(self):
        """显示关于对话框"""
        about_text = f"""
            <p><b>{APP_NAME} v{APP_VERSION}</b></p>
            <p>原作: <a href="https://github.com/Yanam1Anna">Yanam1Anna</a></p>
            <p>此应用根据 <a href="https://github.com/hyb-oyqq/FRAISEMOE2-Installer/blob/master/LICENSE">GPL-3.0 许可证</a> 授权。</p>
        """
        msg_box = msgbox_frame(
            f"关于 - {APP_NAME}",
            about_text,
            QMessageBox.StandardButton.Ok,
        )
        msg_box.setTextFormat(Qt.TextFormat.RichText)  # 使用Qt.TextFormat
        msg_box.exec() 