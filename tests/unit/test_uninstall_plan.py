import os

import pytest

from core.uninstall_plan import (
    UninstallPlan,
    derive_patch_file_candidates,
    derive_uninstall_plan,
)

GAME_INFO = {
    "NEKOPARA Vol.1": {
        "exe": "nekopara_vol1.exe",
        "install_path": "NEKOPARA Vol. 1/adultsonly.xp3",
        "plugin_path": "vol.1/adultsonly.xp3",
    },
    "NEKOPARA After": {
        "exe": "nekopara_after.exe",
        "install_path": "NEKOPARA After/afteradult.xp3",
        "plugin_path": "after/afteradult.xp3",
        "sig_path": "after/afteradult.xp3.sig",
    },
}


def test_candidates_include_base_and_case_variants():
    candidates = derive_patch_file_candidates(r"D:\Games\Vol1", "adultsonly.xp3")
    base = os.path.join(r"D:\Games\Vol1", "adultsonly.xp3")
    assert base in candidates
    assert base.lower() in candidates
    assert base.upper() in candidates


def test_plan_includes_patch_file_and_fain_variant():
    plan = derive_uninstall_plan(r"D:\Games\Vol1", GAME_INFO, "NEKOPARA Vol.1")
    base = os.path.join(r"D:\Games\Vol1", "adultsonly.xp3")
    assert base in plan.files
    assert f"{base}.fain" in plan.files


def test_plan_includes_sig_only_for_after():
    after = derive_uninstall_plan(r"D:\Games\After", GAME_INFO, "NEKOPARA After")
    base = os.path.join(r"D:\Games\After", "afteradult.xp3")
    assert f"{base}.sig" in after.files
    assert f"{base}.fain.sig" in after.files

    vol1 = derive_uninstall_plan(r"D:\Games\Vol1", GAME_INFO, "NEKOPARA Vol.1")
    assert not any(p.endswith(".sig") for p in vol1.files)


def test_plan_returns_dataclass_with_reasons():
    plan = derive_uninstall_plan(r"D:\Games\Vol1", GAME_INFO, "NEKOPARA Vol.1")
    assert isinstance(plan, UninstallPlan)
    assert all(p in plan.reasons for p in plan.files)


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：卸载会删除本程序从未写入的 game/config.json 与 scripts.json。子项目 2 修复",
)
def test_uninstall_plan_excludes_game_config():
    plan = derive_uninstall_plan(r"D:\Games\Vol1", GAME_INFO, "NEKOPARA Vol.1")
    assert not any(p.endswith(("config.json", "Config.json", "CONFIG.JSON")) for p in plan.files)
    assert not any(p.endswith(("scripts.json", "Scripts.json", "SCRIPTS.JSON")) for p in plan.files)


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：卸载会 rmtree 整个 patch/ 与 game/patch/ 目录。子项目 2 修复",
)
def test_uninstall_plan_excludes_patch_dir():
    plan = derive_uninstall_plan(r"D:\Games\Vol1", GAME_INFO, "NEKOPARA Vol.1")
    assert plan.dirs == []


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：路径变体作用于完整路径，可生成 game_dir 之外的路径。子项目 2 修复",
)
def test_candidates_stay_within_game_dir():
    game_dir = r"D:\game_lib\Vol1"
    candidates = derive_patch_file_candidates(game_dir, "adultsonly.xp3")
    for path in candidates:
        assert os.path.commonpath([game_dir, path]) == game_dir
