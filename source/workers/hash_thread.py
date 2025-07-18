from PySide6.QtCore import QThread, Signal
from utils import HashManager
from data.config import BLOCK_SIZE

class HashThread(QThread):
    pre_finished = Signal(dict)
    after_finished = Signal(dict)

    def __init__(self, mode, install_paths, plugin_hash, installed_status, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.install_paths = install_paths
        self.plugin_hash = plugin_hash
        self.installed_status = installed_status
        # 每个线程都应该有自己的HashManager实例
        self.hash_manager = HashManager(BLOCK_SIZE)

    def run(self):
        if self.mode == "pre":
            updated_status = self.hash_manager.cfg_pre_hash_compare(
                self.install_paths, self.plugin_hash, self.installed_status
            )
            self.pre_finished.emit(updated_status)
        elif self.mode == "after":
            result = self.hash_manager.cfg_after_hash_compare(
                self.install_paths, self.plugin_hash, self.installed_status
            )
            self.after_finished.emit(result) 