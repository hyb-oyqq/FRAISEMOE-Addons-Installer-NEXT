import os
import re
import subprocess
import sys
import time
from urllib.parse import urlparse

from PySide6.QtCore import QThread, Signal
from utils import resource_path
from utils.logger import setup_logger
from utils.url_censor import censor_url

# 初始化logger
logger = setup_logger("ip_optimizer")

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
                logger.error(f"错误: cfst.exe 未在资源路径中找到。")
                return None

            ip_txt_path = resource_path("ip.txt")
            
            # 隐藏敏感URL
            safe_url = "***URL protection***"
            
            command = [
                cst_path,
                "-n", "1000",     # 延迟测速线程数
                "-p", "1",       # 显示结果数量
                "-url", url,
                "-f", ip_txt_path,
                "-dd",           # 禁用下载测速
                "-o"," "         # 不写入结果文件
            ]
            
            # 创建用于显示的安全命令副本
            safe_command = command.copy()
            for i, arg in enumerate(safe_command):
                if arg == url:
                    safe_command[i] = safe_url

            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            
            logger.info("--- CloudflareSpeedTest 开始执行 ---")
            logger.info(f"执行命令: {' '.join(safe_command)}")
            
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

            # 匹配格式: IP地址在行首，后面跟着一些数字和文本
            ip_pattern = re.compile(r'^(\d+\.\d+\.\d+\.\d+)\s+.*')
            
            found_header = False
            found_completion = False

            stdout = self.process.stdout
            if not stdout:
                logger.error("错误: 无法获取子进程的输出流。")
                return None

            optimal_ip = None
            timeout_counter = 0
            max_timeout = 300  # 超时时间5分钟

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
                            logger.warning("超时: CloudflareSpeedTest 响应超时")
                            break
                        time.sleep(1)
                        continue
                    
                    timeout_counter = 0
                    
                    # 处理输出行，隐藏可能包含的URL
                    cleaned_line = censor_url(line.strip())
                    if cleaned_line:
                        logger.debug(cleaned_line)
                        
                        if "IP 地址" in cleaned_line and "平均延迟" in cleaned_line:
                            logger.info("检测到IP结果表头，准备获取IP地址...")
                            found_header = True
                            continue
                        
                        if "完整测速结果已写入" in cleaned_line or "按下 回车键 或 Ctrl+C 退出" in cleaned_line:
                            logger.info("检测到测速完成信息")
                            found_completion = True
                            
                            if optimal_ip:
                                break
                        
                        if found_header:
                            match = ip_pattern.search(cleaned_line)
                            if match and not optimal_ip:
                                optimal_ip = match.group(1)
                                logger.info(f"找到最优 IP: {optimal_ip}")
                                break
                            
                except Exception as e:
                    logger.error(f"读取输出时发生错误: {e}")
                    break
            
            if self.process and self.process.poll() is None:
                try:
                    if self.process.stdin and not self.process.stdin.closed:
                        logger.debug("发送退出信号...")
                        self.process.stdin.write('\n')
                        self.process.stdin.flush()
                except:
                    pass
            
            self.stop()
            
            logger.info("--- CloudflareSpeedTest 执行结束 ---")
            return optimal_ip

        except Exception as e:
            logger.error(f"执行 CloudflareSpeedTest 时发生错误: {e}")
            return None

    def get_optimal_ipv6(self, url: str) -> str | None:
        """
        使用 CloudflareSpeedTest 工具获取给定 URL 的最优 Cloudflare IPv6 地址。

        Args:
            url: 需要进行优选的下载链接。

        Returns:
            最优的 IPv6 地址字符串，如果找不到则返回 None。
        """
        try:
            cst_path = resource_path("cfst.exe")
            if not os.path.exists(cst_path):
                logger.error(f"错误: cfst.exe 未在资源路径中找到。")
                return None

            ipv6_txt_path = resource_path("data/ipv6.txt")
            if not os.path.exists(ipv6_txt_path):
                logger.error(f"错误: ipv6.txt 未在资源路径中找到。")
                return None
            
            # 隐藏敏感URL
            safe_url = "***URL protection***"
            
            command = [
                cst_path,
                "-n", "1000",     # 延迟测速线程数
                "-p", "1",       # 显示结果数量
                "-url", url,
                "-f", ipv6_txt_path,
                "-dd",           # 禁用下载测速
                "-o", " "        # 不写入结果文件
            ]
            
            # 创建用于显示的安全命令副本
            safe_command = command.copy()
            for i, arg in enumerate(safe_command):
                if arg == url:
                    safe_command[i] = safe_url

            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            
            logger.info("--- CloudflareSpeedTest IPv6 开始执行 ---")
            logger.info(f"执行命令: {' '.join(safe_command)}")
            
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

            # IPv6格式可能有多种表示形式
            ipv6_pattern = re.compile(r'^([0-9a-fA-F:]+)\s+.*')
            
            found_header = False
            found_completion = False

            stdout = self.process.stdout
            if not stdout:
                logger.error("错误: 无法获取子进程的输出流。")
                return None

            optimal_ipv6 = None
            timeout_counter = 0
            max_timeout = 300  # 超时时间5分钟

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
                            logger.warning("超时: CloudflareSpeedTest IPv6 响应超时")
                            break
                        time.sleep(1)
                        continue
                    
                    timeout_counter = 0
                    
                    # 处理输出行，隐藏可能包含的URL
                    cleaned_line = censor_url(line.strip())
                    if cleaned_line:
                        logger.debug(cleaned_line)
                        
                        if "IP 地址" in cleaned_line and "平均延迟" in cleaned_line:
                            logger.info("检测到IPv6结果表头，准备获取IPv6地址...")
                            found_header = True
                            continue
                        
                        if "完整测速结果已写入" in cleaned_line or "按下 回车键 或 Ctrl+C 退出" in cleaned_line:
                            logger.info("检测到IPv6测速完成信息")
                            found_completion = True
                            
                            if optimal_ipv6:
                                break
                        
                        if found_header:
                            match = ipv6_pattern.search(cleaned_line)
                            if match and not optimal_ipv6:
                                optimal_ipv6 = match.group(1)
                                logger.info(f"找到最优 IPv6: {optimal_ipv6}")
                                break
                            
                except Exception as e:
                    logger.error(f"读取输出时发生错误: {e}")
                    break
            
            if self.process and self.process.poll() is None:
                try:
                    if self.process.stdin and not self.process.stdin.closed:
                        logger.debug("发送退出信号...")
                        self.process.stdin.write('\n')
                        self.process.stdin.flush()
                except:
                    pass
            
            self.stop()
            
            logger.info("--- CloudflareSpeedTest IPv6 执行结束 ---")
            return optimal_ipv6

        except Exception as e:
            logger.error(f"执行 CloudflareSpeedTest IPv6 时发生错误: {e}")
            return None

    def stop(self):
        if self.process and self.process.poll() is None:
            logger.info("正在终止 CloudflareSpeedTest 进程...")
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
            logger.info("CloudflareSpeedTest 进程已终止。")


class IpOptimizerThread(QThread):
    """用于在后台线程中运行IP优化的类
    
    注意：IPv6连接测试功能已迁移至IPv6Manager类，
    本类仅负责IP优化相关功能
    """
    finished = Signal(str)

    def __init__(self, url, parent=None, use_ipv6=False):
        super().__init__(parent)
        self.url = url
        self.optimizer = IpOptimizer()
        self.use_ipv6 = use_ipv6

    def run(self):
        if self.use_ipv6:
            optimal_ip = self.optimizer.get_optimal_ipv6(self.url)
        else:
            optimal_ip = self.optimizer.get_optimal_ip(self.url)
        self.finished.emit(optimal_ip if optimal_ip else "")

    def stop(self):
        self.optimizer.stop()
