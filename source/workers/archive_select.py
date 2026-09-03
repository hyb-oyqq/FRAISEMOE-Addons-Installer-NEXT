"""从压缩包成员列表中挑选待安装文件。

select_members 搬运自 workers/extraction_thread.py:130-181。

**照搬三处已知缺陷**：
1. 非 After 版本的 sig 字段恒为 None，而调用方对任意 .sig 都会命中；
2. 主补丁的宽松回退用 `target_filename in file_path` 子串匹配，
   readme_adultsonly.xp3.txt 之类会被选中；
3. After 分支的 .sig 匹配没有 break，取到的是列表中最后一个 .sig。

三者均由子项目 2 修复。

reject_unsafe_members 是为后续修复新增的实现，本轮只提供实现，不接入调用点。
"""

import os
from dataclasses import dataclass


@dataclass
class MemberSelection:
    """一次压缩包成员挑选的结果。"""

    main: str = None
    sig: str = None
    needs_fallback: bool = False


def select_members(file_list, target_filename, game_version):
    """从成员列表中挑出主补丁与签名文件。

    注意：照搬 extraction_thread.py:130-181 的全部匹配逻辑与缺陷。
    """
    target_file_in_archive = None
    sig_file_in_archive = None

    if game_version == "NEKOPARA After":
        sig_filename = target_filename + ".sig"
        for file_path in file_list:
            basename = os.path.basename(file_path)
            if basename == "afteradult.xp3" and not basename.endswith(".sig"):
                target_file_in_archive = file_path
            elif basename == "afteradult.xp3.sig" or basename.endswith(".sig"):
                # 照搬：此处没有 break，取到的是最后一个 .sig
                sig_file_in_archive = file_path

        if not target_file_in_archive:
            for file_path in file_list:
                if "afteradult.xp3" in file_path and not file_path.endswith(".sig"):
                    target_file_in_archive = file_path
                    break
    else:
        # 照搬：非 After 版本 sig_filename 为 None
        sig_filename = None
        for file_path in file_list:
            basename = os.path.basename(file_path)
            if basename == target_filename and not basename.endswith(".sig"):
                target_file_in_archive = file_path
            elif basename == sig_filename:
                sig_file_in_archive = file_path

        if not target_file_in_archive:
            # 照搬：子串匹配的宽松回退
            for file_path in file_list:
                if target_filename in file_path and not file_path.endswith(".sig"):
                    target_file_in_archive = file_path
                    break

    return MemberSelection(
        main=target_file_in_archive,
        sig=sig_file_in_archive,
        needs_fallback=target_file_in_archive is None,
    )


def reject_unsafe_members(file_list, dest_dir):
    """返回会写出 dest_dir 之外的成员名列表。空列表表示全部安全。

    拒绝：绝对路径、盘符、UNC 路径、以分隔符开头、以及归一化后逃出 dest_dir 的路径。

    本轮只提供实现，不接入 extraction_thread.py 的解压调用点。
    """
    rejected = []
    dest_real = os.path.realpath(dest_dir)

    for member in file_list:
        normalized = member.replace("\\", "/")

        if os.path.isabs(member) or normalized.startswith("/"):
            rejected.append(member)
            continue
        if len(member) >= 2 and member[1] == ":":
            rejected.append(member)
            continue
        if normalized.startswith("//"):
            rejected.append(member)
            continue

        target = os.path.realpath(os.path.join(dest_real, member))
        if os.path.commonpath([dest_real, target]) != dest_real:
            rejected.append(member)

    return rejected
