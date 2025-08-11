import os
import logging
import datetime
import sys
import glob
import time
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from config.config import LOG_DIR, LOG_FILE, LOG_LEVEL, LOG_MAX_SIZE, LOG_BACKUP_COUNT, LOG_RETENTION_DAYS

from .url_censor import censor_url

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

def cleanup_old_logs(retention_days=7):
    """清理超过指定天数的旧日志文件
    
    Args:
        retention_days: 日志保留天数，默认7天
    """
    try:
        now = time.time()
        cutoff = now - (retention_days * 86400)  # 86400秒 = 1天
        
        # 获取所有日志文件
        log_files = glob.glob(os.path.join(LOG_DIR, "log-*.txt"))
        
        for log_file in log_files:
            # 检查文件修改时间
            if os.path.getmtime(log_file) < cutoff:
                try:
                    os.remove(log_file)
                    print(f"已删除过期日志: {log_file}")
                except Exception as e:
                    print(f"删除日志文件失败 {log_file}: {e}")
    except Exception as e:
        print(f"清理旧日志文件时出错: {e}")

def setup_logger(name):
    """设置并返回一个命名的logger
    
    使用统一的日志文件，添加日志轮转功能，实现自动清理过期日志

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
    
    # 根据配置设置日志级别
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.DEBUG)
    logger.setLevel(log_level)
    
    # 确保日志目录存在
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 清理过期日志文件
    cleanup_old_logs(LOG_RETENTION_DAYS)
    
    # 创建主日志文件的轮转处理器
    try:
        # 确保主日志文件目录存在
        log_file_dir = os.path.dirname(LOG_FILE)
        if log_file_dir and not os.path.exists(log_file_dir):
            os.makedirs(log_file_dir, exist_ok=True)
            print(f"已创建主日志目录: {log_file_dir}")
        
        # 使用RotatingFileHandler实现日志轮转
        main_file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_SIZE,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8"
        )
        main_file_handler.setLevel(log_level)
    except (IOError, OSError) as e:
        print(f"无法创建主日志文件处理器: {e}")
        main_file_handler = None
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # 控制台只显示INFO以上级别
    
    # 创建更详细的格式器，包括模块名、文件名和行号
    formatter = URLCensorFormatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    
    console_handler.setFormatter(formatter)
    if main_file_handler:
        main_file_handler.setFormatter(formatter)
    
    # 添加处理器到logger
    logger.addHandler(console_handler)
    if main_file_handler:
        logger.addHandler(main_file_handler)
    
    return logger 