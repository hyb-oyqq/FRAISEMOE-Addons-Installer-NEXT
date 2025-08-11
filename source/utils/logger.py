from .url_censor import censor_url
import logging
import os
from config.config import CACHE

class URLCensorFormatter(logging.Formatter):
    """自定义的日志格式化器，用于隐藏日志消息中的URL"""
    
    def format(self, record):
        # 先使用原始的format方法格式化日志
        formatted_message = super().format(record)
        # 临时禁用URL隐藏，直接返回原始消息
        return formatted_message
        # 然后对格式化后的消息进行URL审查（已禁用）
        # return censor_url(formatted_message)

class Logger:
    def __init__(self, filename, stream):
        self.terminal = stream
        try:
            # 确保目录存在
            log_dir = os.path.dirname(filename)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                print(f"已创建日志目录: {log_dir}")
                
            # 以追加模式打开，避免覆盖现有内容
            self.log = open(filename, "a", encoding="utf-8", errors="replace")
            self.log.write("\n\n--- New logging session started ---\n\n")
        except (IOError, OSError) as e:
            # 如果打开文件失败，记录错误并使用空的写入操作
            print(f"Error opening log file {filename}: {e}")
            self.log = None

    def write(self, message):
        try:
            # 临时禁用URL隐藏
            # censored_message = censor_url(message)
            censored_message = message  # 直接使用原始消息
            self.terminal.write(censored_message)
            if self.log:
                self.log.write(censored_message)
                self.flush()
        except Exception as e:
            # 发生错误时记录到控制台
            self.terminal.write(f"Error writing to log: {e}\n")

    def flush(self):
        try:
            self.terminal.flush()
            if self.log:
                self.log.flush()
        except Exception:
            pass

    def close(self):
        try:
            if self.log:
                self.log.write("\n--- Logging session ended ---\n")
                self.log.close()
                self.log = None
        except Exception:
            pass

def setup_logger(name):
    """设置并返回一个命名的logger
    
    Args:
        name: logger的名称
        
    Returns:
        logging.Logger: 配置好的logger对象
    """
    # 导入LOG_FILE
    from config.config import LOG_FILE
    
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
    
    # 创建文件处理器 - 模块日志
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    
    # 创建主日志文件处理器 - 所有日志合并到主LOG_FILE
    try:
        # 确保主日志文件目录存在
        log_file_dir = os.path.dirname(LOG_FILE)
        if log_file_dir and not os.path.exists(log_file_dir):
            os.makedirs(log_file_dir, exist_ok=True)
            print(f"已创建主日志目录: {log_file_dir}")
            
        main_file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8", mode="w")
        main_file_handler.setLevel(logging.DEBUG)
    except (IOError, OSError) as e:
        print(f"无法创建主日志文件处理器: {e}")
        main_file_handler = None
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式器并添加到处理器
    formatter = URLCensorFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    if main_file_handler:
        main_file_handler.setFormatter(formatter)
    
    # 添加处理器到logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    if main_file_handler:
        logger.addHandler(main_file_handler)
    
    return logger 