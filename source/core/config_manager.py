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
                msg_box = msgbox_frame(
                    f"更新提示 - {self.app_name}",
                    "\n当前版本过低，请及时更新。\n",
                    QMessageBox.StandardButton.Ok,
                )
                msg_box.exec()
                # 在浏览器中打开项目主页
                webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT/")
                # 版本过低，应当显示"无法安装"
                return {"action": "disable_button", "then": "exit"}
                
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
                
                # 网络错误时应当显示"无法安装"
                return {"action": "disable_button"}
        else:
            self.cloud_config = data
            # 标记配置有效
            self.config_valid = True
            # 清除错误信息
            self.last_error_message = ""
            
            if debug_mode:
                print("--- Cloud config fetched successfully ---")
                print(json.dumps(data, indent=2))
                
            # 获取配置成功，允许安装
            return {"action": "enable_button"}
    
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