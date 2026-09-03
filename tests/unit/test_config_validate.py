# tests/unit/test_config_validate.py
import pytest

from config.validate import coerce_config, validate_download_url, validate_cloud_config

UPDATE_MSG = "\u8bf7\u4f7f\u7528\u6700\u65b0\u7248\u672c\u7684FraiseMoe2-Next\u8fdb\u884c\u4e0b\u8f7d"


def _full_config():
    return {
        "vol.1.data": {"url": "https://example.com/a.7z"},
        "vol.2.data": {"url": "https://example.com/b.7z"},
        "vol.3.data": {"url": "https://example.com/c.7z"},
        "vol.4.data": {"url": "https://example.com/d.7z"},
        "after.data": {"url": "https://example.com/e.7z"},
    }


def test_validate_cloud_config_accepts_full_config():
    config, error = validate_cloud_config(_full_config())
    assert error == ""
    assert config == _full_config()


def test_validate_cloud_config_reports_missing_keys():
    data = _full_config()
    del data["vol.3.data"]
    config, error = validate_cloud_config(data)
    assert config is None
    assert error == "missing_keys:vol.3.data"


def test_validate_cloud_config_detects_update_required_string():
    config, error = validate_cloud_config(UPDATE_MSG)
    assert config is None
    assert error == "update_required"


def test_validate_cloud_config_detects_update_required_message_field():
    config, error = validate_cloud_config({"message": UPDATE_MSG})
    assert config is None
    assert error == "update_required"


@pytest.mark.parametrize("value", [[], "abc", 123, None, 1.5, True])
def test_coerce_config_returns_empty_dict_for_non_dict(value):
    assert coerce_config(value) == {}


def test_coerce_config_passes_dict_through():
    data = {"debug_mode": True}
    assert coerce_config(data) is data


@pytest.mark.parametrize(
    "url",
    ["http://example.com/a.7z", "https://example.com/a.7z", "https://a.b.c/d?e=f"],
)
def test_validate_download_url_accepts_http_and_https(url):
    assert validate_download_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "--conf-path=\\\\attacker\\share\\a.conf",
        "-x",
        "file:///C:/Windows/System32/config/SAM",
        "ftp://example.com/a.7z",
        "example.com/a.7z",
        "",
        None,
        123,
    ],
)
def test_validate_download_url_rejects_everything_else(url):
    with pytest.raises(ValueError):
        validate_download_url(url)


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：仅检查顶层键，值为 null/数字时 `key not in data` 抛 TypeError。子项目 2 修复",
)
@pytest.mark.parametrize("value", [None, 123])
def test_validate_cloud_config_rejects_non_dict(value):
    config, error = validate_cloud_config(value)
    assert config is None
    assert error != ""


@pytest.mark.xfail(
    strict=True,
    reason="审查发现：load_config 直接返回 json.load 结果，非 dict 时 Main.py:49 崩在 QApplication 之前。子项目 2 修复",
)
def test_load_config_returns_dict_for_list_json(tmp_path, monkeypatch):
    """走注入到达现有调用路径：把 CONFIG_FILE 指向内容为 [] 的临时文件。

    这一条不测 coerce_config（它是新写的、已正确），而是测尚未接入它的
    utils.helpers.load_config——缺陷仍在，故为红。
    """
    cfg = tmp_path / "config.json"
    cfg.write_text("[]", encoding="utf-8")
    monkeypatch.setattr("utils.helpers.CONFIG_FILE", str(cfg))

    from utils.helpers import load_config

    assert load_config() == {}
