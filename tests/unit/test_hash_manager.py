# tests/unit/test_hash_manager.py
import hashlib

from utils.helpers import HashManager


def test_hash_calculate_matches_hashlib(tmp_path):
    content = b"nekopara patch payload" * 1000
    f = tmp_path / "payload.bin"
    f.write_bytes(content)

    manager = HashManager(1024)
    assert manager.hash_calculate(str(f)) == hashlib.sha256(content).hexdigest()


def test_hash_calculate_handles_empty_file(tmp_path):
    f = tmp_path / "empty.bin"
    f.write_bytes(b"")

    manager = HashManager(1024)
    assert manager.hash_calculate(str(f)) == hashlib.sha256(b"").hexdigest()


def test_calculate_hashes_in_parallel_returns_none_for_missing_file(tmp_path):
    good = tmp_path / "good.bin"
    good.write_bytes(b"abc")
    missing = tmp_path / "missing.bin"

    manager = HashManager(1024)
    results = manager.calculate_hashes_in_parallel([str(good), str(missing)])

    assert results[str(good)] == hashlib.sha256(b"abc").hexdigest()
    assert results[str(missing)] is None
