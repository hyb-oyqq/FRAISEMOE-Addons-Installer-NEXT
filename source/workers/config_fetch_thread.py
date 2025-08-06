import json
import requests
import webbrowser
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QMessageBox
import sys
from utils.logger import setup_logger
from utils.url_censor import censor_url

# 初始化logger
logger = setup_logger("config_fetch")

class ConfigFetchThread(QThread):
    finished = Signal(object, str)  # data, error_message

    def __init__(self, url, headers, debug_mode=False, parent=None):
        super().__init__(parent)
        self.url = url
        self.headers = headers
        self.debug_mode = debug_mode

    def run(self):
        try:
            if self.debug_mode:
                logger.info("--- Starting to fetch cloud config ---")
                # 完全隐藏URL
                logger.debug(f"DEBUG: Requesting URL: ***URL protection***")
                logger.debug(f"DEBUG: Using Headers: {self.headers}")

            response = requests.get(self.url, headers=self.headers, timeout=10)

            if self.debug_mode:
                logger.debug(f"DEBUG: Response Status Code: {response.status_code}")
                logger.debug(f"DEBUG: Response Headers: {response.headers}")
                
                # 记录实际响应内容，但隐藏URL等敏感信息（临时禁用）
                # censored_text = censor_url(response.text)
                censored_text = response.text  # 直接使用原始文本
                logger.debug(f"DEBUG: Response Text: {censored_text}")

            response.raise_for_status()
            
            # 首先，总是尝试解析JSON
            config_data = response.json()

            # 检查是否是要求更新的错误信息 - 使用Unicode编码的更新提示文本
            update_required_msg = "\u8bf7\u4f7f\u7528\u6700\u65b0\u7248\u672c\u7684FraiseMoe2-Next\u8fdb\u884c\u4e0b\u8f7d"
            if isinstance(config_data, str) and config_data == update_required_msg:
                self.finished.emit(None, "update_required")
                return
            elif isinstance(config_data, dict) and config_data.get("message") == update_required_msg:
                self.finished.emit(None, "update_required")
                return

            # 检查是否是有效的配置文件
            required_keys = [f"vol.{i+1}.data" for i in range(4)] + ["after.data"]
            missing_keys = [key for key in required_keys if key not in config_data]
            if missing_keys:
                self.finished.emit(None, f"missing_keys:{','.join(missing_keys)}")
                return

            self.finished.emit(config_data, "")
        except requests.exceptions.RequestException as e:
            error_msg = "访问云端配置失败，请检查网络状况或稍后再试。"
            if self.debug_mode:
                error_msg += f"\n详细错误: {e}"
            self.finished.emit(None, error_msg)
        except (ValueError, json.JSONDecodeError) as e:
            error_msg = "访问云端配置失败，请检查网络状况或稍后再试。"
            if self.debug_mode:
                error_msg += f"\nJSON解析失败: {e}"
            self.finished.emit(None, error_msg)
        finally:
            if self.debug_mode:
                logger.info("--- Finished fetching cloud config ---")
                
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