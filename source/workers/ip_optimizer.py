import os
import re
import subprocess
import sys
import time
from urllib.parse import urlparse

from PySide6.QtCore import QThread, Signal
from utils import resource_path

class IpOptimizer:
    def __init__(self):
        self.process = None

    def get_optimal_ip(self, url: str) -> str | None:
        """
        使用 CloudflareSpeedTest 工具获取给定 URL 的最优 Cloudflare IP。

        Args:
            url: 需要进行优选的下载链接。

        Returns:
            最优的 IP 地址字符串，如果找不到则返回 None。
        """
        try:
            cst_path = resource_path("cfst.exe")
            if not os.path.exists(cst_path):
                print(f"错误: cfst.exe 未在资源路径中找到。")
                return None

            ip_txt_path = resource_path("ip.txt")
            
            # 正确的参数设置，根据cfst帮助文档
            command = [
                cst_path,
                "-n", "500",     # 延迟测速线程数 (默认200)
                "-p", "1",       # 显示结果数量 (默认10个)
                "-url", url,     # 指定测速地址
                "-f", ip_txt_path,   # IP文件
                "-dd",           # 禁用下载测速，按延迟排序
            ]

            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            
            print("--- CloudflareSpeedTest 开始执行 ---")
            
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=creation_flags,
                bufsize=0
            )

            # 更新正则表达式以匹配cfst输出中的IP格式
            # 匹配格式: IP地址在行首，后面跟着一些数字和文本
            ip_pattern = re.compile(r'^(\d+\.\d+\.\d+\.\d+)\s+.*')
            
            # 标记是否已经找到结果表头和完成标记
            found_header = False
            found_completion = False

            stdout = self.process.stdout
            if not stdout:
                print("错误: 无法获取子进程的输出流。")
                return None

            optimal_ip = None
            timeout_counter = 0
            max_timeout = 300  # 增加超时时间到5分钟

            while True:
                if self.process.poll() is not None:
                    break
                try:
                    ready = True
                    try:
                        line = stdout.readline()
                    except:
                        ready = False
                        
                    if not ready or not line:
                        timeout_counter += 1
                        if timeout_counter > max_timeout:
                            print("超时: CloudflareSpeedTest 响应超时")
                            break
                        time.sleep(1)
                        continue
                    
                    timeout_counter = 0
                    
                    cleaned_line = line.strip()
                    if cleaned_line:
                        print(cleaned_line)
                        
                        # 检测结果表头
                        if "IP 地址" in cleaned_line and "平均延迟" in cleaned_line:
                            print("检测到IP结果表头，准备获取IP地址...")
                            found_header = True
                            continue
                        
                        # 检测完成标记
                        if "完整测速结果已写入" in cleaned_line or "按下 回车键 或 Ctrl+C 退出" in cleaned_line:
                            print("检测到测速完成信息")
                            found_completion = True
                            
                            # 如果已经找到了IP，可以退出了
                            if optimal_ip:
                                break
                        
                        # 已找到表头后，尝试匹配IP地址行
                        if found_header:
                            match = ip_pattern.search(cleaned_line)
                            if match and not optimal_ip:  # 只保存第一个匹配的IP（最优IP）
                                optimal_ip = match.group(1)
                                print(f"找到最优 IP: {optimal_ip}")
                                
                                # 如果已经看到完成标记，可以退出了
                                if found_completion:
                                    break
                            
                except Exception as e:
                    print(f"读取输出时发生错误: {e}")
                    break
            
            # 确保完全读取输出后再发送退出信号
            if self.process and self.process.poll() is None:
                try:
                    if self.process.stdin and not self.process.stdin.closed:
                        print("发送退出信号...")
                        self.process.stdin.write('\n')
                        self.process.stdin.flush()
                except:
                    pass
            
            self.stop()
            
            print("--- CloudflareSpeedTest 执行结束 ---")
            return optimal_ip

        except Exception as e:
            print(f"执行 CloudflareSpeedTest 时发生错误: {e}")
            return None

    def stop(self):
        if self.process and self.process.poll() is None:
            print("正在终止 CloudflareSpeedTest 进程...")
            try:
                if self.process.stdin and not self.process.stdin.closed:
                    self.process.stdin.write('\n')
                    self.process.stdin.flush()
                    self.process.stdin.close()
            except:
                pass
            
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            print("CloudflareSpeedTest 进程已终止。")


class IpOptimizerThread(QThread):
    """用于在后台线程中运行IP优化的类"""
    finished = Signal(str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.optimizer = IpOptimizer()

    def run(self):
        optimal_ip = self.optimizer.get_optimal_ip(self.url)
        self.finished.emit(optimal_ip if optimal_ip else "")

    def stop(self):
        self.optimizer.stop()


if __name__ == '__main__':
    # 用于直接测试此模块
    test_url = "https://speed.cloudflare.com/__down?during=download&bytes=104857600"
    optimizer = IpOptimizer()
    ip = optimizer.get_optimal_ip(test_url)
    if ip:
        print(f"为 {test_url} 找到的最优 IP 是: {ip}")
    else:
        print(f"未能为 {test_url} 找到最优 IP。") 