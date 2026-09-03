"""安装后校验判定。

已接入两处 fail-open 判定点：
- core/handlers/extraction_handler.py:146-151
- core/managers/offline_mode_manager.py:553-566

workers/hash_thread.py:127-130 未接入：其 "after" 分支把哈希计算与判定
耦合在同一循环里，用可变 result dict 记录状态并以 break 提前退出，接入
前需先拆成"扫描哈希 → 统一判定"两阶段，属真实重构而非机械搬运，交由
子项目 2 处理。

**照搬已知缺陷：install_paths 为空时返回 PASSED**（现状即「直接认为安装成功」）。
SKIPPED_NO_PATHS 本轮定义但不返回，供子项目 2 翻转时启用。
"""

from enum import Enum


class Verdict(Enum):
    """安装后校验的判定结果。"""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED_NO_PATHS = "skipped_no_paths"


def decide_post_install(install_paths, hash_results, expected):
    """根据哈希结果判定安装是否成功。

    Args:
        install_paths: {游戏版本: 安装路径}
        hash_results: {安装路径: 实际哈希或 None}
        expected: {游戏版本: 预期哈希}

    Returns:
        tuple[Verdict, str]: (判定, 面向用户的消息)。PASSED 时消息为 ""。

    注意：照搬现有缺陷——install_paths 为空时返回 PASSED 而非 SKIPPED_NO_PATHS。
    这是「找不到安装路径就直接认为安装成功」的 fail-open 行为，由子项目 2 修复。
    """
    if not install_paths:
        return Verdict.PASSED, ""

    for game_version, install_path in install_paths.items():
        expected_hash = expected.get(game_version)
        if not expected_hash:
            continue

        if install_path not in hash_results:
            # 照搬 hash_thread.py:127-130——目标文件不存在时直接跳过，
            # passed 保持 True。这是 fail-open 缺陷，由子项目 2 修复。
            # 注意与下面 actual is None 的区别：那是「文件在但哈希算不出来」，
            # 现状下会正确判 FAILED，不属于本轮要照搬的缺陷。
            continue

        actual = hash_results[install_path]
        if actual is None:
            return (
                Verdict.FAILED,
                f"\n无法计算 {game_version} 的文件哈希值，文件可能已损坏或被占用。\n",
            )
        if actual != expected_hash:
            return (
                Verdict.FAILED,
                f"\n检测到 {game_version} 的文件哈希值不匹配。\n",
            )

    return Verdict.PASSED, ""
