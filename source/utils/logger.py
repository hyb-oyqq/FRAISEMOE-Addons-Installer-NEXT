from .helpers import censor_url
import logging
import os
from data.config import CACHE

class URLCensorFormatter(logging.Formatter):
    """自定义的日志格式化器，用于隐藏日志消息中的URL"""
    
    def format(self, record):
        # 先使用原始的format方法格式化日志
        formatted_message = super().format(record)
        # 然后对格式化后的消息进行URL审查
        return censor_url(formatted_message)

class Logger:
    def __init__(self, filename, stream):
        self.terminal = stream
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        censored_message = censor_url(message)
        self.terminal.write(censored_message)
        self.log.write(censored_message)
        self.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()

def setup_logger(name):
    """设置并返回一个命名的logger
    
    Args:
        name: logger的名称
        
    Returns:
        logging.Logger: 配置好的logger对象
    """
    # 创建logger
    logger = logging.getLogger(name)
    
    # 避免重复添加处理器
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(logging.DEBUG)
    
    # 确保日志目录存在
    log_dir = os.path.join(CACHE, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{name}.log")
    
    # 创建文件处理器
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式器并添加到处理器
    formatter = URLCensorFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger 