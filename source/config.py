import os
import base64

# 配置信息
app_data = {
    "APP_VERSION": "1.0.0",
    "APP_NAME": "FRAISEMOE Addons Installer NEXT",
    "TEMP": "TEMP",
    "CACHE": "FRAISEMOE",
    "PLUGIN": "PLUGIN",
    "CONFIG_URL": "aHR0cHM6Ly9hcmNoaXZlLm92b2Zpc2guY29tL2FwaS93aWRnZXQvbmVrb3BhcmEvZG93bmxvYWRfdXJsX2RlYnVnLmpzb24=",
    "UA": "TW96aWxsYS81LjAgKExpbnV4IGRlYmlhbjEyIEZyYWlzZU1vZTItQWNjZXB0LU5leHQpIEdlY2tvLzIwMTAwMTAxIEZpcmVmb3gvMTE0LjAgRnJhaXNlTW9lMi8xLjAuMA==",
    "game_info": {
        "NEKOPARA Vol.1": {
            "exe": "nekopara_vol1.exe",
            "hash": "04b48b231a7f34431431e5027fcc7b27affaa951b8169c541709156acf754f3e",
            "install_path": "NEKOPARA Vol. 1/adultsonly.xp3",
            "plugin_path": "vol.1/adultsonly.xp3",
        },
        "NEKOPARA Vol.2": {
            "exe": "nekopara_vol2.exe",
            "hash": "b9c00a2b113a1e768bf78400e4f9075ceb7b35349cdeca09be62eb014f0d4b42",
            "install_path": "NEKOPARA Vol. 2/adultsonly.xp3",
            "plugin_path": "vol.2/adultsonly.xp3",
        },
        "NEKOPARA Vol.3": {
            "exe": "NEKOPARAvol3.exe",
            "hash": "2ce7b223c84592e1ebc3b72079dee1e5e8d064ade15723328a64dee58833b9d5",
            "install_path": "NEKOPARA Vol. 3/update00.int",
            "plugin_path": "vol.3/update00.int",
        },
        "NEKOPARA Vol.4": {
            "exe": "nekopara_vol4.exe",
            "hash": "4a4a9ae5a75a18aacbe3ab0774d7f93f99c046afe3a777ee0363e8932b90f36a",
            "install_path": "NEKOPARA Vol. 4/vol4adult.xp3",
            "plugin_path": "vol.4/vol4adult.xp3",
        },
        "NEKOPARA After": {
            "exe": "nekopara_after.exe",
            "hash": "eb26ff6850096a240af8340ba21c5c3232e90f29fb8191e24b6ce701acae0aa9",
            "install_path": "NEKOPARA After/afteradult.xp3",
            "plugin_path": "after/afteradult.xp3",
            "sig_path": "after/afteradult.xp3.sig"
        },
    },
}

# Base64解码
def decode_base64(encoded_str):
    return base64.b64decode(encoded_str).decode("utf-8")

# 全局变量
APP_VERSION = app_data["APP_VERSION"]
APP_NAME = app_data["APP_NAME"]
TEMP = os.getenv(app_data["TEMP"]) or app_data["TEMP"]
CACHE = os.path.join(TEMP, app_data["CACHE"])
PLUGIN = os.path.join(CACHE, app_data["PLUGIN"])
CONFIG_URL = decode_base64(app_data["CONFIG_URL"])
UA = decode_base64(app_data["UA"])
GAME_INFO = app_data["game_info"]
BLOCK_SIZE = 67108864
HASH_SIZE = 134217728
PLUGIN_HASH = {game: info["hash"] for game, info in GAME_INFO.items()}
PROCESS_INFO = {info["exe"]: game for game, info in GAME_INFO.items()}