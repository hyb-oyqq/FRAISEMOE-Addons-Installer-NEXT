import os
import re
import subprocess
import sys
from urllib.parse import urlparse

from utils import resource_path

def get_optimal_ip(url: str) -> str | None:
    """
    使用 CloudflareSpeedTest 工具获取给定 URL 的最优 Cloudflare IP。

    Args:
        url: 需要进行优选的下载链接。

    Returns:
        最优的 IP 地址字符串，如果找不到则返回 None。
    """
    try:
        # 1. 定位 CloudflareSpeedTest 工具路径，使用新的文件名 cfst.exe
        cst_path = resource_path("cfst.exe")
        if not os.path.exists(cst_path):
            print(f"错误: cfst.exe 未在资源路径中找到。")
            return None

        # 2. 构建命令行参数
        # -p 1: 只输出最快的一个 IP
        # -o "": 不生成 result.csv 文件
        # -url: 指定我们自己的测速链接
        # -f: 指定 ip.txt 的路径
        ip_txt_path = resource_path("ip.txt")
        command = [
            cst_path,
            "-p", "1",
            "-o", "",
            "-url", url,
            "-f", ip_txt_path,
            "-dd",
        ]

        # 3. 执行命令并捕获输出
        # 使用 CREATE_NO_WINDOW 标志来隐藏控制台窗口
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=creation_flags,
            bufsize=1, # 使用行缓冲
          )

        # 4. 实时读取、打印并解析输出
        print("--- CloudflareSpeedTest 实时输出 ---")
        
        if not process.stdout:
            print("错误: 无法获取子进程的输出流。")
            return None

        # 根据用户提供的最新格式更新正则表达式
        # 格式: IP  Sent  Recv  Loss  Avg-Latency  DL-Speed  Region
        ip_pattern = re.compile(r'^\s*([\d\.]+)\s+\d+\s+\d+\s+[\d\.]+%?\s+[\d\.]+\s+[\d\.]+\s+.*$')
        fd = process.stdout.fileno()
        buffer = b''
        
        while process.poll() is None:
            try:
                chunk = os.read(fd, 1024)
                if not chunk:
                    break
                buffer += chunk
                
                while b'\n' in buffer or b'\r' in buffer:
                    end_index_n = buffer.find(b'\n')
                    end_index_r = buffer.find(b'\r')
                    end_index = min(end_index_n, end_index_r) if end_index_n != -1 and end_index_r != -1 else max(end_index_n, end_index_r)
                    
                    line_bytes = buffer[:end_index]
                    line = line_bytes.decode('utf-8', errors='replace').strip()
                    
                    if line:
                        print(line)
                        match = ip_pattern.match(line)
                        if match:
                            optimal_ip = match.group(1)
                            print(f"找到最优 IP: {optimal_ip}, 正在终止测速进程...")
                            print("------------------------------------")
                            process.terminate() # 终止进程
                            return optimal_ip
                    
                    buffer = buffer[end_index+1:]

            except (IOError, OSError):
                break
        
        # 处理可能残留在缓冲区的数据
        if buffer:
            line = buffer.decode('utf-8', errors='replace').strip()
            if line:
                print(line)
                match = ip_pattern.match(line)
                if match:
                    optimal_ip = match.group(1)
                    print(f"找到最优 IP: {optimal_ip}")
                    print("------------------------------------")
                    process.terminate() # 确保在返回前终止进程
                    return optimal_ip

        print("------------------------------------")

        # 5. 在循环结束后，检查是否找到了 IP
        # （IP 在循环内部找到并返回）
        process.wait() # 等待进程完全终止
        print("警告: 未能在 CloudflareSpeedTest 输出中找到最优 IP。")
        return None

    except Exception as e:
        print(f"执行 CloudflareSpeedTest 时发生错误: {e}")
        return None

if __name__ == '__main__':
    # 用于直接测试此模块
    test_url = "https://speed.cloudflare.com/__down?during=download&bytes=104857600"
    ip = get_optimal_ip(test_url)
    if ip:
        print(f"为 {test_url} 找到的最优 IP 是: {ip}")
    else:
        print(f"未能为 {test_url} 找到最优 IP。")