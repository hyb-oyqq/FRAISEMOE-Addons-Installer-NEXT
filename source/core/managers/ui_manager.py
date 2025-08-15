from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMessageBox
import os
import logging
import subprocess

from utils import load_base64_image, resource_path
from config.config import APP_NAME, APP_VERSION
from ui.components import FontStyleManager, DialogFactory, ExternalLinksHandler, MenuBuilder

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
        
        # 获取主窗口的IPv6Manager实例
        self.ipv6_manager = getattr(main_window, 'ipv6_manager', None)
        
        # 初始化UI组件
        self.font_style_manager = FontStyleManager()
        self.dialog_factory = DialogFactory(main_window)
        self.external_links_handler = ExternalLinksHandler(main_window, self.dialog_factory)
        self.menu_builder = MenuBuilder(main_window, self.font_style_manager, self.external_links_handler, self.dialog_factory)
        
        # 保留一些快捷访问属性以保持兼容性
        self.debug_action = None
        self.disable_auto_restore_action = None
        self.disable_pre_hash_action = None
        
    def setup_ui(self):
        """设置UI元素，包括窗口图标、标题和菜单"""
        # 设置窗口图标
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
        
        # 使用新的菜单构建器设置所有菜单
        self.menu_builder.setup_all_menus()
        
        # 保持对一些重要UI元素的引用以确保兼容性
        self.debug_action = self.menu_builder.debug_action
        self.disable_auto_restore_action = self.menu_builder.disable_auto_restore_action  
        self.disable_pre_hash_action = self.menu_builder.disable_pre_hash_action
        
        # 保存对工作模式菜单项的引用，确保能正确同步状态
        self.online_mode_action = self.menu_builder.online_mode_action
        self.offline_mode_action = self.menu_builder.offline_mode_action
        
        # 在菜单创建完成后，强制同步一次工作模式状态
        self.sync_work_mode_menu_state()
    
    # 为了向后兼容性，添加委托方法
    def create_progress_window(self, title, initial_text="准备中..."):
        """创建进度窗口（委托给dialog_factory）"""
        return self.dialog_factory.create_progress_window(title, initial_text)
    
    def show_loading_dialog(self, message):
        """显示加载对话框（委托给dialog_factory）"""
        return self.dialog_factory.show_loading_dialog(message)
    
    def hide_loading_dialog(self):
        """隐藏加载对话框（委托给dialog_factory）"""
        return self.dialog_factory.hide_loading_dialog()
    
    def _create_message_box(self, title, message, buttons=QMessageBox.StandardButton.Ok):
        """创建消息框（委托给dialog_factory）"""
        return self.dialog_factory.create_message_box(title, message, buttons)
    
    def show_menu(self, menu, button):
        """显示菜单（委托给menu_builder）"""
        return self.menu_builder.show_menu(menu, button)
    
    def sync_work_mode_menu_state(self):
        """同步工作模式菜单状态，确保菜单选择状态与实际工作模式一致"""
        try:
            # 检查是否有离线模式管理器和菜单项
            if not hasattr(self.main_window, 'offline_mode_manager') or not self.main_window.offline_mode_manager:
                return
                
            if not hasattr(self, 'online_mode_action') or not hasattr(self, 'offline_mode_action'):
                return
                
            if not self.online_mode_action or not self.offline_mode_action:
                return
                
            # 获取当前离线模式状态
            is_offline_mode = self.main_window.offline_mode_manager.is_in_offline_mode()
            
            # 同步菜单选择状态
            self.online_mode_action.setChecked(not is_offline_mode)
            self.offline_mode_action.setChecked(is_offline_mode)
            
            # 记录同步操作（仅在调试模式下）
            if hasattr(self.main_window, 'config') and self.main_window.config.get('debug_mode', False):
                from utils.logger import setup_logger
                logger = setup_logger("ui_manager")
                logger.debug(f"已同步工作模式菜单状态: 离线模式={is_offline_mode}")
                
        except Exception as e:
            # 静默处理异常，避免影响程序正常运行
            if hasattr(self.main_window, 'config') and self.main_window.config.get('debug_mode', False):
                from utils.logger import setup_logger
                logger = setup_logger("ui_manager")
                logger.debug(f"同步工作模式菜单状态时出错: {e}")
    






        
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





        
    def show_download_thread_settings(self):
        """显示下载线程设置对话框"""
        if hasattr(self.main_window, 'download_manager'):
            self.main_window.download_manager.show_download_thread_settings()
        else:
            # 如果下载管理器不可用，显示错误信息
            self.dialog_factory.show_simple_message("错误", "\n下载管理器未初始化，无法修改下载线程设置。\n", "error")
        

            
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

    def _handle_pre_hash_toggle(self, checked):
        """处理禁用安装前哈希预检查的切换
        
        Args:
            checked: 是否禁用安装前哈希预检查
        """
        if hasattr(self.main_window, 'config_manager'):
            success = self.main_window.config_manager.toggle_disable_pre_hash_check(self.main_window, checked)
            if not success:
                # 如果操作失败，恢复复选框状态
                self.disable_pre_hash_action.setChecked(not checked)
        else:
            # 如果配置管理器不可用，恢复复选框状态并显示错误
            self.disable_pre_hash_action.setChecked(not checked)
            self._create_message_box("错误", "\n配置管理器未初始化。\n").exec()

 

 

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
            
            # 在离线模式下启用开始安装按钮
            if hasattr(self.main_window, 'window_manager'):
                self.main_window.window_manager.change_window_state(self.main_window.window_manager.STATE_READY)
            
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


 