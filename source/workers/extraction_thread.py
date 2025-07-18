import os
import shutil
import py7zr
from PySide6.QtCore import QThread, Signal
from data.config import PLUGIN, GAME_INFO

class ExtractionThread(QThread):
    finished = Signal(bool, str, str)  # success, error_message, game_version

    def __init__(self, _7z_path, game_folder, plugin_path, game_version, parent=None):
        super().__init__(parent)
        self._7z_path = _7z_path
        self.game_folder = game_folder
        self.plugin_path = plugin_path
        self.game_version = game_version

    def run(self):
        try:
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