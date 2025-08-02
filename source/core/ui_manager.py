from PySide6.QtGui import QIcon, QAction, QFont, QCursor
from PySide6.QtWidgets import QMessageBox, QMainWindow, QMenu, QPushButton
from PySide6.QtCore import Qt, QRect
import webbrowser
import os

from utils import load_base64_image, msgbox_frame, resource_path
from data.config import APP_NAME, APP_VERSION, LOG_FILE

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
        
        # 创建Debug子菜单
        self.debug_submenu = QMenu("Debug模式", self.main_window)
        self.debug_submenu.setFont(menu_font)
        self.debug_submenu.setStyleSheet(menu_style)
        
        # 创建hosts文件选项子菜单
        self.hosts_submenu = QMenu("hosts文件选项", self.main_window)
        self.hosts_submenu.setFont(menu_font)
        self.hosts_submenu.setStyleSheet(menu_style)
        
        # 添加IPv6支持选项
        self.ipv6_action = QAction("启用IPv6支持", self.main_window, checkable=True)
        self.ipv6_action.setFont(menu_font)
        
        # 添加IPv6检测按钮，用于显示详细信息
        self.ipv6_test_action = QAction("测试IPv6连接", self.main_window)
        self.ipv6_test_action.setFont(menu_font)
        self.ipv6_test_action.triggered.connect(self.show_ipv6_details)
        
        # 创建IPv6支持子菜单
        self.ipv6_submenu = QMenu("IPv6支持", self.main_window)
        self.ipv6_submenu.setFont(menu_font)
        self.ipv6_submenu.setStyleSheet(menu_style)
        
        # 检查IPv6是否可用
        ipv6_available = self._check_ipv6_availability()
        
        if not ipv6_available:
            self.ipv6_action.setText("启用IPv6支持 (不可用)")
            self.ipv6_action.setEnabled(False)
            self.ipv6_action.setToolTip("未检测到可用的IPv6连接")
        
        # 检查配置中是否已启用IPv6
        config = getattr(self.main_window, 'config', {})
        ipv6_enabled = False
        if isinstance(config, dict):
            ipv6_enabled = config.get("ipv6_enabled", False)
            # 如果配置中启用了IPv6但实际不可用，则强制禁用
            if ipv6_enabled and not ipv6_available:
                config["ipv6_enabled"] = False
                ipv6_enabled = False
                # 使用utils.save_config直接保存配置
                from utils import save_config
                save_config(config)
        
        self.ipv6_action.setChecked(ipv6_enabled)
        
        # 连接IPv6支持切换事件
        self.ipv6_action.triggered.connect(self.toggle_ipv6_support)
        
        # 将选项添加到IPv6子菜单
        self.ipv6_submenu.addAction(self.ipv6_action)
        self.ipv6_submenu.addAction(self.ipv6_test_action)
        
        # 添加hosts子选项
        self.restore_hosts_action = QAction("还原软件备份的hosts文件", self.main_window)
        self.restore_hosts_action.setFont(menu_font)
        self.restore_hosts_action.triggered.connect(self.restore_hosts_backup)
        
        self.clean_hosts_action = QAction("手动删除软件添加的hosts条目", self.main_window)
        self.clean_hosts_action.setFont(menu_font)
        self.clean_hosts_action.triggered.connect(self.clean_hosts_entries)
        
        # 添加到hosts子菜单
        self.hosts_submenu.addAction(self.restore_hosts_action)
        self.hosts_submenu.addAction(self.clean_hosts_action)
        
        # 创建Debug开关选项
        self.debug_action = QAction("Debug开关", self.main_window, checkable=True)
        self.debug_action.setFont(menu_font)
        
        # 安全地获取config属性
        config = getattr(self.main_window, 'config', {})
        debug_mode = False
        if isinstance(config, dict):
            debug_mode = config.get("debug_mode", False)
        
        self.debug_action.setChecked(debug_mode)
        
        # 安全地连接toggle_debug_mode方法
        if hasattr(self.main_window, 'toggle_debug_mode'):
            self.debug_action.triggered.connect(self.main_window.toggle_debug_mode)
        
        # 创建打开log文件选项
        self.open_log_action = QAction("打开log.txt", self.main_window)
        self.open_log_action.setFont(menu_font)
        # 初始状态根据debug模式设置启用状态
        self.open_log_action.setEnabled(debug_mode)
        
        # 连接打开log文件的事件
        self.open_log_action.triggered.connect(self.open_log_file)
        
        # 添加到Debug子菜单
        self.debug_submenu.addAction(self.debug_action)
        self.debug_submenu.addAction(self.open_log_action)
        
        # 创建下载设置子菜单
        self.download_settings_menu = QMenu("下载设置", self.main_window)
        self.download_settings_menu.setFont(menu_font)
        self.download_settings_menu.setStyleSheet(menu_style)
        
        # "修改下载源"按钮移至下载设置菜单
        self.switch_source_action = QAction("修改下载源", self.main_window)
        self.switch_source_action.setFont(menu_font)
        self.switch_source_action.setEnabled(True)
        self.switch_source_action.triggered.connect(self.show_under_development)
        
        # 添加下载线程设置选项
        self.thread_settings_action = QAction("下载线程设置", self.main_window)
        self.thread_settings_action.setFont(menu_font)
        # 连接到下载线程设置对话框
        self.thread_settings_action.triggered.connect(self.show_download_thread_settings)
        
        # 添加到下载设置子菜单
        self.download_settings_menu.addAction(self.switch_source_action)
        self.download_settings_menu.addAction(self.thread_settings_action)
        
        # 添加到主菜单
        self.ui.menu.addMenu(self.download_settings_menu)  # 添加下载设置子菜单
        self.ui.menu.addSeparator()
        self.ui.menu.addMenu(self.dev_menu)  # 添加开发者选项子菜单
        
        # 添加Debug子菜单到开发者选项菜单
        self.dev_menu.addMenu(self.debug_submenu)
        self.dev_menu.addMenu(self.hosts_submenu) # 添加hosts文件选项子菜单
        self.dev_menu.addMenu(self.ipv6_submenu)  # 添加IPv6支持子菜单
        
    def _check_ipv6_availability(self):
        """检查IPv6是否可用
        
        通过访问IPv6专用图片URL测试IPv6连接
        
        Returns:
            bool: IPv6是否可用
        """
        import urllib.request
        import ssl
        import time
        
        print("开始检测IPv6可用性...")
        
        # IPv6测试URL - 这是一个只能通过IPv6访问的资源
        ipv6_test_url = "https://ipv6.testipv6.cn/images-nc/knob_green.png?&testdomain=www.test-ipv6.com&testname=sites"
        
        try:
            # 设置3秒超时，避免长时间等待
            context = ssl._create_unverified_context()
            
            # 创建请求并添加常见的HTTP头
            req = urllib.request.Request(ipv6_test_url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            req.add_header('Accept', 'image/webp,image/apng,image/*,*/*;q=0.8')
            
            # 尝试连接
            start_time = time.time()
            with urllib.request.urlopen(req, timeout=3, context=context) as response:
                # 读取图片数据
                image_data = response.read()
                
                # 检查是否成功
                if response.status == 200 and len(image_data) > 0:
                    elapsed = time.time() - start_time
                    print(f"IPv6测试成功! 用时: {elapsed:.2f}秒")
                    return True
                else:
                    print(f"IPv6测试失败: 状态码 {response.status}")
                    return False
        except Exception as e:
            print(f"IPv6测试失败: {e}")
            return False
    
    def show_ipv6_details(self):
        """显示IPv6连接详情"""
        import threading
        import urllib.request
        import ssl
        import time
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit, QProgressBar
        from PySide6.QtCore import Signal, QObject
        
        class SignalEmitter(QObject):
            update_signal = Signal(str)
            complete_signal = Signal(bool, float)
        
        # 创建对话框
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle(f"IPv6连接测试 - {APP_NAME}")
        dialog.resize(500, 300)
        
        # 创建布局
        layout = QVBoxLayout(dialog)
        
        # 创建状态标签
        status_label = QLabel("正在测试IPv6连接...", dialog)
        layout.addWidget(status_label)
        
        # 创建进度条
        progress = QProgressBar(dialog)
        progress.setRange(0, 0)  # 不确定进度
        layout.addWidget(progress)
        
        # 创建结果文本框
        result_text = QTextEdit(dialog)
        result_text.setReadOnly(True)
        layout.addWidget(result_text)
        
        # 创建关闭按钮
        close_button = QPushButton("关闭", dialog)
        close_button.clicked.connect(dialog.accept)
        close_button.setEnabled(False)  # 测试完成前禁用
        layout.addWidget(close_button)
        
        # 信号发射器
        signal_emitter = SignalEmitter()
        
        # 连接信号
        signal_emitter.update_signal.connect(
            lambda text: result_text.append(text)
        )
        
        def on_test_complete(success, elapsed_time):
            # 停止进度条动画
            progress.setRange(0, 100)
            progress.setValue(100 if success else 0)
            
            # 更新状态
            if success:
                status_label.setText(f"IPv6连接测试完成: 可用 (用时: {elapsed_time:.2f}秒)")
            else:
                status_label.setText("IPv6连接测试完成: 不可用")
            
            # 启用关闭按钮
            close_button.setEnabled(True)
        
        signal_emitter.complete_signal.connect(on_test_complete)
        
        # 测试函数
        def test_ipv6():
            try:
                signal_emitter.update_signal.emit("正在测试IPv6连接，请稍候...")
                
                # 使用与_check_ipv6_availability相同的测试URL
                ipv6_test_url = "https://ipv6.testipv6.cn/images-nc/knob_green.png?&testdomain=www.test-ipv6.com&testname=sites"
                
                try:
                    # 设置3秒超时
                    context = ssl._create_unverified_context()
                    req = urllib.request.Request(ipv6_test_url)
                    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
                    req.add_header('Accept', 'image/webp,image/apng,image/*,*/*;q=0.8')
                    
                    # 记录开始时间
                    start_time = time.time()
                    signal_emitter.update_signal.emit(f"开始连接: {ipv6_test_url}")
                    
                    # 尝试下载图片
                    with urllib.request.urlopen(req, timeout=5, context=context) as response:
                        image_data = response.read()
                        
                        # 计算耗时
                        elapsed_time = time.time() - start_time
                        
                        # 检查是否成功
                        if response.status == 200 and len(image_data) > 0:
                            signal_emitter.update_signal.emit(f"✓ 成功! 已下载 {len(image_data)} 字节")
                            signal_emitter.update_signal.emit(f"✓ 响应时间: {elapsed_time:.2f}秒")
                            signal_emitter.update_signal.emit("\n结论: 您的网络支持IPv6连接 ✓")
                            signal_emitter.complete_signal.emit(True, elapsed_time)
                            return
                        else:
                            signal_emitter.update_signal.emit(f"✗ 失败: 状态码 {response.status}")
                            signal_emitter.update_signal.emit("\n结论: 您的网络不支持IPv6连接 ✗")
                            signal_emitter.complete_signal.emit(False, 0)
                            return
                            
                except Exception as e:
                    signal_emitter.update_signal.emit(f"✗ 连接失败: {e}")
                    signal_emitter.update_signal.emit("\n结论: 您的网络不支持IPv6连接 ✗")
                    signal_emitter.complete_signal.emit(False, 0)
                
            except Exception as e:
                signal_emitter.update_signal.emit(f"测试过程中出错: {e}")
                signal_emitter.complete_signal.emit(False, 0)
        
        # 启动测试线程
        threading.Thread(target=test_ipv6, daemon=True).start()
        
        # 显示对话框
        dialog.exec()
        
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

    def show_under_development(self):
        """显示功能正在开发中的提示"""
        msg_box = msgbox_frame(
            f"提示 - {APP_NAME}",
            "\n该功能正在开发中，敬请期待！\n",
            QMessageBox.StandardButton.Ok,
        )
        msg_box.exec()
        
    def show_download_thread_settings(self):
        """显示下载线程设置对话框"""
        if hasattr(self.main_window, 'download_manager'):
            self.main_window.download_manager.show_download_thread_settings()
        else:
            # 如果下载管理器不可用，显示错误信息
            msg_box = msgbox_frame(
                f"错误 - {APP_NAME}",
                "\n下载管理器未初始化，无法修改下载线程设置。\n",
                QMessageBox.StandardButton.Ok,
            )
            msg_box.exec()
        
    def open_log_file(self):
        """打开log.txt文件"""
        if os.path.exists(LOG_FILE):
            try:
                # 使用操作系统默认程序打开日志文件
                if os.name == 'nt':  # Windows
                    os.startfile(LOG_FILE)
                else:  # macOS 和 Linux
                    import subprocess
                    subprocess.call(['xdg-open', LOG_FILE])
            except Exception as e:
                msg_box = msgbox_frame(
                    f"错误 - {APP_NAME}",
                    f"\n打开log.txt文件失败：\n\n{str(e)}\n",
                    QMessageBox.StandardButton.Ok,
                )
                msg_box.exec()
        else:
            msg_box = msgbox_frame(
                f"提示 - {APP_NAME}",
                "\nlog.txt文件不存在，请确保Debug模式已开启并生成日志。\n",
                QMessageBox.StandardButton.Ok,
            )
            msg_box.exec()
            
    def restore_hosts_backup(self):
        """还原软件备份的hosts文件"""
        if hasattr(self.main_window, 'download_manager') and hasattr(self.main_window.download_manager, 'hosts_manager'):
            try:
                # 调用恢复hosts文件的方法
                result = self.main_window.download_manager.hosts_manager.restore()
                
                if result:
                    msg_box = msgbox_frame(
                        f"成功 - {APP_NAME}",
                        "\nhosts文件已成功还原为备份版本。\n",
                        QMessageBox.StandardButton.Ok,
                    )
                else:
                    msg_box = msgbox_frame(
                        f"警告 - {APP_NAME}",
                        "\n还原hosts文件失败或没有找到备份文件。\n",
                        QMessageBox.StandardButton.Ok,
                    )
                
                msg_box.exec()
            except Exception as e:
                msg_box = msgbox_frame(
                    f"错误 - {APP_NAME}",
                    f"\n还原hosts文件时发生错误：\n\n{str(e)}\n",
                    QMessageBox.StandardButton.Ok,
                )
                msg_box.exec()
        else:
            msg_box = msgbox_frame(
                f"错误 - {APP_NAME}",
                "\n无法访问hosts管理器。\n",
                QMessageBox.StandardButton.Ok,
            )
            msg_box.exec()
            
    def toggle_ipv6_support(self, enabled):
        """切换IPv6支持
        
        Args:
            enabled: 是否启用IPv6支持
        """
        print(f"Toggle IPv6 support: {enabled}")
        
        # 如果用户尝试启用IPv6，检查系统是否支持IPv6并发出警告
        if enabled:
            # 先显示警告提示
            warning_msg_box = msgbox_frame(
                f"警告 - {APP_NAME}",
                "\n目前IPv6支持功能仍在测试阶段，可能会发生意料之外的bug！\n\n您确定需要启用吗？\n",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            response = warning_msg_box.exec()
            
            # 如果用户选择不启用，直接返回
            if response != QMessageBox.StandardButton.Yes:
                self.ipv6_action.setChecked(False)
                return
            
            # 用户确认启用后，继续检查IPv6可用性
            ipv6_available = self._check_ipv6_availability()
                
            if not ipv6_available:
                msg_box = msgbox_frame(
                    f"错误 - {APP_NAME}",
                    "\n未检测到可用的IPv6连接，无法启用IPv6支持。\n\n请确保您的网络环境支持IPv6且已正确配置。\n",
                    QMessageBox.StandardButton.Ok,
                )
                msg_box.exec()
                
                # 恢复复选框状态
                self.ipv6_action.setChecked(False)
                return
                
        # 保存设置到配置
        if hasattr(self.main_window, 'config'):
            self.main_window.config["ipv6_enabled"] = enabled
            # 直接使用utils.save_config保存配置
            from utils import save_config
            save_config(self.main_window.config)
            
        # 显示设置已保存的消息
        status = "启用" if enabled else "禁用"
        msg_box = msgbox_frame(
            f"IPv6设置 - {APP_NAME}",
            f"\nIPv6支持已{status}。新的设置将在下一次下载时生效。\n",
            QMessageBox.StandardButton.Ok,
        )
        msg_box.exec()
            
    def clean_hosts_entries(self):
        """手动删除软件添加的hosts条目"""
        if hasattr(self.main_window, 'download_manager') and hasattr(self.main_window.download_manager, 'hosts_manager'):
            try:
                # 调用清理hosts条目的方法
                result = self.main_window.download_manager.hosts_manager.check_and_clean_all_entries()
                
                if result:
                    msg_box = msgbox_frame(
                        f"成功 - {APP_NAME}",
                        "\n已成功清理软件添加的hosts条目。\n",
                        QMessageBox.StandardButton.Ok,
                    )
                else:
                    msg_box = msgbox_frame(
                        f"提示 - {APP_NAME}",
                        "\n未发现软件添加的hosts条目或清理操作失败。\n",
                        QMessageBox.StandardButton.Ok,
                    )
                
                msg_box.exec()
            except Exception as e:
                msg_box = msgbox_frame(
                    f"错误 - {APP_NAME}",
                    f"\n清理hosts条目时发生错误：\n\n{str(e)}\n",
                    QMessageBox.StandardButton.Ok,
                )
                msg_box.exec()
        else:
            msg_box = msgbox_frame(
                f"错误 - {APP_NAME}",
                "\n无法访问hosts管理器。\n",
                QMessageBox.StandardButton.Ok,
            )
            msg_box.exec()

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
            <p>- <a href="https://github.com/hosxy/aria2-fast">hosxy/aria2-fast</a>：提供了修改版aria2c，提高了下载速度和性能。</p>
        """
        msg_box = msgbox_frame(
            f"关于 - {APP_NAME}",
            about_text,
            QMessageBox.StandardButton.Ok,
        )
        msg_box.setTextFormat(Qt.TextFormat.RichText)  # 使用Qt.TextFormat
        msg_box.exec() 