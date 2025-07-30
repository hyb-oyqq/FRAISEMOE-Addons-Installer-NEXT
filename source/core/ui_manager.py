from PySide6.QtGui import QIcon, QAction, QFont
from PySide6.QtWidgets import QMessageBox, QMainWindow, QMenu
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
        self.turbo_download_action = None
        self.dev_menu = None
        
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

        # 获取自定义字体和字体族名称
        font_family = "Arial"  # 默认字体族
        menu_font = None

        # 尝试从UI中获取字体和字体族
        try:
            # 优先从Ui_install.py中获取font_family变量
            import os
            from PySide6.QtGui import QFontDatabase
            
            # 尝试直接加载字体并获取字体族
            font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts", "SmileySans-Oblique.ttf")
            if os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
                    # 创建与UI_install.py中完全相同的菜单字体
                    menu_font = QFont(font_family, 14)  # 字体大小为14
                    menu_font.setBold(True)  # 设置粗体
            
            # 如果以上方法失败，则尝试从ui获取字体
            if not menu_font and hasattr(self.ui, 'menu') and self.ui.menu:
                menu_font = self.ui.menu.font()
            
            # 如果仍然没有获取到，使用默认字体
            if not menu_font:
                menu_font = QFont(font_family, 14)
                menu_font.setBold(True)
                
        except:
            # 如果出错，使用默认字体
            menu_font = QFont(font_family, 14)
            menu_font.setBold(True)

        # 创建开发者选项子菜单
        self.dev_menu = QMenu("开发者选项", self.main_window)
        self.dev_menu.setFont(menu_font)  # 设置与UI_install.py中相同的字体
        
        # 使用和主菜单相同的样式，直接指定字体族、字体大小和粗细
        menu_style = f"""
            QMenu {{
                background-color: #E96948;
                color: white;
                font-family: "{font_family}";
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #F47A5B;
                padding: 8px;
                border-radius: 6px;
                margin-top: 2px;
            }}
            QMenu::item {{
                padding: 6px 20px 6px 15px;
                background-color: transparent;
                min-width: 120px;
                color: white;
                font-family: "{font_family}";
                font-size: 14px;
                font-weight: bold;
            }}
            QMenu::item:selected {{
                background-color: #F47A5B;
                border-radius: 4px;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: #F47A5B;
                margin: 5px 15px;
            }}
            QMenu::item:checked {{
                background-color: #D25A3C;
                border-radius: 4px;
            }}
        """
        self.dev_menu.setStyleSheet(menu_style)
        
        # 创建Debug模式选项并添加到开发者选项子菜单中
        self.debug_action = QAction("Debug模式", self.main_window, checkable=True)
        self.debug_action.setFont(menu_font)  # 设置相同的字体
        
        # 安全地获取config属性
        config = getattr(self.main_window, 'config', {})
        debug_mode = False
        if isinstance(config, dict):
            debug_mode = config.get("debug_mode", False)
        
        self.debug_action.setChecked(debug_mode)
        
        # 安全地连接toggle_debug_mode方法
        if hasattr(self.main_window, 'toggle_debug_mode'):
            self.debug_action.triggered.connect(self.main_window.toggle_debug_mode)
        
        # 创建狂暴下载选项（无功能）
        self.turbo_download_action = QAction("狂暴下载", self.main_window)
        self.turbo_download_action.setFont(menu_font)  # 设置自定义字体
        self.turbo_download_action.setEnabled(False)  # 禁用按钮
        
        # 添加到开发者选项子菜单
        self.dev_menu.addAction(self.debug_action)
        self.dev_menu.addAction(self.turbo_download_action)
        
        # 为未来功能预留的"切换下载源"按钮
        self.switch_source_action = QAction("切换下载源", self.main_window)
        self.switch_source_action.setFont(menu_font)  # 设置自定义字体
        self.switch_source_action.setEnabled(False)  # 暂时禁用
        
        # 添加到主菜单
        self.ui.menu.addAction(self.switch_source_action)
        self.ui.menu.addSeparator()
        self.ui.menu.addMenu(self.dev_menu)  # 添加开发者选项子菜单
        
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
            <br>
            <p><b>感谢:</b></p>
            <p>- <a href="https://github.com/HTony03">HTony03</a>：对原项目部分源码的重构、逻辑优化和功能实现提供了支持。</p>
            <p>- <a href="https://github.com/ABSIDIA">钨鸮</a>：对于云端资源存储提供了支持。</p>
            <p>- <a href="https://github.com/XIU2/CloudflareSpeedTest">XIU2/CloudflareSpeedTest</a>：提供了 IP 优选功能的核心支持。</p>
        """
        msg_box = msgbox_frame(
            f"关于 - {APP_NAME}",
            about_text,
            QMessageBox.StandardButton.Ok,
        )
        msg_box.setTextFormat(Qt.TextFormat.RichText)  # 使用Qt.TextFormat
        msg_box.exec() 