from PySide6.QtGui import QIcon, QAction, QFont, QCursor
from PySide6.QtWidgets import QMessageBox, QMainWindow, QMenu, QPushButton
from PySide6.QtCore import Qt, QRect
import webbrowser
import os

from utils import load_base64_image, msgbox_frame, resource_path
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
        self.privacy_menu = None  # 隐私协议菜单
        self.about_menu = None    # 关于菜单
        self.about_btn = None     # 关于按钮
        
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
        
        # 创建关于按钮
        self._create_about_button()
        
        # 设置菜单
        self._setup_help_menu()
        self._setup_about_menu()  # 新增关于菜单
        self._setup_settings_menu()
    
    def _create_about_button(self):
        """创建"关于"按钮"""
        if not self.ui or not hasattr(self.ui, 'menu_area'):
            return
            
        # 获取菜单字体和样式
        menu_font = self._get_menu_font()
        
        # 创建关于按钮
        self.about_btn = QPushButton("关于", self.ui.menu_area)
        self.about_btn.setObjectName(u"about_btn")
        
        # 获取帮助按钮的位置和样式
        help_btn_x = 0
        help_btn_width = 0
        if hasattr(self.ui, 'help_btn'):
            help_btn_x = self.ui.help_btn.x()
            help_btn_width = self.ui.help_btn.width()
            
        # 设置位置在"帮助"按钮右侧
        self.about_btn.setGeometry(QRect(help_btn_x + help_btn_width + 20, 1, 80, 28))
        self.about_btn.setFont(menu_font)
        self.about_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # 复制帮助按钮的样式
        if hasattr(self.ui, 'help_btn'):
            self.about_btn.setStyleSheet(self.ui.help_btn.styleSheet())
        else:
            # 默认样式
            self.about_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    border: none;
                    text-align: left;
                    padding-left: 10px;
                }
                QPushButton:hover {
                    background-color: #F47A5B;
                    border-radius: 4px;
                }
                QPushButton:pressed {
                    background-color: #D25A3C;
                    border-radius: 4px;
                }
            """)
    
    def _setup_help_menu(self):
        """设置"帮助"菜单"""
        if not self.ui or not hasattr(self.ui, 'menu_2'):
            return

        # 获取菜单字体
        menu_font = self._get_menu_font()

        # 创建菜单项 - 移除"项目主页"，添加"常见问题"和"提交错误"
        faq_action = QAction("常见问题", self.main_window)
        faq_action.triggered.connect(self.open_faq_page)
        faq_action.setFont(menu_font)
        
        report_issue_action = QAction("提交错误", self.main_window)
        report_issue_action.triggered.connect(self.open_issues_page)
        report_issue_action.setFont(menu_font)
        
        # 清除现有菜单项并添加新的菜单项
        self.ui.menu_2.clear()
        self.ui.menu_2.addAction(faq_action)
        self.ui.menu_2.addAction(report_issue_action)
        
        # 连接按钮点击事件，如果使用按钮式菜单
        if hasattr(self.ui, 'help_btn'):
            # 按钮已经连接到显示菜单，不需要额外处理
            pass

    def _setup_about_menu(self):
        """设置"关于"菜单"""
        # 获取菜单字体
        menu_font = self._get_menu_font()
        
        # 创建关于菜单
        self.about_menu = QMenu("关于", self.main_window)
        self.about_menu.setFont(menu_font)
        
        # 设置菜单样式
        font_family = menu_font.family()
        menu_style = self._get_menu_style(font_family)
        self.about_menu.setStyleSheet(menu_style)
        
        # 创建菜单项
        about_project_action = QAction("关于本项目", self.main_window)
        about_project_action.setFont(menu_font)
        about_project_action.triggered.connect(self.show_about_dialog)
        
        # 添加项目主页选项（从帮助菜单移动过来）
        project_home_action = QAction("Github项目主页", self.main_window)
        project_home_action.setFont(menu_font)
        project_home_action.triggered.connect(self.open_project_home_page)
        
        # 添加加入QQ群选项
        qq_group_action = QAction("加入QQ群", self.main_window)
        qq_group_action.setFont(menu_font)
        qq_group_action.triggered.connect(self.open_qq_group)
        
        # 创建隐私协议菜单
        self._setup_privacy_menu()
        
        # 添加到关于菜单
        self.about_menu.addAction(about_project_action)
        self.about_menu.addAction(project_home_action)
        self.about_menu.addAction(qq_group_action)
        self.about_menu.addSeparator()
        self.about_menu.addMenu(self.privacy_menu)
        
        # 连接按钮点击事件
        if self.about_btn:
            self.about_btn.clicked.connect(lambda: self.show_menu(self.about_menu, self.about_btn))
    
    def _setup_privacy_menu(self):
        """设置"隐私协议"菜单"""
        # 获取菜单字体
        menu_font = self._get_menu_font()
        
        # 创建隐私协议子菜单
        self.privacy_menu = QMenu("隐私协议", self.main_window)
        self.privacy_menu.setFont(menu_font)
        
        # 设置与其他菜单一致的样式
        font_family = menu_font.family()
        menu_style = self._get_menu_style(font_family)
        self.privacy_menu.setStyleSheet(menu_style)
        
        # 添加子选项
        view_privacy_action = QAction("查看完整隐私协议", self.main_window)
        view_privacy_action.setFont(menu_font)
        view_privacy_action.triggered.connect(self.open_privacy_policy)
        
        revoke_privacy_action = QAction("撤回隐私协议", self.main_window)
        revoke_privacy_action.setFont(menu_font)
        revoke_privacy_action.triggered.connect(self.revoke_privacy_agreement)
        
        # 添加到子菜单
        self.privacy_menu.addAction(view_privacy_action)
        self.privacy_menu.addAction(revoke_privacy_action)

    def _get_menu_style(self, font_family):
        """获取统一的菜单样式"""
        return f"""
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

    def _get_menu_font(self):
        """获取菜单字体"""
        font_family = "Arial"  # 默认字体族
        
        try:
            from PySide6.QtGui import QFontDatabase
            
            # 尝试加载字体
            font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts", "SmileySans-Oblique.ttf")
            if os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            
            # 创建菜单字体
            menu_font = QFont(font_family, 14)
            menu_font.setBold(True)
            return menu_font
            
        except Exception as e:
            print(f"加载字体失败: {e}")
            # 返回默认字体
            menu_font = QFont(font_family, 14)
            menu_font.setBold(True)
            return menu_font
    
    def _setup_settings_menu(self):
        """设置"设置"菜单"""
        if not self.ui or not hasattr(self.ui, 'menu'):
            return

        # 获取菜单字体
        menu_font = self._get_menu_font()
        font_family = menu_font.family()

        # 创建开发者选项子菜单
        self.dev_menu = QMenu("开发者选项", self.main_window)
        self.dev_menu.setFont(menu_font)  # 设置与UI_install.py中相同的字体
        
        # 使用和主菜单相同的样式
        menu_style = self._get_menu_style(font_family)
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

    def show_menu(self, menu, button):
        """显示菜单
        
        Args:
            menu: 要显示的菜单
            button: 触发菜单的按钮
        """
        # 检查Ui_install中是否定义了show_menu方法
        if hasattr(self.ui, 'show_menu'):
            # 如果存在，使用UI中定义的方法
            self.ui.show_menu(menu, button)
        else:
            # 否则，使用默认的弹出方法
            global_pos = button.mapToGlobal(button.rect().bottomLeft())
            menu.popup(global_pos)

    def open_project_home_page(self):
        """打开项目主页"""
        webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT")
        
    def open_github_page(self):
        """打开项目GitHub页面"""
        webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT")
    
    def open_faq_page(self):
        """打开常见问题页面"""
        import locale
        # 根据系统语言选择FAQ页面
        system_lang = locale.getdefaultlocale()[0]
        if system_lang and system_lang.startswith('zh'):
            webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT/blob/master/FAQ.md")
        else:
            webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT/blob/master/FAQ-en.md")
    
    def open_issues_page(self):
        """打开GitHub问题页面"""
        webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT/issues")
    
    def open_qq_group(self):
        """打开QQ群链接"""
        webbrowser.open("https://qm.qq.com/q/g9i04i5eec")
        
    def open_privacy_policy(self):
        """打开完整隐私协议（在GitHub上）"""
        webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT/blob/master/PRIVACY.md")

    def revoke_privacy_agreement(self):
        """撤回隐私协议同意，并重启软件"""
        # 创建确认对话框
        msg_box = msgbox_frame(
            f"确认操作 - {APP_NAME}",
            "\n您确定要撤回隐私协议同意吗？\n\n撤回后软件将立即重启，您需要重新阅读并同意隐私协议。\n",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        
        reply = msg_box.exec()
        if reply == QMessageBox.StandardButton.Yes:
            # 用户确认撤回
            try:
                # 导入隐私管理器
                from core.privacy_manager import PrivacyManager
                import sys
                import subprocess
                import os
                
                # 创建实例并重置隐私协议同意
                privacy_manager = PrivacyManager()
                if privacy_manager.reset_privacy_agreement():
                    # 显示重启提示
                    restart_msg = msgbox_frame(
                        f"操作成功 - {APP_NAME}",
                        "\n已成功撤回隐私协议同意。\n\n软件将立即重启。\n",
                        QMessageBox.StandardButton.Ok,
                    )
                    restart_msg.exec()
                    
                    # 获取当前执行的Python解释器路径和脚本路径
                    python_executable = sys.executable
                    script_path = os.path.abspath(sys.argv[0])
                    
                    # 构建重启命令
                    restart_cmd = [python_executable, script_path]
                    
                    # 启动新进程
                    subprocess.Popen(restart_cmd)
                    
                    # 退出当前进程
                    sys.exit(0)
                else:
                    # 显示失败提示
                    fail_msg = msgbox_frame(
                        f"操作失败 - {APP_NAME}",
                        "\n撤回隐私协议同意失败。\n\n请检查应用权限或稍后再试。\n",
                        QMessageBox.StandardButton.Ok,
                    )
                    fail_msg.exec()
            except Exception as e:
                # 显示错误提示
                error_msg = msgbox_frame(
                    f"错误 - {APP_NAME}",
                    f"\n撤回隐私协议同意时发生错误：\n\n{str(e)}\n",
                    QMessageBox.StandardButton.Ok,
                )
                error_msg.exec()

    def show_about_dialog(self):
        """显示关于对话框"""
        about_text = f"""
            <p><b>{APP_NAME} v{APP_VERSION}</b></p>
            <p>GitHub: <a href="https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT">https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT</a></p>
            <p>原作: <a href="https://github.com/Yanam1Anna">Yanam1Anna</a></p>
            <p>此应用根据 <a href="https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT/blob/master/LICENSE">GPL-3.0 许可证</a> 授权。</p>
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