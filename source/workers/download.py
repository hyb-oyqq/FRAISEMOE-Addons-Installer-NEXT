import os
import sys
import subprocess
import re
from urllib.parse import urlparse
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import (Qt, Signal, QThread, QTimer)
from PySide6.QtWidgets import (QLabel, QProgressBar, QVBoxLayout, QDialog, QHBoxLayout)
from utils import resource_path
from data.config import APP_NAME, UA
import signal
import ctypes
import time

# Windows API常量和函数
if sys.platform == 'win32':
    kernel32 = ctypes.windll.kernel32
    PROCESS_ALL_ACCESS = 0x1F0FFF
    THREAD_SUSPEND_RESUME = 0x0002
    TH32CS_SNAPTHREAD = 0x00000004
    
    class THREADENTRY32(ctypes.Structure):
        _fields_ = [
            ('dwSize', ctypes.c_ulong),
            ('cntUsage', ctypes.c_ulong),
            ('th32ThreadID', ctypes.c_ulong),
            ('th32OwnerProcessID', ctypes.c_ulong),
            ('tpBasePri', ctypes.c_ulong),
            ('tpDeltaPri', ctypes.c_ulong),
            ('dwFlags', ctypes.c_ulong)
        ]

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
        self._is_paused = False
        self.threads = []

    def stop(self):
        if self.process and self.process.poll() is None:
            self._is_running = False
            try:
                # 使用 taskkill 强制终止进程及其子进程，并隐藏窗口
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"停止下载进程时出错: {e}")

    def _get_process_threads(self, pid):
        """获取进程的所有线程ID"""
        if sys.platform != 'win32':
            return []
            
        thread_ids = []
        h_snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
        if h_snapshot == -1:
            return []
        
        thread_entry = THREADENTRY32()
        thread_entry.dwSize = ctypes.sizeof(THREADENTRY32)
        
        res = kernel32.Thread32First(h_snapshot, ctypes.byref(thread_entry))
        while res:
            if thread_entry.th32OwnerProcessID == pid:
                thread_ids.append(thread_entry.th32ThreadID)
            res = kernel32.Thread32Next(h_snapshot, ctypes.byref(thread_entry))
            
        kernel32.CloseHandle(h_snapshot)
        return thread_ids
                
    def pause(self):
        """暂停下载进程"""
        if not self._is_paused and self.process and self.process.poll() is None:
            try:
                if sys.platform == 'win32':
                    # 获取所有线程
                    self.threads = self._get_process_threads(self.process.pid)
                    if not self.threads:
                        print("未找到可暂停的线程")
                        return False
                        
                    # 暂停所有线程
                    for thread_id in self.threads:
                        h_thread = kernel32.OpenThread(THREAD_SUSPEND_RESUME, False, thread_id)
                        if h_thread:
                            kernel32.SuspendThread(h_thread)
                            kernel32.CloseHandle(h_thread)
                            
                    self._is_paused = True
                    print(f"下载进程已暂停: PID {self.process.pid}, 线程数: {len(self.threads)}")
                    return True
                else:
                    # 在Unix系统上使用SIGSTOP
                    os.kill(self.process.pid, signal.SIGSTOP)
                    self._is_paused = True
                    print(f"下载进程已暂停: PID {self.process.pid}")
                    return True
            except Exception as e:
                print(f"暂停下载进程时出错: {e}")
                return False
        return False
                
    def resume(self):
        """恢复下载进程"""
        if self._is_paused and self.process and self.process.poll() is None:
            try:
                if sys.platform == 'win32':
                    # 恢复所有线程
                    for thread_id in self.threads:
                        h_thread = kernel32.OpenThread(THREAD_SUSPEND_RESUME, False, thread_id)
                        if h_thread:
                            kernel32.ResumeThread(h_thread)
                            kernel32.CloseHandle(h_thread)
                            
                    self._is_paused = False
                    print(f"下载进程已恢复: PID {self.process.pid}, 线程数: {len(self.threads)}")
                    return True
                else:
                    # 在Unix系统上使用SIGCONT
                    os.kill(self.process.pid, signal.SIGCONT)
                    self._is_paused = False
                    print(f"下载进程已恢复: PID {self.process.pid}")
                    return True
            except Exception as e:
                print(f"恢复下载进程时出错: {e}")
                return False
        return False

    def is_paused(self):
        """返回当前下载是否处于暂停状态"""
        return self._is_paused

    def run(self):
        try:
            if not self._is_running:
                self.finished.emit(False, "下载已手动停止。")
                return

            aria2c_path = resource_path("aria2c-fast_x64.exe")
            download_dir = os.path.dirname(self._7z_path)
            file_name = os.path.basename(self._7z_path)

            parsed_url = urlparse(self.url)
            referer = f"{parsed_url.scheme}://{parsed_url.netloc}/"

            command = [
                aria2c_path,
            ]
            
            # 获取主窗口的下载管理器对象
            thread_count = 64 # 默认值
            if hasattr(self.parent(), 'download_manager'):
                # 从下载管理器获取线程数设置
                thread_count = self.parent().download_manager.get_download_thread_count()

            # 检查是否启用IPv6支持
            ipv6_enabled = False
            if hasattr(self.parent(), 'config'):
                ipv6_enabled = self.parent().config.get("ipv6_enabled", False)

            # 打印IPv6状态
            print(f"IPv6支持状态: {ipv6_enabled}")
            
            # 将所有的优化参数应用于每个下载任务
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
                '--console-log-level=notice',
                '--summary-interval=1',
                '--log-level=notice',
                '--max-tries=3',
                '--retry-wait=2',
                '--connect-timeout=60',
                '--timeout=60',
                '--auto-file-renaming=false',
                '--allow-overwrite=true',
                '--split=128',
                f'--max-connection-per-server={thread_count}', # 使用动态的线程数
                '--min-split-size=1M', # 减小最小分片大小
                '--optimize-concurrent-downloads=true', # 优化并发下载
                '--file-allocation=none', # 禁用文件预分配加快开始
                '--async-dns=true', # 使用异步DNS
            ])

            # 根据IPv6设置决定是否禁用IPv6
            if not ipv6_enabled:
                command.append('--disable-ipv6=true')
                print("已禁用IPv6支持")
            else:
                print("已启用IPv6支持")

            # 证书验证现在总是需要，因为我们依赖hosts文件
            command.append('--check-certificate=false')
            
            command.append(self.url)
            
            # 打印将要执行的命令，用于调试
            print(f"即将执行的 Aria2c 命令: {' '.join(command)}")

            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', creationflags=creation_flags)

            # 正则表达式用于解析aria2c的输出
            # 例如: #1 GID[...]](  5%) CN:1 DL:10.5MiB/s ETA:1m30s
            progress_pattern = re.compile(r'\((\d{1,3})%\).*?CN:(\d+).*?DL:\s*([^\s]+).*?ETA:\s*([^\s\]]+)')
            
            # 添加限流计时器，防止更新过于频繁导致UI卡顿
            last_update_time = 0
            update_interval = 0.2  # 限制UI更新频率，每0.2秒最多更新一次
            
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
                    # 检查是否达到更新间隔
                    current_time = time.time()
                    if current_time - last_update_time >= update_interval:
                        percent = int(match.group(1))
                        threads = match.group(2)
                        speed = match.group(3)
                        eta = match.group(4)
                        
                        # 直接发送进度信号，不使用invokeMethod
                        self.progress.emit({
                            "game": self.game_version,
                            "percent": percent,
                            "threads": threads,
                            "speed": speed,
                            "eta": eta
                        })
                        
                        last_update_time = current_time

            return_code = self.process.wait()

            if not self._is_running:
                # 如果是手动停止的
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
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        # 创建暂停/恢复按钮
        self.pause_resume_button = QtWidgets.QPushButton("暂停下载")
        self.pause_resume_button.setToolTip("暂停或恢复下载")
        
        # 创建停止按钮
        self.stop_button = QtWidgets.QPushButton("取消下载")
        self.stop_button.setToolTip("取消整个下载过程")
        
        # 添加按钮到按钮布局
        button_layout.addWidget(self.pause_resume_button)
        button_layout.addWidget(self.stop_button)

        layout.addWidget(self.game_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.stats_label)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # 设置暂停/恢复状态
        self.is_paused = False
        # 添加最后进度记录，用于优化UI更新
        self._last_percent = -1
        
    def update_pause_button_state(self, is_paused):
        """更新暂停按钮的显示状态
        
        Args:
            is_paused: 是否处于暂停状态
        """
        self.is_paused = is_paused
        if is_paused:
            self.pause_resume_button.setText("恢复下载")
        else:
            self.pause_resume_button.setText("暂停下载")

    def update_progress(self, data):
        game_version = data.get("game", "未知游戏")
        percent = data.get("percent", 0)
        speed = data.get("speed", "-")
        threads = data.get("threads", "-")
        eta = data.get("eta", "-")
        
        # 清除ETA值中可能存在的"]"符号
        if isinstance(eta, str):
            eta = eta.replace("]", "")
        
        # 优化UI更新
        if hasattr(self, '_last_percent') and self._last_percent == percent and percent < 100:
            # 如果百分比没变，只更新速度和ETA信息
            self.stats_label.setText(f"速度: {speed} | 线程: {threads} | 剩余时间: {eta}")
        else:
            # 百分比变化或初次更新，更新所有信息
            self._last_percent = percent
            self.game_label.setText(f"正在下载 {game_version} 的补丁")
            self.progress_bar.setValue(int(percent))
            self.stats_label.setText(f"速度: {speed} | 线程: {threads} | 剩余时间: {eta}")

        if percent == 100:
            self.pause_resume_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.stop_button.setText("下载完成")
            QTimer.singleShot(1500, self.accept)

    def closeEvent(self, event):
        # 覆盖默认的关闭事件，防止用户通过其他方式关闭窗口
        event.ignore()