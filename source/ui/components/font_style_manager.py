"""
字体和样式管理器
负责管理应用程序的字体加载和UI样式
"""

import os
import logging
import traceback
from PySide6.QtGui import QFont, QFontDatabase

from utils import resource_path

logger = logging.getLogger(__name__)


class FontStyleManager:
    """字体和样式管理器"""
    
    def __init__(self):
        """初始化字体样式管理器"""
        self._cached_font = None
        self._font_family = "Arial"  # 默认字体族
        self._load_custom_font()
    
    def _load_custom_font(self):
        """加载自定义字体"""
        try:
            # 使用resource_path查找字体文件
            font_path = resource_path(os.path.join("assets", "fonts", "SmileySans-Oblique.ttf"))
            
            # 详细记录字体加载过程
            if os.path.exists(font_path):
                logger.info(f"尝试加载字体文件: {font_path}")
                font_id = QFontDatabase.addApplicationFont(font_path)
                
                if font_id != -1:
                    font_families = QFontDatabase.applicationFontFamilies(font_id)
                    if font_families:
                        self._font_family = font_families[0]
                        logger.info(f"成功加载字体: {self._font_family} 从 {font_path}")
                    else:
                        logger.warning(f"字体加载成功但无法获取字体族: {font_path}")
                else:
                    logger.warning(f"字体加载失败: {font_path} (返回ID: {font_id})")
                    self._check_font_file_issues(font_path)
            else:
                logger.error(f"找不到字体文件: {font_path}")
                self._list_font_directory(font_path)
                
        except Exception as e:
            logger.error(f"加载字体过程中发生异常: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
    
    def _check_font_file_issues(self, font_path):
        """检查字体文件的问题"""
        try:
            file_size = os.path.getsize(font_path)
            logger.debug(f"字体文件大小: {file_size} 字节")
            if file_size == 0:
                logger.error(f"字体文件大小为0字节: {font_path}")
            
            # 尝试打开文件测试可读性
            with open(font_path, 'rb') as f:
                f.read(10)  # 只读取前几个字节测试可访问性
                logger.debug(f"字体文件可以正常打开和读取")
        except Exception as file_error:
            logger.error(f"字体文件访问错误: {file_error}")
    
    def _list_font_directory(self, font_path):
        """列出字体目录下的文件"""
        try:
            fonts_dir = os.path.dirname(font_path)
            if os.path.exists(fonts_dir):
                files = os.listdir(fonts_dir)
                logger.debug(f"字体目录 {fonts_dir} 中的文件: {files}")
            else:
                logger.debug(f"字体目录不存在: {fonts_dir}")
        except Exception as dir_error:
            logger.error(f"无法列出字体目录内容: {dir_error}")
    
    def get_menu_font(self, size=14, bold=True):
        """获取菜单字体
        
        Args:
            size: 字体大小，默认14
            bold: 是否加粗，默认True
            
        Returns:
            QFont: 配置好的菜单字体
        """
        if self._cached_font is None or self._cached_font.pointSize() != size:
            self._cached_font = QFont(self._font_family, size)
            self._cached_font.setBold(bold)
        return self._cached_font
    
    def get_menu_style(self, font_family=None):
        """获取统一的菜单样式
        
        Args:
            font_family: 字体族，如果不提供则使用默认
            
        Returns:
            str: CSS样式字符串
        """
        if font_family is None:
            font_family = self._font_family
            
        return f"""
            QMenu {{
                background-color: #E96948;
                color: white;
                font-family: "{font_family}";
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #F47A5B;
                padding: 8px;
                border-radius: 6px;
                margin-top: 2px;
            }}
            QMenu::item {{
                padding: 6px 20px 6px 15px;
                background-color: transparent;
                min-width: 120px;
                color: white;
                font-family: "{font_family}";
                font-size: 14px;
                font-weight: bold;
            }}
            QMenu::item:selected {{
                background-color: #F47A5B;
                border-radius: 4px;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: #F47A5B;
                margin: 5px 15px;
            }}
            QMenu::item:checked {{
                background-color: #D25A3C;
                border-radius: 4px;
            }}
        """
    
    @property
    def font_family(self):
        """获取当前字体族"""
        return self._font_family