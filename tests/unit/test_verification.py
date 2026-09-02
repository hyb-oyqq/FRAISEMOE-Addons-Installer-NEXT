import pytest

from core.verification import Verdict, decide_post_install

EXPECTED = {"NEKOPARA Vol.1": "aabb"}


def test_all_hashes_match_returns_passed():
    verdict, message = decide_post_install(
        {"NEKOPARA Vol.1": "D:/g/adultsonly.xp3"},
        {"D:/g/adultsonly.xp3": "aabb"},
        EXPECTED,
    )
    assert verdict is Verdict.PASSED
    assert message == ""


def test_hash_mismatch_returns_failed():
    verdict, message = decide_post_install(
        {"NEKOPARA Vol.1": "D:/g/adultsonly.xp3"},
        {"D:/g/adultsonly.xp3": "ffff"},
        EXPECTED,
    )
    assert verdict is Verdict.FAILED
    assert "NEKOPARA Vol.1" in message


def test_hash_calculation_failure_returns_failed():
    verdict, message = decide_post_install(
        {"NEKOPARA Vol.1": "D:/g/adultsonly.xp3"},
        {"D:/g/adultsonly.xp3": None},
        EXPECTED,
    )
    assert verdict is Verdict.FAILED


def test_skipped_no_paths_enum_member_exists():
    # 子项目 2 会启用该值；本轮仅确认它已定义
    assert Verdict.SKIPPED_NO_PATHS.name == "SKIPPED_NO_PATHS"


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：install_paths 为空时判为 PASSED（源码注释：直接认为安装成功）。子项目 2 修复",
)
def test_decide_post_install_empty_paths_fails():
    verdict, message = decide_post_install({}, {}, EXPECTED)
    assert verdict is Verdict.SKIPPED_NO_PATHS
    assert message != ""


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：目标文件不存在时 hash_thread 只 continue，passed 保持 True。子项目 2 修复",
)
def test_decide_post_install_missing_file_fails():
    # 安装路径存在于映射中，但哈希结果里没有它——对应文件不存在的情形
    verdict, message = decide_post_install(
        {"NEKOPARA Vol.1": "D:/g/adultsonly.xp3"},
        {},
        EXPECTED,
    )
    assert verdict is Verdict.FAILED
