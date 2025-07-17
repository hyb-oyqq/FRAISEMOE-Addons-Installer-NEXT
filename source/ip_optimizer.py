import os
import re
import subprocess
import sys
import time
from urllib.parse import urlparse

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
            command = [
                cst_path,
                "-p", "1",
                "-o", "",
                "-url", url,
                "-f", ip_txt_path,
                "-dd",
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

            # 立即向 stdin 发送换行符，以便程序在 Windows 下正常退出
            if self.process.stdin:
                try:
                    self.process.stdin.write('\n')
                    self.process.stdin.flush()
                except:
                    pass
                finally:
                    self.process.stdin.close()

            ip_pattern = re.compile(r'^\s*([\d\.]+)\s+\d+\s+\d+\s+[\d\.]+%?\s+[\d\.]+\s+[\d\.]+\s+.*$')

            stdout = self.process.stdout
            if not stdout:
                print("错误: 无法获取子进程的输出流。")
                return None

            optimal_ip = None
            timeout_counter = 0
            max_timeout = 60

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
                        match = ip_pattern.match(cleaned_line)
                        if match:
                            optimal_ip = match.group(1)
                            print(f"找到最优 IP: {optimal_ip}, 正在终止测速进程...")
                            break
                            
                except Exception as e:
                    print(f"读取输出时发生错误: {e}")
                    break
            
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

if __name__ == '__main__':
    # 用于直接测试此模块
    test_url = "https://speed.cloudflare.com/__down?during=download&bytes=104857600"
    optimizer = IpOptimizer()
    ip = optimizer.get_optimal_ip(test_url)
    if ip:
        print(f"为 {test_url} 找到的最优 IP 是: {ip}")
    else:
        print(f"未能为 {test_url} 找到最优 IP。")