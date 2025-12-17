import os
import base64
import datetime

# 配置信息
app_data = {
    "APP_VERSION": "1.4.2",
    "APP_NAME": "FRAISEMOE Addons Installer NEXT",
    "TEMP": "TEMP",
    "CACHE": "FRAISEMOE",
    "PLUGIN": "PLUGIN",
    "CONFIG_URL": "aHR0cHM6Ly9uZWtvcGFyYS1hcGkub3ZvZmlzaC5jb20vYXBpL291eWFuZ3FpcWkvbmVrb3BhcmEvZG93bmxvYWRfdXJsLmpzb24=",
    "UA_TEMPLATE": "Mozilla/5.0 (Linux debian12 FraiseMoe2-Accept-Next) Gecko/20100101 Firefox/114.0 FraiseMoe2/{}",
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

def decode_base64(b64str):
    """解码base64字符串"""
    try:
        return base64.b64decode(b64str).decode('utf-8')
    except:
        return b64str
        
# 确保缓存目录存在
def ensure_cache_dirs():
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(PLUGIN, exist_ok=True)

# 全局变量
APP_NAME = app_data["APP_NAME"]
APP_VERSION = app_data["APP_VERSION"]  # 从app_data中获取，不再重复定义
TEMP = os.getenv(app_data["TEMP"]) or app_data["TEMP"]
CACHE = os.path.join(TEMP, app_data["CACHE"])
CONFIG_FILE = os.path.join(CACHE, "config.json")

# 日志配置
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "log")
LOG_LEVEL = "DEBUG"  # 可选值: DEBUG, INFO, WARNING, ERROR, CRITICAL

# 日志文件大小和轮转配置（新增）
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 3  # 保留3个备份文件
LOG_RETENTION_DAYS = 7  # 日志保留7天

# 将log文件放在程序根目录下的log文件夹中，使用日期+时间戳格式命名
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
log_dir = os.path.join(root_dir, "log")
os.makedirs(log_dir, exist_ok=True)
current_datetime = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
LOG_FILE = os.path.join(log_dir, f"log-{current_datetime}.txt")

PLUGIN = os.path.join(CACHE, app_data["PLUGIN"])
CONFIG_URL = decode_base64(app_data["CONFIG_URL"])
UA = app_data["UA_TEMPLATE"].format(APP_VERSION)

# 哈希计算块大小
BLOCK_SIZE = 67108864
HASH_SIZE = 134217728

# 资源哈希值
GAME_INFO = app_data["game_info"]
PLUGIN_HASH = {
    "NEKOPARA Vol.1": GAME_INFO["NEKOPARA Vol.1"]["hash"],
    "NEKOPARA Vol.2": GAME_INFO["NEKOPARA Vol.2"]["hash"],
    "NEKOPARA Vol.3": GAME_INFO["NEKOPARA Vol.3"]["hash"],
    "NEKOPARA Vol.4": GAME_INFO["NEKOPARA Vol.4"]["hash"],
    "NEKOPARA After": GAME_INFO["NEKOPARA After"]["hash"]
}
PROCESS_INFO = {info["exe"]: game for game, info in GAME_INFO.items()}

# 下载线程档位设置
DOWNLOAD_THREADS = {
    "low": 1,      # 低速
    "medium": 8,   # 中速（默认）
    "high": 16,    # 高速
    "extreme": 32, # 极速
    "insane": 64   # 狂暴
}

# 默认下载线程档位
DEFAULT_DOWNLOAD_THREAD_LEVEL = "high"