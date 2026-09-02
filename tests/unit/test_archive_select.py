# tests/unit/test_archive_select.py
import pytest

from workers.archive_select import MemberSelection, reject_unsafe_members, select_members


def test_select_members_exact_match_for_vol1():
    result = select_members(["vol.1/adultsonly.xp3"], "adultsonly.xp3", "NEKOPARA Vol.1")
    assert isinstance(result, MemberSelection)
    assert result.main == "vol.1/adultsonly.xp3"
    assert result.needs_fallback is False


def test_select_members_after_picks_main_and_sig():
    files = ["after/afteradult.xp3", "after/afteradult.xp3.sig"]
    result = select_members(files, "afteradult.xp3", "NEKOPARA After")
    assert result.main == "after/afteradult.xp3"
    assert result.sig == "after/afteradult.xp3.sig"


def test_select_members_flags_fallback_when_nothing_matches():
    result = select_members(["readme.txt"], "adultsonly.xp3", "NEKOPARA Vol.1")
    assert result.main is None
    assert result.needs_fallback is True


@pytest.mark.parametrize(
    "member",
    ["../evil.xp3", "a/../../evil.xp3", "C:/Windows/evil.xp3", "/etc/passwd", "\\\\server\\share\\x"],
)
def test_reject_unsafe_members_rejects_traversal(member):
    assert reject_unsafe_members([member], r"D:\temp\extract") == [member]


def test_reject_unsafe_members_allows_normal_relative_paths():
    safe = ["vol.1/adultsonly.xp3", "after/afteradult.xp3.sig", "readme.txt"]
    assert reject_unsafe_members(safe, r"D:\temp\extract") == []


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：After 分支 .sig 匹配无 break，取到列表中最后一个 .sig 而非精确匹配项。子项目 2 修复",
)
def test_select_members_after_picks_exact_sig_not_last():
    files = [
        "after/afteradult.xp3",
        "after/afteradult.xp3.sig",
        "after/unrelated.sig",
    ]
    result = select_members(files, "afteradult.xp3", "NEKOPARA After")
    assert result.sig == "after/afteradult.xp3.sig"


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：宽松回退用子串匹配，readme_<目标名>.txt 会被选为主补丁。子项目 2 修复",
)
def test_select_members_exact_basename():
    files = ["vol.1/readme_adultsonly.xp3.txt"]
    result = select_members(files, "adultsonly.xp3", "NEKOPARA Vol.1")
    assert result.main is None
