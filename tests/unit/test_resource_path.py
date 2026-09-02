# tests/unit/test_resource_path.py
import os

from utils.helpers import resource_path


def test_resource_path_maps_executables_to_bin():
    result = resource_path("aria2c-fast_x64.exe")
    assert os.path.basename(os.path.dirname(result)) == "bin"
    assert result.endswith("aria2c-fast_x64.exe")


def test_resource_path_maps_data_files_to_data():
    result = resource_path("ip.txt")
    assert os.path.basename(os.path.dirname(result)) == "data"


def test_resource_path_returns_absolute_path():
    assert os.path.isabs(resource_path("aria2c-fast_x64.exe"))
