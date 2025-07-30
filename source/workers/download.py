import os
import sys
import subprocess
import re
from urllib.parse import urlparse
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import (Qt, Signal, QThread, QTimer)
from PySide6.QtWidgets import (QLabel, QProgressBar, QVBoxLayout, QDialog)
from utils import resource_path
from data.config import APP_NAME, UA

# 下载线程类
class DownloadThread(QThread):
    progress = Signal(dict)
    finished = Signal(bool, str)

    def __init__(self, url, _7z_path, game_version, parent=None):
        super().__init__(parent)
        self.url = url
        self._7z_path = _7z_path
        self.game_version = game_version
        self.process = None
        self._is_running = True

    def stop(self):
        if self.process and self.process.poll() is None:
            self._is_running = False
            try:
                # 使用 taskkill 强制终止进程及其子进程，并隐藏窗口
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"停止下载进程时出错: {e}")


    def run(self):
        try:
            if not self._is_running:
                self.finished.emit(False, "下载已手动停止。")
                return

            aria2c_path = resource_path("aria2c.exe")
            download_dir = os.path.dirname(self._7z_path)
            file_name = os.path.basename(self._7z_path)
            
            parsed_url = urlparse(self.url)
            referer = f"{parsed_url.scheme}://{parsed_url.netloc}/"
            
            command = [
                aria2c_path,
            ]

            command.extend([
                '--dir', download_dir,
                '--out', file_name,
                '--user-agent', UA,
                '--referer', referer,
                '--header', f'Origin: {referer.rstrip("/")}',
                '--header', 'Accept: */*',
                '--header', 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8',
                '--header', 'Accept-Encoding: gzip, deflate, br',
                '--header', 'Cache-Control: no-cache',
                '--header', 'Pragma: no-cache',
                '--header', 'DNT: 1',
                '--header', 'Sec-Fetch-Dest: empty',
                '--header', 'Sec-Fetch-Mode: cors',
                '--header', 'Sec-Fetch-Site: same-origin',
                '--http-accept-gzip=true',
                '--console-log-level=info',
                '--summary-interval=1',
                '--log-level=info',
                '--max-tries=3',
                '--retry-wait=2',
                '--connect-timeout=60',
                '--timeout=60',
                '--auto-file-renaming=false',
                '--allow-overwrite=true',
                '--split=16',
                '--max-connection-per-server=16'
            ])
            
            # 证书验证现在总是需要，因为我们依赖hosts文件
            command.append('--check-certificate=false')
            
            command.append(self.url)
            
            # 打印将要执行的命令，用于调试
            print(f"即将执行的 Aria2c 命令: {' '.join(command)}")

            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', creationflags=creation_flags)

            # 正则表达式用于解析aria2c的输出
            # 例如: #1 GID[...](  5%) CN:1 DL:10.5MiB/s ETA:1m30s
            progress_pattern = re.compile(r'\((\d{1,3})%\).*?CN:(\d+).*?DL:\s*([^\s]+).*?ETA:\s*([^\s\]]+)')

            full_output = []
            while self._is_running and self.process.poll() is None:
                if self.process.stdout:
                    line = self.process.stdout.readline()
                    if not line:
                        break
                else:
                    break
                
                full_output.append(line)
                print(line.strip()) # 在控制台输出实时日志

                match = progress_pattern.search(line)
                if match:
                    percent = int(match.group(1))
                    threads = match.group(2)
                    speed = match.group(3)
                    eta = match.group(4)
                    self.progress.emit({
                        "game": self.game_version,
                        "percent": percent,
                        "threads": threads,
                        "speed": speed,
                        "eta": eta
                    })

            return_code = self.process.wait()
            
            if not self._is_running: # 如果是手动停止的
                self.finished.emit(False, "下载已手动停止。")
                return

            if return_code == 0:
                self.progress.emit({
                    "game": self.game_version,
                    "percent": 100,
                    "threads": "N/A",
                    "speed": "N/A",
                    "eta": "完成"
                })
                self.finished.emit(True, "")
            else:
                error_message = f"\nAria2c下载失败，退出码: {return_code}\n\n--- Aria2c 输出 ---\n{''.join(full_output)}\n---------------------\n"
                self.finished.emit(False, error_message)

        except Exception as e:
            if self._is_running:
                self.finished.emit(False, f"\n下载时发生未知错误\n\n【错误信息】: {e}\n")

# 下载进度窗口类
class ProgressWindow(QDialog):
    def __init__(self, parent=None):
        super(ProgressWindow, self).__init__(parent)
        self.setWindowTitle(f"下载进度 - {APP_NAME}")
        self.resize(450, 180)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowSystemMenuHint)

        layout = QVBoxLayout()
        self.game_label = QLabel("正在启动下载，请稍后...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.stats_label = QLabel("速度: - | 线程: - | 剩余时间: -")
        self.stop_button = QtWidgets.QPushButton("停止下载")

        layout.addWidget(self.game_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.stats_label)
        layout.addWidget(self.stop_button)
        self.setLayout(layout)

    def update_progress(self, data):
        game_version = data.get("game", "未知游戏")
        percent = data.get("percent", 0)
        speed = data.get("speed", "-")
        threads = data.get("threads", "-")
        eta = data.get("eta", "-")
        
        # 清除ETA值中可能存在的"]"符号
        if isinstance(eta, str):
            eta = eta.replace("]", "")

        self.game_label.setText(f"正在下载 {game_version} 的补丁")
        self.progress_bar.setValue(int(percent))
        self.stats_label.setText(f"速度: {speed} | 线程: {threads} | 剩余时间: {eta}")

        if percent == 100:
            self.stop_button.setEnabled(False)
            self.stop_button.setText("下载完成")
            QTimer.singleShot(1500, self.accept)

    def closeEvent(self, event):
        # 覆盖默认的关闭事件，防止用户通过其他方式关闭窗口
        event.ignore()