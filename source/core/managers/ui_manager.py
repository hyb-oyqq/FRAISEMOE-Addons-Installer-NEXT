from PySide6.QtGui import QIcon, QAction, QFont, QCursor, QActionGroup
from PySide6.QtWidgets import QMessageBox, QMainWindow, QMenu, QPushButton, QDialog, QVBoxLayout, QProgressBar, QLabel
from PySide6.QtCore import Qt, QRect
import webbrowser
import os
import logging
import traceback

from utils import load_base64_image, msgbox_frame, resource_path
from config.config import APP_NAME, APP_VERSION, LOG_FILE
from core.managers.ipv6_manager import IPv6Manager  # 导入新的IPv6Manager类

logger = logging.getLogger(__name__)

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
        self.loading_dialog = None # 添加loading_dialog实例变量
        
        # 获取主窗口的IPv6Manager实例
        self.ipv6_manager = getattr(main_window, 'ipv6_manager', None)
        
    def setup_ui(self):
        """设置UI元素，包括窗口图标、标题和菜单"""
        # 设置窗口图标
        import os
        from utils import resource_path
        icon_path = resource_path(os.path.join("assets", "images", "ICO", "icon.png"))
        if os.path.exists(icon_path):
            self.main_window.setWindowIcon(QIcon(icon_path))

        # 获取当前离线模式状态
        is_offline_mode = False
        if hasattr(self.main_window, 'offline_mode_manager'):
            is_offline_mode = self.main_window.offline_mode_manager.is_in_offline_mode()
            
        # 设置窗口标题和UI标题标签
        mode_indicator = "[离线模式]" if is_offline_mode else "[在线模式]"
        self.main_window.setWindowTitle(f"{APP_NAME} v{APP_VERSION} {mode_indicator}")
        
        # 更新UI中的标题标签
        if hasattr(self.main_window, 'ui') and hasattr(self.main_window.ui, 'title_label'):
            self.main_window.ui.title_label.setText(f"{APP_NAME} v{APP_VERSION} {mode_indicator}")
        
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
            from utils import resource_path
            
            # 使用resource_path查找字体文件
            font_path = resource_path(os.path.join("assets", "fonts", "SmileySans-Oblique.ttf"))
            
            # 详细记录字体加载过程
            if os.path.exists(font_path):
                logger.info(f"尝试加载字体文件: {font_path}")
                font_id = QFontDatabase.addApplicationFont(font_path)
                
                if font_id != -1:
                    font_families = QFontDatabase.applicationFontFamilies(font_id)
                    if font_families:
                        font_family = font_families[0]
                        logger.info(f"成功加载字体: {font_family} 从 {font_path}")
                    else:
                        logger.warning(f"字体加载成功但无法获取字体族: {font_path}")
                else:
                    logger.warning(f"字体加载失败: {font_path} (返回ID: {font_id})")
                    
                    # 检查文件大小和是否可读
                    try:
                        file_size = os.path.getsize(font_path)
                        logger.debug(f"字体文件大小: {file_size} 字节")
                        if file_size == 0:
                            logger.error(f"字体文件大小为0字节: {font_path}")
                        
                        # 尝试打开文件测试可读性
                        with open(font_path, 'rb') as f:
                            # 只读取前几个字节测试可访问性
                            f.read(10)
                            logger.debug(f"字体文件可以正常打开和读取")
                    except Exception as file_error:
                        logger.error(f"字体文件访问错误: {file_error}")
            else:
                logger.error(f"找不到字体文件: {font_path}")
                
                # 尝试列出assets/fonts目录下的文件
                try:
                    fonts_dir = os.path.dirname(font_path)
                    if os.path.exists(fonts_dir):
                        files = os.listdir(fonts_dir)
                        logger.debug(f"字体目录 {fonts_dir} 中的文件: {files}")
                    else:
                        logger.debug(f"字体目录不存在: {fonts_dir}")
                except Exception as dir_error:
                    logger.error(f"无法列出字体目录内容: {dir_error}")
            
            # 创建菜单字体
            menu_font = QFont(font_family, 14)
            menu_font.setBold(True)
            return menu_font
            
        except Exception as e:
            logger.error(f"加载字体过程中发生异常: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
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

        # 创建工作模式子菜单
        self.work_mode_menu = QMenu("工作模式", self.main_window)
        self.work_mode_menu.setFont(menu_font)
        self.work_mode_menu.setStyleSheet(self._get_menu_style(font_family))
        
        # 获取当前离线模式状态
        is_offline_mode = False
        if hasattr(self.main_window, 'offline_mode_manager'):
            is_offline_mode = self.main_window.offline_mode_manager.is_in_offline_mode()
        
        # 创建在线模式和离线模式选项
        self.online_mode_action = QAction("在线模式", self.main_window, checkable=True)
        self.online_mode_action.setFont(menu_font)
        self.online_mode_action.setChecked(not is_offline_mode)  # 根据当前状态设置
        
        self.offline_mode_action = QAction("离线模式", self.main_window, checkable=True)
        self.offline_mode_action.setFont(menu_font)
        self.offline_mode_action.setChecked(is_offline_mode)  # 根据当前状态设置
        
        # 将两个模式选项添加到同一个互斥组
        mode_group = QActionGroup(self.main_window)
        mode_group.addAction(self.online_mode_action)
        mode_group.addAction(self.offline_mode_action)
        mode_group.setExclusive(True)  # 确保只能选择一个模式
        
        # 连接切换事件
        self.online_mode_action.triggered.connect(lambda: self.switch_work_mode("online"))
        self.offline_mode_action.triggered.connect(lambda: self.switch_work_mode("offline"))
        
        # 添加到工作模式子菜单
        self.work_mode_menu.addAction(self.online_mode_action)
        self.work_mode_menu.addAction(self.offline_mode_action)

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
        if self.ipv6_manager:
            self.ipv6_test_action.triggered.connect(self.ipv6_manager.show_ipv6_details)
        else:
            self.ipv6_test_action.triggered.connect(self.show_ipv6_manager_not_ready)
        
        # 创建IPv6支持子菜单
        self.ipv6_submenu = QMenu("IPv6支持", self.main_window)
        self.ipv6_submenu.setFont(menu_font)
        self.ipv6_submenu.setStyleSheet(menu_style)
        
        # 检查配置中是否已启用IPv6
        config = getattr(self.main_window, 'config', {})
        ipv6_enabled = False
        if isinstance(config, dict):
            ipv6_enabled = config.get("ipv6_enabled", False)
        
        self.ipv6_action.setChecked(ipv6_enabled)
        
        # 连接IPv6支持切换事件
        self.ipv6_action.triggered.connect(self._handle_ipv6_toggle)
        
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
        
        # 添加禁用自动还原hosts的选项
        self.disable_auto_restore_action = QAction("禁用关闭/重启自动还原hosts", self.main_window, checkable=True)
        self.disable_auto_restore_action.setFont(menu_font)
        
        # 从配置中读取当前状态
        config = getattr(self.main_window, 'config', {})
        disable_auto_restore = False
        if isinstance(config, dict):
            disable_auto_restore = config.get("disable_auto_restore_hosts", False)
        
        self.disable_auto_restore_action.setChecked(disable_auto_restore)
        self.disable_auto_restore_action.triggered.connect(self.toggle_disable_auto_restore_hosts)
        
        # 添加打开hosts文件选项
        self.open_hosts_action = QAction("打开hosts文件", self.main_window)
        self.open_hosts_action.setFont(menu_font)
        self.open_hosts_action.triggered.connect(self.open_hosts_file)
        
        # 添加到hosts子菜单
        self.hosts_submenu.addAction(self.disable_auto_restore_action)
        self.hosts_submenu.addAction(self.restore_hosts_action)
        self.hosts_submenu.addAction(self.clean_hosts_action)
        self.hosts_submenu.addAction(self.open_hosts_action)
        
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
        self.ui.menu.addMenu(self.work_mode_menu)  # 添加工作模式子菜单
        self.ui.menu.addMenu(self.download_settings_menu)  # 添加下载设置子菜单
        self.ui.menu.addSeparator()
        self.ui.menu.addMenu(self.dev_menu)  # 添加开发者选项子菜单
        
        # 添加Debug子菜单到开发者选项菜单
        self.dev_menu.addMenu(self.debug_submenu)
        self.dev_menu.addMenu(self.hosts_submenu) # 添加hosts文件选项子菜单
        self.dev_menu.addMenu(self.ipv6_submenu)  # 添加IPv6支持子菜单
        
    def _handle_ipv6_toggle(self, enabled):
        """处理IPv6支持切换事件
        
        Args:
            enabled: 是否启用IPv6支持
        """
        if not self.ipv6_manager:
            # 显示错误提示
            msg_box = self._create_message_box("错误", "\nIPv6管理器尚未初始化，请稍后再试。\n")
            msg_box.exec()
            # 恢复复选框状态
            self.ipv6_action.setChecked(not enabled)
            return
        
        if enabled:
            # 先显示警告提示
            warning_msg_box = self._create_message_box(
                "警告", 
                "\n目前IPv6支持功能仍在测试阶段，可能会发生意料之外的bug！\n\n您确定需要启用吗？\n",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            response = warning_msg_box.exec()
            
            # 如果用户选择不启用，直接返回
            if response != QMessageBox.StandardButton.Yes:
                # 恢复复选框状态
                self.ipv6_action.setChecked(False)
                return
                
            # 显示正在校验IPv6的提示
            msg_box = self._create_message_box("IPv6检测", "\n正在校验是否支持IPv6，请稍候...\n")
            msg_box.open()  # 使用open而不是exec，这样不会阻塞UI
            
            # 处理消息队列，确保对话框显示
            from PySide6.QtCore import QCoreApplication
            QCoreApplication.processEvents()
            
            # 检查IPv6是否可用
            ipv6_available = self.ipv6_manager.check_ipv6_availability()
            
            # 关闭提示对话框
            msg_box.accept()
            
            if not ipv6_available:
                # 显示IPv6不可用的提示
                error_msg_box = self._create_message_box(
                    "IPv6不可用", 
                    "\n未检测到可用的IPv6连接，无法启用IPv6支持。\n\n请确保您的网络环境支持IPv6且已正确配置。\n"
                )
                error_msg_box.exec()
                # 恢复复选框状态
                self.ipv6_action.setChecked(False)
                return False
        
        # 使用IPv6Manager处理切换
        success = self.ipv6_manager.toggle_ipv6_support(enabled)
        # 如果切换失败，恢复复选框状态
        if not success:
            self.ipv6_action.setChecked(not enabled)

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
        msg_box = self._create_message_box(
            "确认操作",
            "\n您确定要撤回隐私协议同意吗？\n\n撤回后软件将立即重启，您需要重新阅读并同意隐私协议。\n",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        
        reply = msg_box.exec()
        if reply == QMessageBox.StandardButton.Yes:
            # 用户确认撤回
            try:
                # 导入隐私管理器
                from core.managers.privacy_manager import PrivacyManager
                import sys
                import subprocess
                import os
                
                # 创建实例并重置隐私协议同意
                privacy_manager = PrivacyManager()
                if privacy_manager.reset_privacy_agreement():
                    # 显示重启提示
                    restart_msg = self._create_message_box(
                        "操作成功",
                        "\n已成功撤回隐私协议同意。\n\n软件将立即重启。\n"
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
                    fail_msg = self._create_message_box(
                        "操作失败",
                        "\n撤回隐私协议同意失败。\n\n请检查应用权限或稍后再试。\n"
                    )
                    fail_msg.exec()
            except Exception as e:
                # 显示错误提示
                error_msg = self._create_message_box(
                    "错误",
                    f"\n撤回隐私协议同意时发生错误：\n\n{str(e)}\n"
                )
                error_msg.exec()

    def _create_message_box(self, title, message, buttons=QMessageBox.StandardButton.Ok):
        """创建统一风格的消息框

        Args:
            title: 消息框标题
            message: 消息内容
            buttons: 按钮类型，默认为确定按钮

        Returns:
            QMessageBox: 配置好的消息框实例
        """
        msg_box = msgbox_frame(
            f"{title} - {APP_NAME}",
            message,
            buttons,
        )
        return msg_box
        
    def show_under_development(self):
        """显示功能正在开发中的提示"""
        msg_box = self._create_message_box("提示", "\n该功能正在开发中，敬请期待！\n")
        msg_box.exec()
        
    def show_download_thread_settings(self):
        """显示下载线程设置对话框"""
        if hasattr(self.main_window, 'download_manager'):
            self.main_window.download_manager.show_download_thread_settings()
        else:
            # 如果下载管理器不可用，显示错误信息
            msg_box = self._create_message_box("错误", "\n下载管理器未初始化，无法修改下载线程设置。\n")
            msg_box.exec()
        
    def open_log_file(self):
        """打开当前日志文件"""
        try:
            # 检查日志文件是否存在
            if os.path.exists(LOG_FILE):
                # 获取日志文件大小
                file_size = os.path.getsize(LOG_FILE)
                if file_size == 0:
                    msg_box = self._create_message_box("提示", f"\n当前日志文件 {os.path.basename(LOG_FILE)} 存在但为空。\n\n日志文件位置：{os.path.abspath(LOG_FILE)}")
                    msg_box.exec()
                    return
                
                # 根据文件大小决定是使用文本查看器还是直接打开
                if file_size > 1024 * 1024:  # 大于1MB
                    # 文件较大，显示警告
                    msg_box = self._create_message_box(
                        "警告",
                        f"\n日志文件较大 ({file_size / 1024 / 1024:.2f} MB)，是否仍要打开？\n\n日志文件位置：{os.path.abspath(LOG_FILE)}",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if msg_box.exec() != QMessageBox.StandardButton.Yes:
                        return
                
                # 使用操作系统默认程序打开日志文件
                if os.name == 'nt':  # Windows
                    os.startfile(LOG_FILE)
                else:  # macOS 和 Linux
                    import subprocess
                    subprocess.call(['xdg-open', LOG_FILE])
            else:
                # 文件不存在，显示信息
                # 搜索log文件夹下所有可能的日志文件
                root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                log_dir = os.path.join(root_dir, "log")
                
                # 如果log文件夹不存在，尝试创建它
                if not os.path.exists(log_dir):
                    try:
                        os.makedirs(log_dir, exist_ok=True)
                        msg_box = self._create_message_box(
                            "信息",
                            f"\n日志文件夹不存在，已创建新的日志文件夹：\n{log_dir}\n\n请在启用调试模式后重试。"
                        )
                        msg_box.exec()
                        return
                    except Exception as e:
                        msg_box = self._create_message_box(
                            "错误",
                            f"\n创建日志文件夹失败：\n\n{str(e)}"
                        )
                        msg_box.exec()
                        return
                
                # 搜索log文件夹中的日志文件
                try:
                    log_files = [f for f in os.listdir(log_dir) if f.startswith("log-") and f.endswith(".txt")]
                except Exception as e:
                    msg_box = self._create_message_box(
                        "错误",
                        f"\n无法读取日志文件夹：\n\n{str(e)}"
                    )
                    msg_box.exec()
                    return
                
                if log_files:
                    # 按照修改时间排序，获取最新的日志文件
                    log_files.sort(key=lambda x: os.path.getmtime(os.path.join(log_dir, x)), reverse=True)
                    latest_log = os.path.join(log_dir, log_files[0])
                    
                    # 获取最新日志文件的创建时间信息
                    try:
                        log_datetime = "-".join(os.path.basename(latest_log)[4:-4].split("-")[:2])
                        log_date = log_datetime.split("-")[0]
                        log_time = log_datetime.split("-")[1] if "-" in log_datetime else "未知时间"
                        date_info = f"日期: {log_date[:4]}-{log_date[4:6]}-{log_date[6:]}"
                        time_info = f"时间: {log_time[:2]}:{log_time[2:4]}:{log_time[4:]}"
                    except:
                        date_info = "日期未知 "
                        time_info = "时间未知"
                    
                    msg_box = self._create_message_box(
                        "信息",
                        f"\n当前日志文件 {os.path.basename(LOG_FILE)} 不存在。\n\n"
                        f"发现最新的日志文件: {os.path.basename(latest_log)}\n"
                        f"({date_info}{time_info})\n\n"
                        f"是否打开此文件？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if msg_box.exec() == QMessageBox.StandardButton.Yes:
                        if os.name == 'nt':  # Windows
                            os.startfile(latest_log)
                        else:  # macOS 和 Linux
                            import subprocess
                            subprocess.call(['xdg-open', latest_log])
                        return
                
                # 如果没有找到任何日志文件或用户选择不打开最新的日志文件
                msg_box = self._create_message_box(
                    "信息",
                    f"\n没有找到有效的日志文件。\n\n"
                    f"预期的日志文件夹：{log_dir}\n\n"
                    f"请确认调试模式已启用，并执行一些操作后再查看日志。"
                )
                msg_box.exec()
                
        except Exception as e:
            msg_box = self._create_message_box("错误", f"\n处理日志文件时出错：\n\n{str(e)}\n\n文件位置：{os.path.abspath(LOG_FILE)}")
            msg_box.exec()
            
    def restore_hosts_backup(self):
        """还原软件备份的hosts文件"""
        if hasattr(self.main_window, 'download_manager') and hasattr(self.main_window.download_manager, 'hosts_manager'):
            try:
                # 调用恢复hosts文件的方法
                result = self.main_window.download_manager.hosts_manager.restore()
                
                if result:
                    msg_box = self._create_message_box("成功", "\nhosts文件已成功还原为备份版本。\n")
                else:
                    msg_box = self._create_message_box("警告", "\n还原hosts文件失败或没有找到备份文件。\n")
                
                msg_box.exec()
            except Exception as e:
                msg_box = self._create_message_box("错误", f"\n还原hosts文件时发生错误：\n\n{str(e)}\n")
                msg_box.exec()
        else:
            msg_box = self._create_message_box("错误", "\n无法访问hosts管理器。\n")
            msg_box.exec()
            
    def clean_hosts_entries(self):
        """手动删除软件添加的hosts条目"""
        if hasattr(self.main_window, 'download_manager') and hasattr(self.main_window.download_manager, 'hosts_manager'):
            try:
                # 调用清理hosts条目的方法，强制清理即使禁用了自动还原
                result = self.main_window.download_manager.hosts_manager.check_and_clean_all_entries(force_clean=True)
                
                if result:
                    msg_box = self._create_message_box("成功", "\n已成功清理软件添加的hosts条目。\n")
                else:
                    msg_box = self._create_message_box("提示", "\n未发现软件添加的hosts条目或清理操作失败。\n")
                
                msg_box.exec()
            except Exception as e:
                msg_box = self._create_message_box("错误", f"\n清理hosts条目时发生错误：\n\n{str(e)}\n")
                msg_box.exec()
        else:
            msg_box = self._create_message_box("错误", "\n无法访问hosts管理器。\n")
            msg_box.exec()

    def open_hosts_file(self):
        """打开系统hosts文件"""
        try:
            # 获取hosts文件路径
            hosts_path = os.path.join(os.environ['SystemRoot'], 'System32', 'drivers', 'etc', 'hosts')
            
            # 检查文件是否存在
            if os.path.exists(hosts_path):
                # 使用操作系统默认程序打开hosts文件
                if os.name == 'nt':  # Windows
                    # 尝试以管理员权限打开记事本编辑hosts文件
                    try:
                        # 使用PowerShell以管理员身份启动记事本
                        subprocess.Popen(["powershell", "Start-Process", "notepad", hosts_path, "-Verb", "RunAs"])
                    except Exception as e:
                        # 如果失败，尝试直接打开
                        os.startfile(hosts_path)
                else:  # macOS 和 Linux
                    import subprocess
                    subprocess.call(['xdg-open', hosts_path])
            else:
                msg_box = self._create_message_box("错误", f"\nhosts文件不存在：\n{hosts_path}\n")
                msg_box.exec()
        except Exception as e:
            msg_box = self._create_message_box("错误", f"\n打开hosts文件时发生错误：\n\n{str(e)}\n")
            msg_box.exec()

    def toggle_disable_auto_restore_hosts(self, checked):
        """切换禁用自动还原hosts的状态
        
        Args:
            checked: 是否禁用自动还原
        """
        if hasattr(self.main_window, 'download_manager') and hasattr(self.main_window.download_manager, 'hosts_manager'):
            try:
                # 调用HostsManager的方法设置自动还原标志
                result = self.main_window.download_manager.hosts_manager.set_auto_restore_disabled(checked)
                
                if result:
                    # 同时更新内部配置，确保立即生效
                    if hasattr(self.main_window, 'config'):
                        self.main_window.config['disable_auto_restore_hosts'] = checked
                    
                    # 显示成功提示
                    status = "禁用" if checked else "启用"
                    msg_box = self._create_message_box(
                        "设置已更新", 
                        f"\n已{status}关闭/重启时自动还原hosts。\n\n{'hosts将被保留' if checked else 'hosts将在关闭时自动还原'}。\n"
                    )
                    msg_box.exec()
                else:
                    # 如果设置失败，恢复复选框状态
                    self.disable_auto_restore_action.setChecked(not checked)
                    msg_box = self._create_message_box(
                        "设置失败", 
                        "\n更新设置时发生错误，请稍后再试。\n"
                    )
                    msg_box.exec()
            except Exception as e:
                # 如果发生异常，恢复复选框状态
                self.disable_auto_restore_action.setChecked(not checked)
                msg_box = self._create_message_box(
                    "错误", 
                    f"\n更新设置时发生异常：\n\n{str(e)}\n"
                )
                msg_box.exec()
        else:
            # 如果hosts管理器不可用，恢复复选框状态
            self.disable_auto_restore_action.setChecked(not checked)
            msg_box = self._create_message_box(
                "错误", 
                "\nhosts管理器不可用，无法更新设置。\n"
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

    def show_ipv6_manager_not_ready(self):
        """显示IPv6管理器未准备好的提示"""
        msg_box = self._create_message_box("错误", "\nIPv6管理器尚未初始化，请稍后再试。\n")
        msg_box.exec() 

    def switch_work_mode(self, mode):
        """切换工作模式
        
        Args:
            mode: 要切换的模式，"online"或"offline"
        """
        # 检查主窗口是否有离线模式管理器
        if not hasattr(self.main_window, 'offline_mode_manager'):
            # 如果没有离线模式管理器，创建提示
            msg_box = self._create_message_box(
                "错误",
                "\n离线模式管理器未初始化，无法切换工作模式。\n"
            )
            msg_box.exec()
            
            # 恢复选择状态
            self.online_mode_action.setChecked(True)
            self.offline_mode_action.setChecked(False)
            return
            
        if mode == "offline":
            # 尝试切换到离线模式
            success = self.main_window.offline_mode_manager.set_offline_mode(True)
            if not success:
                # 如果切换失败，恢复选择状态
                self.online_mode_action.setChecked(True)
                self.offline_mode_action.setChecked(False)
                return
                
            # 更新配置
            self.main_window.config["offline_mode"] = True
            self.main_window.save_config(self.main_window.config)
            
            # 在离线模式下始终启用开始安装按钮
            if hasattr(self.main_window, 'set_start_button_enabled'):
                self.main_window.set_start_button_enabled(True)
            
            # 清除版本警告标志
            if hasattr(self.main_window, 'version_warning'):
                self.main_window.version_warning = False
            
            # 显示提示
            msg_box = self._create_message_box(
                "模式已切换",
                "\n已切换到离线模式。\n\n将使用本地补丁文件进行安装，不会从网络下载补丁。\n"
            )
            msg_box.exec()
        else:
            # 切换到在线模式
            self.main_window.offline_mode_manager.set_offline_mode(False)
            
            # 更新配置
            self.main_window.config["offline_mode"] = False
            self.main_window.save_config(self.main_window.config)
            
            # 重新获取云端配置
            if hasattr(self.main_window, 'fetch_cloud_config'):
                self.main_window.fetch_cloud_config()
                
            # 如果当前版本过低，设置版本警告标志
            if hasattr(self.main_window, 'last_error_message') and self.main_window.last_error_message == "update_required":
                # 设置版本警告标志
                if hasattr(self.main_window, 'version_warning'):
                    self.main_window.version_warning = True
            
            # 显示提示
            msg_box = self._create_message_box(
                "模式已切换",
                "\n已切换到在线模式。\n\n将从网络下载补丁进行安装。\n"
            )
            msg_box.exec() 

    def create_progress_window(self, title, initial_text="准备中..."):
        """创建并返回一个通用的进度窗口.
        
        Args:
            title (str): 窗口标题.
            initial_text (str): 初始状态文本.

        Returns:
            QDialog: 配置好的进度窗口实例.
        """
        progress_window = QDialog(self.main_window)
        progress_window.setWindowTitle(f"{title} - {APP_NAME}")
        progress_window.setFixedSize(400, 150)
        
        layout = QVBoxLayout()
        
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        layout.addWidget(progress_bar)
        
        status_label = QLabel(initial_text)
        layout.addWidget(status_label)
        
        progress_window.setLayout(layout)
        # 将控件附加到窗口对象上，以便外部访问
        progress_window.progress_bar = progress_bar
        progress_window.status_label = status_label
        
        return progress_window

    def show_loading_dialog(self, message):
        """显示或更新加载对话框."""
        if not self.loading_dialog:
            self.loading_dialog = QDialog(self.main_window)
            self.loading_dialog.setWindowTitle(f"请稍候 - {APP_NAME}")
            self.loading_dialog.setFixedSize(300, 100)
            self.loading_dialog.setModal(True)
            layout = QVBoxLayout()
            loading_label = QLabel(message)
            loading_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(loading_label)
            self.loading_dialog.setLayout(layout)
            # 将label附加到dialog，方便后续更新
            self.loading_dialog.loading_label = loading_label
        else:
            self.loading_dialog.loading_label.setText(message)
        
        self.loading_dialog.show()
        # force UI update
        QMessageBox.QApplication.processEvents()

    def hide_loading_dialog(self):
        """隐藏并销毁加载对话框."""
        if self.loading_dialog:
            self.loading_dialog.hide()
            self.loading_dialog = None 