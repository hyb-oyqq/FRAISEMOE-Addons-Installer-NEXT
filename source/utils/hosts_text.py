"""hosts 文件的纯文本处理。

parse_entries / find_ips_for_host 搬运自 HostsManager.get_hostname_entries
（该处逻辑正确，按字段分词匹配）。

remove_host_entries 搬运自 HostsManager.clean_hostname_entries，
**照搬其整行子串匹配缺陷**——它会误删 cdn.<域名> 与注释行。

strip_marked_block 搬运自 HostsManager.check_and_clean_all_entries，
**照搬其「遇标记则无条件丢弃下一行」缺陷**。

read_text_with_fallback 与 atomic_write 是为后续修复新增的实现，
本轮只提供实现，不接入任何调用点。
"""

import os
import tempfile


def parse_entries(text):
    """把 hosts 文本解析为 [(ip, [域名...]), ...]，跳过空行与注释行。"""
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            entries.append((parts[0], parts[1:]))
    return entries


def find_ips_for_host(text, hostname):
    """返回 hosts 文本中指定域名对应的全部 IP。按域名字段精确比对。"""
    return [ip for ip, domains in parse_entries(text) if hostname in domains]


def remove_host_entries(text, hostname):
    """移除包含指定域名的行。

    注意：照搬 clean_hostname_entries 的整行子串匹配。
    这会连带删除 cdn.<hostname>、<hostname>.lan 以及提及该域名的注释行。
    这是已知缺陷，由子项目 2 修复。
    """
    lines = text.splitlines()
    new_lines = [line for line in lines if hostname not in line]
    return "\n".join(new_lines)


def add_host_entry(text, hostname, ip, marker):
    """追加一条带标记的 hosts 记录。搬运自 apply_ip。"""
    lines = text.splitlines()
    lines.append(f"\n{marker}")
    lines.append(f"{ip}\t{hostname}")
    return "\n".join(lines)


def strip_marked_block(text, marker):
    """移除标记行及其下一行。

    注意：照搬 check_and_clean_all_entries 的实现——遇到标记行即
    无条件丢弃紧随其后的一行，不校验该行是否真是本程序写入的记录。
    孤儿标记会导致用户自己的条目被误删。这是已知缺陷，由子项目 2 修复。
    """
    lines = text.splitlines()
    new_lines = []
    skip_next = False
    for line in lines:
        if skip_next:
            skip_next = False
            continue
        if marker in line:
            skip_next = True
            continue
        new_lines.append(line)
    return "\n".join(new_lines)


def read_text_with_fallback(path):
    """按 utf-8-sig → gbk → latin-1 顺序尝试读取文本文件。

    utf-8-sig 是 utf-8 解码侧的超集，只是多剥离开头的 BOM，因此不带 BOM 的
    常规 utf-8 文件同样能被正确读取。
    中文 Windows 上第三方工具常往 hosts 写入 GBK 编码的中文注释，
    硬编码 utf-8 会抛 UnicodeDecodeError（ValueError 子类，不被 except IOError 捕获）。

    本轮只提供实现，不接入 HostsManager 的任何读取点。
    """
    for encoding in ("utf-8-sig", "gbk", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    # latin-1 能解码任意字节序列，理论上不会走到这里
    raise UnicodeDecodeError("utf-8", b"", 0, 1, f"无法解码文件: {path}")


def atomic_write(path, text):
    """原子写入：先写同目录临时文件，再 os.replace 覆盖目标。

    避免「截断后写入中途崩溃」留下空文件或半截内容。

    本轮只提供实现，不接入 HostsManager 的任何写入点。
    """
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".hosts_tmp_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
