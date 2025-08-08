import os
import shutil
import py7zr
from PySide6.QtCore import QThread, Signal
from data.config import PLUGIN, GAME_INFO

class ExtractionThread(QThread):
    finished = Signal(bool, str, str)  # success, error_message, game_version

    def __init__(self, _7z_path, game_folder, plugin_path, game_version, parent=None, extracted_path=None):
        super().__init__(parent)
        self._7z_path = _7z_path
        self.game_folder = game_folder
        self.plugin_path = plugin_path
        self.game_version = game_version
        self.extracted_path = extracted_path  # 添加已解压文件路径参数

    def run(self):
        try:
            # 如果提供了已解压文件路径，直接使用它
            if self.extracted_path and os.path.exists(self.extracted_path):
                # 直接复制已解压的文件到游戏目录
                os.makedirs(self.game_folder, exist_ok=True)
                shutil.copy(self.extracted_path, self.game_folder)
                
                # 对于NEKOPARA After，还需要复制签名文件
                if self.game_version == "NEKOPARA After":
                    # 从已解压文件的目录中获取签名文件
                    extracted_dir = os.path.dirname(self.extracted_path)
                    sig_filename = os.path.basename(GAME_INFO[self.game_version]["sig_path"])
                    sig_path = os.path.join(extracted_dir, sig_filename)
                    
                    # 如果签名文件存在，则复制它
                    if os.path.exists(sig_path):
                        shutil.copy(sig_path, self.game_folder)
                    else:
                        # 如果签名文件不存在，则使用原始路径
                        sig_path = os.path.join(PLUGIN, GAME_INFO[self.game_version]["sig_path"])
                        shutil.copy(sig_path, self.game_folder)
            else:
                # 如果没有提供已解压文件路径，执行正常的解压流程
                with py7zr.SevenZipFile(self._7z_path, mode="r") as archive:
                    archive.extractall(path=PLUGIN)
                
                os.makedirs(self.game_folder, exist_ok=True)
                shutil.copy(self.plugin_path, self.game_folder)
                
                if self.game_version == "NEKOPARA After":
                    sig_path = os.path.join(PLUGIN, GAME_INFO[self.game_version]["sig_path"])
                    shutil.copy(sig_path, self.game_folder)
                    
            self.finished.emit(True, "", self.game_version)
        except (py7zr.Bad7zFile, FileNotFoundError, Exception) as e:
            self.finished.emit(False, f"\n文件操作失败，请重试\n\n【错误信息】：{e}\n", self.game_version) 