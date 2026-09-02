import os

import pytest

from utils.hosts_text import (
    add_host_entry,
    atomic_write,
    find_ips_for_host,
    parse_entries,
    read_text_with_fallback,
    remove_host_entries,
    strip_marked_block,
)

MARKER = "# Added by FRAISEMOE Addons Installer NEXT"

SAMPLE = """\
# Copyright (c) 1993-2009 Microsoft Corp.
127.0.0.1       localhost
::1             localhost

104.16.0.1      example.com
104.16.0.2      cdn.example.com  alias.example.com
"""


def test_parse_entries_skips_comments_and_blanks():
    entries = parse_entries(SAMPLE)
    assert ("127.0.0.1", ["localhost"]) in entries
    assert ("104.16.0.2", ["cdn.example.com", "alias.example.com"]) in entries
    assert all(not ip.startswith("#") for ip, _ in entries)
    assert len(entries) == 4


def test_find_ips_for_host_matches_exact_domain_field():
    assert find_ips_for_host(SAMPLE, "example.com") == ["104.16.0.1"]
    assert find_ips_for_host(SAMPLE, "alias.example.com") == ["104.16.0.2"]
    assert find_ips_for_host(SAMPLE, "nope.example.com") == []


def test_add_host_entry_appends_marker_and_record():
    result = add_host_entry(SAMPLE, "example.com", "1.2.3.4", MARKER)
    assert MARKER in result
    assert "1.2.3.4\texample.com" in result
    # 原有内容不应丢失
    assert "127.0.0.1       localhost" in result


def test_strip_marked_block_removes_marker_and_its_record():
    text = add_host_entry(SAMPLE, "example.com", "1.2.3.4", MARKER)
    result = strip_marked_block(text, MARKER)
    assert MARKER not in result
    assert "1.2.3.4\texample.com" not in result


def test_read_text_with_fallback_reads_utf8(tmp_path):
    p = tmp_path / "hosts"
    p.write_bytes("127.0.0.1 本机\n".encode("utf-8"))
    assert "本机" in read_text_with_fallback(str(p))


def test_read_text_with_fallback_reads_gbk(tmp_path):
    p = tmp_path / "hosts"
    p.write_bytes("127.0.0.1 本机\n".encode("gbk"))
    assert "本机" in read_text_with_fallback(str(p))


def test_read_text_with_fallback_reads_utf8_bom(tmp_path):
    p = tmp_path / "hosts"
    p.write_bytes("\ufeff127.0.0.1 localhost\n".encode("utf-8"))
    assert "localhost" in read_text_with_fallback(str(p))


def test_atomic_write_writes_content(tmp_path):
    p = tmp_path / "hosts"
    atomic_write(str(p), "127.0.0.1 localhost\n")
    assert p.read_text(encoding="utf-8") == "127.0.0.1 localhost\n"


def test_atomic_write_leaves_no_temp_file_behind(tmp_path):
    p = tmp_path / "hosts"
    atomic_write(str(p), "content\n")
    assert [f.name for f in tmp_path.iterdir()] == ["hosts"]


from config.config import APP_NAME
from utils.helpers import HostsManager

APP_MARKER = f"# Added by {APP_NAME}"

WITH_SUBDOMAIN = """\
127.0.0.1       localhost
1.1.1.1         cdn.example.com
2.2.2.2         example.com
"""

WITH_COMMENT = """\
127.0.0.1       localhost
# 屏蔽 example.com 用
2.2.2.2         other.org
"""


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：remove_host_entries 用整行子串匹配，会误删 cdn.<域名>。子项目 2 修复",
)
def test_remove_host_entries_keeps_subdomain():
    result = remove_host_entries(WITH_SUBDOMAIN, "example.com")
    assert "cdn.example.com" in result
    assert "2.2.2.2         example.com" not in result


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：remove_host_entries 会删除仅提及该域名的注释行。子项目 2 修复",
)
def test_remove_host_entries_keeps_comments():
    result = remove_host_entries(WITH_COMMENT, "example.com")
    assert "# 屏蔽 example.com 用" in result


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：strip_marked_block 无条件丢弃标记行的下一行。子项目 2 修复",
)
def test_strip_marked_block_keeps_orphan_neighbor():
    # 孤儿标记：标记行存在，但其后并非本程序写入的记录
    text = f"127.0.0.1 localhost\n{APP_MARKER}\n9.9.9.9 user-own-entry.com\n"
    result = strip_marked_block(text, APP_MARKER)
    assert "9.9.9.9 user-own-entry.com" in result


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：apply_ip 覆盖 original_content，restore 写回的是已修改内容。子项目 2 修复",
)
def test_hosts_manager_restore_recovers_original(tmp_path, monkeypatch):
    hosts = tmp_path / "hosts"
    original = "127.0.0.1 localhost\n5.5.5.5 example.com\n"
    hosts.write_text(original, encoding="utf-8")

    manager = HostsManager(
        hosts_path=str(hosts), backup_path=str(tmp_path / "hosts.bak")
    )
    # 绕过管理员权限检查与自动还原开关，只验证内容语义
    monkeypatch.setattr(manager, "is_auto_restore_disabled", lambda: False)
    monkeypatch.setattr("utils.helpers.AdminPrivileges.is_admin", lambda self: True)

    manager.backup()
    manager.apply_ip("example.com", "1.2.3.4")
    manager.restore()

    assert "5.5.5.5 example.com" in hosts.read_text(encoding="utf-8")


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：hosts 读写硬编码 utf-8 且只捕获 IOError，GBK 内容抛 UnicodeDecodeError 穿透。子项目 2 修复",
)
def test_hosts_manager_backup_reads_gbk_file(tmp_path, monkeypatch):
    hosts = tmp_path / "hosts"
    hosts.write_bytes("127.0.0.1 localhost\n# 加速器写入的中文注释\n".encode("gbk"))

    manager = HostsManager(
        hosts_path=str(hosts), backup_path=str(tmp_path / "hosts.bak")
    )
    monkeypatch.setattr("utils.helpers.AdminPrivileges.is_admin", lambda self: True)

    assert manager.backup() is True
