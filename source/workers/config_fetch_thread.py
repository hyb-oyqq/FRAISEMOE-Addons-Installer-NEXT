import json
import requests
import webbrowser
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QMessageBox
import sys

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
                print("--- Starting to fetch cloud config ---")
                print(f"DEBUG: Requesting URL: {self.url}")
                print(f"DEBUG: Using Headers: {self.headers}")

            response = requests.get(self.url, headers=self.headers, timeout=10)

            if self.debug_mode:
                print(f"DEBUG: Response Status Code: {response.status_code}")
                print(f"DEBUG: Response Headers: {response.headers}")
                print(f"DEBUG: Response Text: {response.text}")

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
                print("--- Finished fetching cloud config ---") 