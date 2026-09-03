"""卸载计划推导。

搬运自 core/managers/patch_manager.py 的 uninstall_patch(:108-271)。

**照搬两处已知缺陷**：
1. derive_patch_file_candidates 对完整路径（而非文件名）做大小写与下划线变形，
   游戏装在 D:\\game_lib\\ 时会生成指向 D:\\gamelib\\ 的路径。
2. derive_uninstall_plan 包含 patch/、game/patch/、game/config.json、
   game/scripts.json——这些从来不是本程序写入的。

二者均由子项目 2 修复。
"""

import os
from dataclasses import dataclass, field


@dataclass
class UninstallPlan:
    """一次卸载操作的待删清单。"""

    files: list = field(default_factory=list)
    dirs: list = field(default_factory=list)
    reasons: dict = field(default_factory=dict)


def derive_patch_file_candidates(game_dir, install_path_base):
    """推导补丁文件的候选路径。

    注意：照搬 patch_manager.py:119-125，变形作用于**完整路径**而非文件名。
    这是已知缺陷，由子项目 2 修复。
    """
    patch_file_path = os.path.join(game_dir, install_path_base)
    return [
        patch_file_path,
        patch_file_path.lower(),
        patch_file_path.upper(),
        patch_file_path.replace("_", ""),
        patch_file_path.replace("_", "-"),
    ]


def derive_uninstall_plan(game_dir, game_info, game_version):
    """推导一次卸载要删除的全部文件与目录。

    注意：照搬 patch_manager.py:194-271 的全部删除范围，
    包括本程序从未写入过的 patch/ 目录与 game/config.json。
    这是已知缺陷，由子项目 2 修复。
    """
    plan = UninstallPlan()

    def add_file(path, reason):
        if path not in plan.files:
            plan.files.append(path)
            plan.reasons[path] = reason

    def add_dir(path, reason):
        if path not in plan.dirs:
            plan.dirs.append(path)
            plan.reasons[path] = reason

    install_path_base = os.path.basename(game_info[game_version]["install_path"])
    candidates = derive_patch_file_candidates(game_dir, install_path_base)

    for patch_path in candidates:
        add_file(patch_path, "补丁文件")
        add_file(f"{patch_path}.fain", "被禁用的补丁文件")

    if game_version == "NEKOPARA After":
        for patch_path in candidates:
            add_file(f"{patch_path}.sig", "签名文件")
            add_file(f"{patch_path}.fain.sig", "被禁用补丁的签名文件")

    for name in ("patch", "Patch", "PATCH"):
        add_dir(os.path.join(game_dir, name), "补丁文件夹")

    game_folders = ("game", "Game", "GAME")
    patch_folders = ("patch", "Patch", "PATCH")
    for game_folder in game_folders:
        for patch_folder in patch_folders:
            add_dir(os.path.join(game_dir, game_folder, patch_folder), "game/patch 文件夹")

    for game_folder in game_folders:
        game_path = os.path.join(game_dir, game_folder)
        for config_file in ("config.json", "Config.json", "CONFIG.JSON"):
            add_file(os.path.join(game_path, config_file), "配置文件")
        for script_file in ("scripts.json", "Scripts.json", "SCRIPTS.JSON"):
            add_file(os.path.join(game_path, script_file), "脚本文件")

    return plan
