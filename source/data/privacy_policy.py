#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
from datetime import datetime

# 隐私协议的缩略版内容
PRIVACY_POLICY_BRIEF = """
# FRAISEMOE Addons Installer NEXT 隐私政策摘要

本应用在运行过程中会收集和处理以下信息：

## 收集的信息
- **系统信息**：程序版本号。
- **网络信息**：IP 地址、ISP、地理位置（用于使用统计）、下载统计。
- **文件信息**：游戏安装路径、文件哈希值。

## 系统修改
- 使用 Cloudflare 加速时会临时修改系统 hosts 文件。
- 修改前会自动备份，程序退出时自动恢复。

## 第三方服务
- **Cloudflare 服务**：通过开源项目 CloudflareSpeedTest (CFST) 提供，用于优化下载速度。此过程会将您的 IP 提交至 Cloudflare 节点。
- **云端配置服务**：获取配置信息。服务器会记录您的 IP、ISP 及地理位置用于统计。

完整的隐私政策可在本程序的 GitHub 仓库中查看。
"""

# 隐私协议的英文版缩略版内容
PRIVACY_POLICY_BRIEF_EN = """
# FRAISEMOE Addons Installer NEXT Privacy Policy Summary

This application collects and processes the following information:

## Information Collected
- **System info**: Application version.
- **Network info**: IP address, ISP, geographic location (for usage statistics), download statistics.
- **File info**: Game installation paths, file hash values.

## System Modifications
- Temporarily modifies system hosts file when using Cloudflare acceleration.
- Automatically backs up before modification and restores upon exit.

## Third-party Services
- **Cloudflare services**: Provided via the open-source project CloudflareSpeedTest (CFST) to optimize download speeds. This process submits your IP to Cloudflare nodes.
- **Cloud configuration services**: For obtaining configuration information. The server logs your IP, ISP, and location for statistical purposes.

The complete privacy policy can be found in the program's GitHub repository.
"""

# 默认隐私协议版本 - 本地版本的日期
PRIVACY_POLICY_VERSION = "2025.07.31"

def get_local_privacy_policy():
    """获取本地打包的隐私协议文件
    
    Returns:
        tuple: (隐私协议内容, 版本号, 错误信息)
    """
    # 尝试不同的可能路径
    possible_paths = [
        "PRIVACY.md",  # 相对于可执行文件
        os.path.join(os.path.dirname(sys.executable), "PRIVACY.md"),  # 可执行文件目录
        os.path.join(os.path.dirname(__file__), "PRIVACY.md"),  # 当前模块目录
    ]
    
    for path in possible_paths:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # 提取更新日期
                date_pattern = r'最后更新日期：(\d{4}年\d{1,2}月\d{1,2}日)'
                match = re.search(date_pattern, content)
                
                if match:
                    date_str = match.group(1)
                    try:
                        date_obj = datetime.strptime(date_str, '%Y年%m月%d日')
                        date_version = date_obj.strftime('%Y.%m.%d')
                        print(f"成功读取本地隐私协议文件: {path}, 版本: {date_version}")
                        return content, date_version, ""
                    except ValueError:
                        print(f"本地隐私协议日期格式解析错误: {path}")
                else:
                    print(f"本地隐私协议未找到更新日期: {path}")
        except Exception as e:
            print(f"读取本地隐私协议失败 {path}: {str(e)}")
    
    # 所有路径都尝试失败，使用默认版本
    return PRIVACY_POLICY_BRIEF, PRIVACY_POLICY_VERSION, "无法读取本地隐私协议文件" 