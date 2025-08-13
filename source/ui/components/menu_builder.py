"""
菜单构建器
负责构建和管理应用程序的各种菜单
"""

from PySide6.QtGui import QAction, QActionGroup, QCursor
from PySide6.QtWidgets import QMenu, QPushButton
from PySide6.QtCore import Qt, QRect

from config.config import APP_NAME, APP_VERSION


class MenuBuilder:
    """菜单构建器类"""
    
    def __init__(self, main_window, font_style_manager, external_links_handler, dialog_factory):
        """初始化菜单构建器
        
        Args:
            main_window: 主窗口实例
            font_style_manager: 字体样式管理器
            external_links_handler: 外部链接处理器
            dialog_factory: 对话框工厂
        """
        self.main_window = main_window
        self.ui = getattr(main_window, 'ui', None)
        self.font_style_manager = font_style_manager
        self.external_links_handler = external_links_handler
        self.dialog_factory = dialog_factory
        
        # 菜单引用
        self.dev_menu = None
        self.privacy_menu = None
        self.about_menu = None
        self.about_btn = None
        
        # 工作模式相关
        self.work_mode_menu = None
        self.online_mode_action = None
        self.offline_mode_action = None
        
        # 开发者选项相关
        self.debug_submenu = None
        self.hosts_submenu = None
        self.ipv6_submenu = None
        self.hash_settings_menu = None
        self.download_settings_menu = None
        
        # 各种action引用
        self.debug_action = None
        self.open_log_action = None
        self.ipv6_action = None
        self.ipv6_test_action = None
        self.disable_auto_restore_action = None
        self.disable_pre_hash_action = None
    
    def setup_all_menus(self):
        """设置所有菜单"""
        self.create_about_button()
        self.setup_help_menu()
        self.setup_about_menu()
        self.setup_settings_menu()
    
    def create_about_button(self):
        """创建"关于"按钮"""
        if not self.ui or not hasattr(self.ui, 'menu_area'):
            return
            
        # 获取菜单字体和样式
        menu_font = self.font_style_manager.get_menu_font()
        
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
    
    def setup_help_menu(self):
        """设置"帮助"菜单"""
        if not self.ui or not hasattr(self.ui, 'menu_2'):
            return

        # 获取菜单字体
        menu_font = self.font_style_manager.get_menu_font()

        # 创建菜单项
        faq_action = QAction("常见问题", self.main_window)
        faq_action.triggered.connect(self.external_links_handler.open_faq_page)
        faq_action.setFont(menu_font)
        
        report_issue_action = QAction("提交错误", self.main_window)
        report_issue_action.triggered.connect(self.external_links_handler.open_issues_page)
        report_issue_action.setFont(menu_font)
        
        # 清除现有菜单项并添加新的菜单项
        self.ui.menu_2.clear()
        self.ui.menu_2.addAction(faq_action)
        self.ui.menu_2.addAction(report_issue_action)

    def setup_about_menu(self):
        """设置"关于"菜单"""
        # 获取菜单字体
        menu_font = self.font_style_manager.get_menu_font()
        
        # 创建关于菜单
        self.about_menu = QMenu("关于", self.main_window)
        self.about_menu.setFont(menu_font)
        
        # 设置菜单样式
        menu_style = self.font_style_manager.get_menu_style()
        self.about_menu.setStyleSheet(menu_style)
        
        # 创建菜单项
        about_project_action = QAction("关于本项目", self.main_window)
        about_project_action.setFont(menu_font)
        about_project_action.triggered.connect(self.external_links_handler.show_about_dialog)
        
        project_home_action = QAction("Github项目主页", self.main_window)
        project_home_action.setFont(menu_font)
        project_home_action.triggered.connect(self.external_links_handler.open_project_home_page)
        
        qq_group_action = QAction("加入QQ群", self.main_window)
        qq_group_action.setFont(menu_font)
        qq_group_action.triggered.connect(self.external_links_handler.open_qq_group)
        
        # 创建隐私协议菜单
        self.setup_privacy_menu()
        
        # 添加到关于菜单
        self.about_menu.addAction(about_project_action)
        self.about_menu.addAction(project_home_action)
        self.about_menu.addAction(qq_group_action)
        self.about_menu.addSeparator()
        self.about_menu.addMenu(self.privacy_menu)
        
        # 连接按钮点击事件
        if self.about_btn:
            self.about_btn.clicked.connect(lambda: self.show_menu(self.about_menu, self.about_btn))
    
    def setup_privacy_menu(self):
        """设置"隐私协议"菜单"""
        menu_font = self.font_style_manager.get_menu_font()
        
        # 创建隐私协议子菜单
        self.privacy_menu = QMenu("隐私协议", self.main_window)
        self.privacy_menu.setFont(menu_font)
        
        # 设置样式
        menu_style = self.font_style_manager.get_menu_style()
        self.privacy_menu.setStyleSheet(menu_style)
        
        # 添加子选项
        view_privacy_action = QAction("查看完整隐私协议", self.main_window)
        view_privacy_action.setFont(menu_font)
        view_privacy_action.triggered.connect(self.external_links_handler.open_privacy_policy)
        
        revoke_privacy_action = QAction("撤回隐私协议", self.main_window)
        revoke_privacy_action.setFont(menu_font)
        revoke_privacy_action.triggered.connect(self.external_links_handler.revoke_privacy_agreement)
        
        # 添加到子菜单
        self.privacy_menu.addAction(view_privacy_action)
        self.privacy_menu.addAction(revoke_privacy_action)

    def setup_settings_menu(self):
        """设置"设置"菜单"""
        if not self.ui or not hasattr(self.ui, 'menu'):
            return

        # 获取菜单字体
        menu_font = self.font_style_manager.get_menu_font()
        menu_style = self.font_style_manager.get_menu_style()

        # 创建各个子菜单
        self._create_work_mode_menu(menu_font, menu_style)
        self._create_download_settings_menu(menu_font, menu_style)
        self._create_developer_options_menu(menu_font, menu_style)
        
        # 添加到主菜单
        self.ui.menu.addMenu(self.work_mode_menu)
        self.ui.menu.addMenu(self.download_settings_menu)
        self.ui.menu.addSeparator()
        self.ui.menu.addMenu(self.dev_menu)
    
    def _create_work_mode_menu(self, menu_font, menu_style):
        """创建工作模式子菜单"""
        self.work_mode_menu = QMenu("工作模式", self.main_window)
        self.work_mode_menu.setFont(menu_font)
        self.work_mode_menu.setStyleSheet(menu_style)
        
        # 获取当前离线模式状态
        is_offline_mode = False
        if hasattr(self.main_window, 'offline_mode_manager'):
            is_offline_mode = self.main_window.offline_mode_manager.is_in_offline_mode()
        
        # 创建在线模式和离线模式选项
        self.online_mode_action = QAction("在线模式", self.main_window, checkable=True)
        self.online_mode_action.setFont(menu_font)
        self.online_mode_action.setChecked(not is_offline_mode)
        
        self.offline_mode_action = QAction("离线模式", self.main_window, checkable=True)
        self.offline_mode_action.setFont(menu_font)
        self.offline_mode_action.setChecked(is_offline_mode)
        
        # 将两个模式选项添加到同一个互斥组
        mode_group = QActionGroup(self.main_window)
        mode_group.addAction(self.online_mode_action)
        mode_group.addAction(self.offline_mode_action)
        mode_group.setExclusive(True)
        
        # 连接切换事件（这里需要在ui_manager中处理）
        self.online_mode_action.triggered.connect(lambda: self._handle_mode_switch("online"))
        self.offline_mode_action.triggered.connect(lambda: self._handle_mode_switch("offline"))
        
        # 添加到工作模式子菜单
        self.work_mode_menu.addAction(self.online_mode_action)
        self.work_mode_menu.addAction(self.offline_mode_action)

    def _create_download_settings_menu(self, menu_font, menu_style):
        """创建下载设置子菜单"""
        self.download_settings_menu = QMenu("下载设置", self.main_window)
        self.download_settings_menu.setFont(menu_font)
        self.download_settings_menu.setStyleSheet(menu_style)
        
        # "修改下载源"按钮
        switch_source_action = QAction("修改下载源", self.main_window)
        switch_source_action.setFont(menu_font)
        switch_source_action.setEnabled(True)
        switch_source_action.triggered.connect(
            lambda: self.dialog_factory.show_simple_message("提示", "\n该功能正在开发中，敬请期待！\n")
        )
        
        # 添加下载线程设置选项
        thread_settings_action = QAction("下载线程设置", self.main_window)
        thread_settings_action.setFont(menu_font)
        thread_settings_action.triggered.connect(self._handle_download_thread_settings)
        
        # 添加到下载设置子菜单
        self.download_settings_menu.addAction(switch_source_action)
        self.download_settings_menu.addAction(thread_settings_action)

    def _create_developer_options_menu(self, menu_font, menu_style):
        """创建开发者选项子菜单"""
        self.dev_menu = QMenu("开发者选项", self.main_window)
        self.dev_menu.setFont(menu_font)
        self.dev_menu.setStyleSheet(menu_style)
        
        # 创建各个子菜单
        self._create_debug_submenu(menu_font, menu_style)
        self._create_hosts_submenu(menu_font, menu_style)
        self._create_ipv6_submenu(menu_font, menu_style)
        self._create_hash_settings_submenu(menu_font, menu_style)
        
        # 添加到开发者选项菜单
        self.dev_menu.addMenu(self.debug_submenu)
        self.dev_menu.addMenu(self.hosts_submenu)
        self.dev_menu.addMenu(self.ipv6_submenu)
        self.dev_menu.addMenu(self.hash_settings_menu)

    def _create_debug_submenu(self, menu_font, menu_style):
        """创建Debug子菜单"""
        self.debug_submenu = QMenu("Debug模式", self.main_window)
        self.debug_submenu.setFont(menu_font)
        self.debug_submenu.setStyleSheet(menu_style)
        
        # 创建Debug开关选项
        self.debug_action = QAction("Debug开关", self.main_window, checkable=True)
        self.debug_action.setFont(menu_font)
        
        # 获取debug模式状态
        config = getattr(self.main_window, 'config', {})
        debug_mode = False
        if isinstance(config, dict):
            debug_mode = config.get("debug_mode", False)
        
        self.debug_action.setChecked(debug_mode)
        
        # 连接toggle_debug_mode方法
        if hasattr(self.main_window, 'toggle_debug_mode'):
            self.debug_action.triggered.connect(self.main_window.toggle_debug_mode)
        
        # 创建打开log文件选项
        self.open_log_action = QAction("打开log.txt", self.main_window)
        self.open_log_action.setFont(menu_font)
        self.open_log_action.setEnabled(debug_mode)
        
        # 连接打开log文件的事件
        if hasattr(self.main_window, 'debug_manager'):
            self.open_log_action.triggered.connect(self.main_window.debug_manager.open_log_file)
        else:
            self.open_log_action.triggered.connect(
                lambda: self.dialog_factory.show_simple_message("错误", "\n调试管理器未初始化。\n", "error")
            )
        
        # 添加到Debug子菜单
        self.debug_submenu.addAction(self.debug_action)
        self.debug_submenu.addAction(self.open_log_action)

    def _create_hosts_submenu(self, menu_font, menu_style):
        """创建hosts文件选项子菜单"""
        self.hosts_submenu = QMenu("hosts文件选项", self.main_window)
        self.hosts_submenu.setFont(menu_font)
        self.hosts_submenu.setStyleSheet(menu_style)
        
        # 添加hosts子选项
        restore_hosts_action = QAction("还原软件备份的hosts文件", self.main_window)
        restore_hosts_action.setFont(menu_font)
        restore_hosts_action.triggered.connect(self._handle_restore_hosts_backup)
        
        clean_hosts_action = QAction("手动删除软件添加的hosts条目", self.main_window)
        clean_hosts_action.setFont(menu_font)
        clean_hosts_action.triggered.connect(self._handle_clean_hosts_entries)
        
        # 添加禁用自动还原hosts的选项
        self.disable_auto_restore_action = QAction("禁用关闭/重启自动还原hosts", self.main_window, checkable=True)
        self.disable_auto_restore_action.setFont(menu_font)
        
        # 从配置中读取当前状态
        config = getattr(self.main_window, 'config', {})
        disable_auto_restore = False
        if isinstance(config, dict):
            disable_auto_restore = config.get("disable_auto_restore_hosts", False)
        
        self.disable_auto_restore_action.setChecked(disable_auto_restore)
        self.disable_auto_restore_action.triggered.connect(self._handle_toggle_disable_auto_restore_hosts)
        
        # 添加打开hosts文件选项
        open_hosts_action = QAction("打开hosts文件", self.main_window)
        open_hosts_action.setFont(menu_font)
        open_hosts_action.triggered.connect(self._handle_open_hosts_file)
        
        # 添加到hosts子菜单
        self.hosts_submenu.addAction(self.disable_auto_restore_action)
        self.hosts_submenu.addAction(restore_hosts_action)
        self.hosts_submenu.addAction(clean_hosts_action)
        self.hosts_submenu.addAction(open_hosts_action)

    def _create_ipv6_submenu(self, menu_font, menu_style):
        """创建IPv6支持子菜单"""
        self.ipv6_submenu = QMenu("IPv6支持", self.main_window)
        self.ipv6_submenu.setFont(menu_font)
        self.ipv6_submenu.setStyleSheet(menu_style)
        
        # 添加IPv6支持选项
        self.ipv6_action = QAction("启用IPv6支持", self.main_window, checkable=True)
        self.ipv6_action.setFont(menu_font)
        
        # 添加IPv6检测按钮
        self.ipv6_test_action = QAction("测试IPv6连接", self.main_window)
        self.ipv6_test_action.setFont(menu_font)
        
        # 获取IPv6Manager实例
        ipv6_manager = getattr(self.main_window, 'ipv6_manager', None)
        if ipv6_manager:
            self.ipv6_test_action.triggered.connect(ipv6_manager.show_ipv6_details)
        else:
            self.ipv6_test_action.triggered.connect(
                lambda: self.dialog_factory.show_simple_message("错误", "\nIPv6管理器尚未初始化，请稍后再试。\n", "error")
            )
        
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

    def _create_hash_settings_submenu(self, menu_font, menu_style):
        """创建哈希校验设置子菜单"""
        self.hash_settings_menu = QMenu("哈希校验设置", self.main_window)
        self.hash_settings_menu.setFont(menu_font)
        self.hash_settings_menu.setStyleSheet(menu_style)
        
        # 添加禁用安装前哈希预检查选项
        self.disable_pre_hash_action = QAction("禁用安装前哈希预检查", self.main_window, checkable=True)
        self.disable_pre_hash_action.setFont(menu_font)
        
        # 从配置中读取当前状态
        config = getattr(self.main_window, 'config', {})
        disable_pre_hash = False
        if isinstance(config, dict):
            disable_pre_hash = config.get("disable_pre_hash_check", False)
        
        self.disable_pre_hash_action.setChecked(disable_pre_hash)
        self.disable_pre_hash_action.triggered.connect(lambda checked: self._handle_pre_hash_toggle(checked))
        
        # 添加到哈希校验设置子菜单
        self.hash_settings_menu.addAction(self.disable_pre_hash_action)

    def show_menu(self, menu, button):
        """显示菜单
        
        Args:
            menu: 要显示的菜单
            button: 触发菜单的按钮
        """
        # 检查Ui_install中是否定义了show_menu方法
        if hasattr(self.ui, 'show_menu'):
            self.ui.show_menu(menu, button)
        else:
            # 否则，使用默认的弹出方法
            global_pos = button.mapToGlobal(button.rect().bottomLeft())
            menu.popup(global_pos)

    # 以下方法需要委托给ui_manager处理
    def _handle_mode_switch(self, mode):
        """处理工作模式切换"""
        # 这个方法需要在ui_manager中实现
        if hasattr(self.main_window, 'ui_manager') and hasattr(self.main_window.ui_manager, 'switch_work_mode'):
            self.main_window.ui_manager.switch_work_mode(mode)
        else:
            self.dialog_factory.show_simple_message("错误", "\n工作模式切换功能不可用。\n", "error")

    def _handle_download_thread_settings(self):
        """处理下载线程设置"""
        if hasattr(self.main_window, 'download_manager'):
            self.main_window.download_manager.show_download_thread_settings()
        else:
            self.dialog_factory.show_simple_message("错误", "\n下载管理器未初始化，无法修改下载线程设置。\n", "error")

    def _handle_ipv6_toggle(self, enabled):
        """处理IPv6支持切换"""
        if hasattr(self.main_window, 'ui_manager') and hasattr(self.main_window.ui_manager, '_handle_ipv6_toggle'):
            self.main_window.ui_manager._handle_ipv6_toggle(enabled)
        else:
            self.dialog_factory.show_simple_message("错误", "\nIPv6管理功能不可用。\n", "error")

    def _handle_pre_hash_toggle(self, checked):
        """处理禁用安装前哈希预检查的切换"""
        if hasattr(self.main_window, 'ui_manager') and hasattr(self.main_window.ui_manager, '_handle_pre_hash_toggle'):
            self.main_window.ui_manager._handle_pre_hash_toggle(checked)
        else:
            self.dialog_factory.show_simple_message("错误", "\n哈希检查设置功能不可用。\n", "error")

    def _handle_restore_hosts_backup(self):
        """处理还原hosts备份"""
        if hasattr(self.main_window, 'ui_manager') and hasattr(self.main_window.ui_manager, 'restore_hosts_backup'):
            self.main_window.ui_manager.restore_hosts_backup()
        else:
            self.dialog_factory.show_simple_message("错误", "\nhosts管理功能不可用。\n", "error")

    def _handle_clean_hosts_entries(self):
        """处理清理hosts条目"""
        if hasattr(self.main_window, 'ui_manager') and hasattr(self.main_window.ui_manager, 'clean_hosts_entries'):
            self.main_window.ui_manager.clean_hosts_entries()
        else:
            self.dialog_factory.show_simple_message("错误", "\nhosts管理功能不可用。\n", "error")

    def _handle_toggle_disable_auto_restore_hosts(self, checked):
        """处理切换禁用自动还原hosts"""
        if hasattr(self.main_window, 'ui_manager') and hasattr(self.main_window.ui_manager, 'toggle_disable_auto_restore_hosts'):
            self.main_window.ui_manager.toggle_disable_auto_restore_hosts(checked)
        else:
            self.dialog_factory.show_simple_message("错误", "\nhosts管理功能不可用。\n", "error")

    def _handle_open_hosts_file(self):
        """处理打开hosts文件"""
        if hasattr(self.main_window, 'ui_manager') and hasattr(self.main_window.ui_manager, 'open_hosts_file'):
            self.main_window.ui_manager.open_hosts_file()
        else:
            self.dialog_factory.show_simple_message("错误", "\nhosts管理功能不可用。\n", "error")