import json
import webbrowser
from PySide6.QtWidgets import QMessageBox

from utils import load_config, save_config, msgbox_frame

class ConfigManager:
    """配置管理器，用于处理配置的加载、保存和获取云端配置"""
    
    def __init__(self, app_name, config_url, ua, debug_manager=None):
        """初始化配置管理器
        
        Args:
            app_name: 应用程序名称，用于显示消息框标题
            config_url: 云端配置URL
            ua: User-Agent字符串
            debug_manager: 调试管理器实例，用于输出调试信息
        """
        self.app_name = app_name
        self.config_url = config_url
        self.ua = ua
        self.debug_manager = debug_manager
        self.cloud_config = None
        self.config_valid = False
        self.last_error_message = ""
        
    def _is_debug_mode(self):
        """检查是否处于调试模式
        
        Returns:
            bool: 是否处于调试模式
        """
        if hasattr(self.debug_manager, 'ui_manager') and hasattr(self.debug_manager.ui_manager, 'debug_action'):
            return self.debug_manager.ui_manager.debug_action.isChecked()
        return False
    
    def load_config(self):
        """加载本地配置
        
        Returns:
            dict: 加载的配置
        """
        return load_config()
    
    def save_config(self, config):
        """保存配置
        
        Args:
            config: 要保存的配置
        """
        save_config(config)
    
    def fetch_cloud_config(self, config_fetch_thread_class, callback=None):
        """获取云端配置
        
        Args:
            config_fetch_thread_class: 用于获取云端配置的线程类
            callback: 获取完成后的回调函数，接受两个参数(data, error_message)
        """
        headers = {"User-Agent": self.ua}
        debug_mode = self._is_debug_mode()
        self.config_fetch_thread = config_fetch_thread_class(self.config_url, headers, debug_mode)
        
        # 如果提供了回调，使用它；否则使用内部的on_config_fetched方法
        if callback:
            self.config_fetch_thread.finished.connect(callback)
        else:
            self.config_fetch_thread.finished.connect(self.on_config_fetched)
            
        self.config_fetch_thread.start()
    
    def on_config_fetched(self, data, error_message):
        """云端配置获取完成的回调处理
        
        Args:
            data: 获取到的配置数据
            error_message: 错误信息，如果有
        """
        debug_mode = self._is_debug_mode()
        
        if error_message:
            # 标记配置无效
            self.config_valid = False
            
            # 记录错误信息，用于按钮点击时显示
            if error_message == "update_required":
                self.last_error_message = "update_required"
                
                # 检查是否处于离线模式
                is_offline_mode = False
                if hasattr(self.debug_manager, 'main_window') and hasattr(self.debug_manager.main_window, 'offline_mode_manager'):
                    is_offline_mode = self.debug_manager.main_window.offline_mode_manager.is_in_offline_mode()
                
                if is_offline_mode:
                    # 离线模式下只显示提示，不禁用开始安装按钮
                    msg_box = msgbox_frame(
                        f"更新提示 - {self.app_name}",
                        "\n当前版本过低，请及时更新。\n在离线模式下，您仍可使用禁用/启用补丁、卸载补丁和离线安装功能。\n",
                        QMessageBox.StandardButton.Ok,
                    )
                    msg_box.exec()
                    # 移除在浏览器中打开项目主页的代码
                    # 离线模式下版本过低，仍然允许使用安装按钮
                    return {"action": "enable_button"}
                else:
                    # 在线模式下显示强制更新提示
                    msg_box = msgbox_frame(
                        f"更新提示 - {self.app_name}",
                        "\n当前版本过低，请及时更新。\n如需联网下载补丁，请更新到最新版，否则无法下载。\n",
                        QMessageBox.StandardButton.Ok,
                    )
                    msg_box.exec()
                    # 移除在浏览器中打开项目主页的代码
                    # 在线模式下版本过低，但不直接禁用按钮，而是在点击时提示
                    return {"action": "enable_button", "version_warning": True}
                
            elif "missing_keys" in error_message:
                self.last_error_message = "missing_keys"
                missing_versions = error_message.split(":")[1]
                msg_box = msgbox_frame(
                    f"配置缺失 - {self.app_name}",
                    f'\n云端缺失下载链接，可能云服务器正在维护，不影响其他版本下载。\n当前缺失版本:"{missing_versions}"\n',
                    QMessageBox.StandardButton.Ok,
                )
                msg_box.exec()
                # 对于部分缺失，仍然允许使用，因为可能只影响部分游戏版本
                self.config_valid = True
                return {"action": "enable_button"}
            else:
                # 设置网络错误标记
                self.last_error_message = "network_error"
                
                # 显示通用错误消息，只在debug模式下显示详细错误
                error_msg = "访问云端配置失败，请检查网络状况或稍后再试。"
                if debug_mode and "详细错误:" in error_message:
                    msg_box = msgbox_frame(
                        f"错误 - {self.app_name}",
                        f"\n{error_message}\n",
                        QMessageBox.StandardButton.Ok,
                    )
                else:
                    msg_box = msgbox_frame(
                        f"错误 - {self.app_name}",
                        f"\n{error_msg}\n",
                        QMessageBox.StandardButton.Ok,
                    )
                msg_box.exec()
                
                # 网络错误时仍然允许使用按钮，用户可以尝试离线模式
                return {"action": "enable_button"}
        else:
            self.cloud_config = data
            # 标记配置有效
            self.config_valid = True
            # 清除错误信息
            self.last_error_message = ""
            
            if debug_mode:
                print("--- Cloud config fetched successfully ---")
                # 创建一个数据副本，隐藏敏感URL
                safe_data = self._create_safe_config_for_logging(data)
                print(json.dumps(safe_data, indent=2))
                
            # 获取配置成功，允许安装
            return {"action": "enable_button"}
            
    def _create_safe_config_for_logging(self, config_data):
        """创建用于日志记录的安全配置副本，隐藏敏感URL
        
        Args:
            config_data: 原始配置数据
            
        Returns:
            dict: 安全的配置数据副本
        """
        if not config_data or not isinstance(config_data, dict):
            return config_data
            
        # 创建深拷贝，避免修改原始数据
        import copy
        safe_config = copy.deepcopy(config_data)
        
        # 隐藏敏感URL
        for key in safe_config:
            if isinstance(safe_config[key], dict) and "url" in safe_config[key]:
                # 完全隐藏URL
                safe_config[key]["url"] = "***URL protection***"
        
        return safe_config
    
    def is_config_valid(self):
        """检查配置是否有效
        
        Returns:
            bool: 配置是否有效
        """
        return self.config_valid
    
    def get_cloud_config(self):
        """获取云端配置
        
        Returns:
            dict: 云端配置
        """
        return self.cloud_config
    
    def get_last_error(self):
        """获取最后一次错误信息
        
        Returns:
            str: 错误信息
        """
        return self.last_error_message
        
    def toggle_disable_pre_hash_check(self, main_window, checked):
        """切换禁用安装前哈希预检查的状态
        
        Args:
            main_window: 主窗口实例
            checked: 是否禁用安装前哈希预检查
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 更新配置
            if hasattr(main_window, 'config'):
                main_window.config['disable_pre_hash_check'] = checked
                
                # 保存配置到文件
                if hasattr(main_window, 'save_config'):
                    main_window.save_config(main_window.config)
                
                # 显示成功提示
                status = "禁用" if checked else "启用"
                from utils import msgbox_frame
                msg_box = msgbox_frame(
                    f"设置已更新 - {self.app_name}",
                    f"\n已{status}安装前哈希预检查。\n\n{'安装时将跳过哈希预检查' if checked else '安装时将进行哈希预检查'}。\n",
                    QMessageBox.StandardButton.Ok,
                )
                msg_box.exec()
                return True
            else:
                # 如果配置不可用，显示错误
                from utils import msgbox_frame
                msg_box = msgbox_frame(
                    f"错误 - {self.app_name}",
                    "\n配置管理器不可用，无法更新设置。\n",
                    QMessageBox.StandardButton.Ok,
                )
                msg_box.exec()
                return False
        except Exception as e:
            # 如果发生异常，显示错误
            from utils import msgbox_frame
            msg_box = msgbox_frame(
                f"错误 - {self.app_name}",
                f"\n更新设置时发生异常：\n\n{str(e)}\n",
                QMessageBox.StandardButton.Ok,
            )
            msg_box.exec()
            return False 