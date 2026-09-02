"""配置与 URL 校验。

`validate_cloud_config` 由 workers/config_fetch_thread.py 搬运而来，
现有缺陷（仅检查顶层键存在性、不校验值类型）一并照搬。

`coerce_config` 与 `validate_download_url` 是为后续修复新增的实现，
本轮只提供实现，不接入任何调用点。
"""

from urllib.parse import urlparse

# 与 workers/config_fetch_thread.py 中的常量保持一致
UPDATE_REQUIRED_MSG = "\u8bf7\u4f7f\u7528\u6700\u65b0\u7248\u672c\u7684FraiseMoe2-Next\u8fdb\u884c\u4e0b\u8f7d"

REQUIRED_KEYS = [f"vol.{i + 1}.data" for i in range(4)] + ["after.data"]


def validate_cloud_config(data):
    """校验云端配置。

    Returns:
        tuple[dict | None, str]: (配置, 错误信息)。成功时错误信息为 ""。

    注意：照搬自 config_fetch_thread.py:44-60，仅检查顶层键是否存在。
    值为 null 或非对象时不会被发现——这是已知缺陷，由子项目 2 修复。
    """
    if isinstance(data, str) and data == UPDATE_REQUIRED_MSG:
        return None, "update_required"
    if isinstance(data, dict) and data.get("message") == UPDATE_REQUIRED_MSG:
        return None, "update_required"

    missing_keys = [key for key in REQUIRED_KEYS if key not in data]
    if missing_keys:
        return None, f"missing_keys:{','.join(missing_keys)}"

    return data, ""


def coerce_config(data):
    """把任意 JSON 反序列化结果收敛为 dict。

    本轮只提供实现，不接入 utils/helpers.py:232 与 Main.py:49。
    """
    if isinstance(data, dict):
        return data
    return {}


def validate_download_url(url):
    """校验下载 URL，合法则原样返回，否则抛 ValueError。

    scheme 白名单按定义排除 "-" 开头的字符串，从而堵住把云端可控值
    作为裸位置参数交给 aria2c 所导致的选项注入。

    本轮只提供实现，不接入 workers/download.py:216。
    """
    if not isinstance(url, str) or not url:
        raise ValueError(f"下载 URL 必须是非空字符串，实际为: {type(url).__name__}")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"下载 URL 的协议必须是 http 或 https，实际为: {parsed.scheme!r}")
    if not parsed.netloc:
        raise ValueError(f"下载 URL 缺少主机名: {url!r}")

    return url
