import os
import shutil
import py7zr
from PySide6.QtCore import QThread, Signal
from config.config import PLUGIN, GAME_INFO

class ExtractionThread(QThread):
    finished = Signal(bool, str, str)  # success, error_message, game_version
    progress = Signal(int, str)  # 添加进度信号，传递进度百分比和状态信息

    def __init__(self, _7z_path, game_folder, plugin_path, game_version, parent=None, extracted_path=None):
        super().__init__(parent)
        self._7z_path = _7z_path
        self.game_folder = game_folder
        self.plugin_path = plugin_path
        self.game_version = game_version
        self.extracted_path = extracted_path  # 添加已解压文件路径参数

    def run(self):
        try:
            # 确保游戏目录存在
            os.makedirs(self.game_folder, exist_ok=True)

            def update_progress(percent: int, message: str):
                try:
                    self.progress.emit(percent, message)
                except Exception:
                    pass

            update_progress(0, f"开始处理 {self.game_version} 的补丁文件...")

            # 支持外部请求中断
            if self.isInterruptionRequested():
                self.finished.emit(False, "操作已取消", self.game_version)
                return

            # 如果提供了已解压文件路径，直接使用它
            if self.extracted_path and os.path.exists(self.extracted_path):
                update_progress(20, f"正在复制 {self.game_version} 的补丁文件...\n(在此过程中可能会卡顿或无响应，请不要关闭软件)")

                # 直接复制已解压的文件到游戏目录
                target_file = os.path.join(self.game_folder, os.path.basename(self.plugin_path))
                shutil.copy(self.extracted_path, target_file)

                update_progress(60, f"正在完成 {self.game_version} 的补丁安装...")

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

                update_progress(100, f"{self.game_version} 补丁文件处理完成")
                self.finished.emit(True, "", self.game_version)
                return

            # 否则解压源压缩包到临时目录，再复制目标文件
            target_filename = os.path.basename(self.plugin_path)
            target_path = os.path.join(self.game_folder, target_filename)

            update_progress(10, f"正在打开 {self.game_version} 的补丁压缩包...")

            with py7zr.SevenZipFile(self._7z_path, mode="r") as archive:
                # 获取压缩包内的文件列表
                file_list = archive.getnames()

                update_progress(20, f"正在分析 {self.game_version} 的补丁文件...")

                # 查找压缩包内的目标文件
                target_file_in_archive = None
                for file_path in file_list:
                    if target_filename in file_path:
                        target_file_in_archive = file_path
                        break

                if not target_file_in_archive:
                    raise FileNotFoundError(f"在压缩包中未找到目标文件 {target_filename}")

                update_progress(30, f"正在解压 {self.game_version} 的补丁文件...\n(在此过程中可能会卡顿或无响应，请不要关闭软件)")

                import tempfile
                with tempfile.TemporaryDirectory() as temp_dir:
                    # 解压特定文件到临时目录
                    archive.extract(path=temp_dir, targets=[target_file_in_archive])

                    update_progress(60, f"正在复制 {self.game_version} 的补丁文件...")

                    # 找到解压后的文件
                    extracted_file_path = os.path.join(temp_dir, target_file_in_archive)

                    # 复制到目标位置
                    shutil.copy2(extracted_file_path, target_path)

                    update_progress(80, f"正在完成 {self.game_version} 的补丁安装...")

                    # 对于NEKOPARA After，还需要复制签名文件
                    if self.game_version == "NEKOPARA After":
                        sig_filename = f"{target_filename}.sig"
                        sig_file_in_archive = None

                        # 查找签名文件
                        for file_path in file_list:
                            if sig_filename in file_path:
                                sig_file_in_archive = file_path
                                break

                        if sig_file_in_archive:
                            # 解压签名文件
                            archive.extract(path=temp_dir, targets=[sig_file_in_archive])
                            extracted_sig_path = os.path.join(temp_dir, sig_file_in_archive)
                            sig_target = os.path.join(self.game_folder, sig_filename)
                            shutil.copy2(extracted_sig_path, sig_target)
                        else:
                            # 如果签名文件不存在，则使用原始路径
                            sig_path = os.path.join(PLUGIN, GAME_INFO[self.game_version]["sig_path"])
                            if os.path.exists(sig_path):
                                sig_target = os.path.join(self.game_folder, sig_filename)
                                shutil.copy2(sig_path, sig_target)

            update_progress(100, f"{self.game_version} 补丁文件解压完成")
            self.finished.emit(True, "", self.game_version)
        except (py7zr.Bad7zFile, FileNotFoundError, Exception) as e:
            try:
                self.progress.emit(100, f"处理 {self.game_version} 的补丁文件失败")
            except Exception:
                pass
            self.finished.emit(False, f"\n文件操作失败，请重试\n\n【错误信息】：{e}\n", self.game_version) 