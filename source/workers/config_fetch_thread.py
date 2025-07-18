import json
import requests
from PySide6.QtCore import QThread, Signal

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

            # 检查是否是要求更新的错误信息
            if config_data.get("message") == "请使用最新版本的FRAISEMOE Addons Installer NEXT进行下载安装":
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
            self.finished.emit(None, f"网络请求失败: {e}")
        except (ValueError, json.JSONDecodeError) as e:
            self.finished.emit(None, f"JSON解析失败: {e}")
        finally:
            if self.debug_mode:
                print("--- Finished fetching cloud config ---") 