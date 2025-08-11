from PySide6.QtCore import Qt, QPoint, QRect, QSize
from PySide6.QtGui import QPainterPath, QRegion

class WindowManager:
    """窗口管理器类，用于处理窗口的基本行为，如拖拽、调整大小和圆角设置"""
    
    def __init__(self, parent_window):
        """初始化窗口管理器
        
        Args:
            parent_window: 父窗口实例
        """
        self.window = parent_window
        self.ui = parent_window.ui
        
        # 拖动窗口相关变量
        self._drag_position = QPoint()
        self._is_dragging = False
        
        # 窗口比例
        self.aspect_ratio = 16 / 9
        self.updateRoundedCorners = True
        
        # 设置圆角窗口
        self.setRoundedCorners()
        
        # 初始化状态管理
        self._setup_window_state()

    def _setup_window_state(self):
        """初始化窗口状态管理."""
        self.STATE_INITIALIZING = "initializing"
        self.STATE_READY = "ready"
        self.STATE_DOWNLOADING = "downloading"
        self.STATE_EXTRACTING = "extracting"
        self.STATE_VERIFYING = "verifying"
        self.STATE_INSTALLING = "installing"
        self.STATE_COMPLETED = "completed"
        self.STATE_ERROR = "error"
        
        self.current_state = self.STATE_INITIALIZING

    def change_window_state(self, new_state, error_message=None):
        """更改窗口状态并更新UI.
        
        Args:
            new_state (str): 新的状态.
            error_message (str, optional): 错误信息. Defaults to None.
        """
        if new_state == self.current_state:
            return
            
        self.current_state = new_state
        self._update_ui_for_state(new_state, error_message)

    def _update_ui_for_state(self, state, error_message=None):
        """根据当前状态更新UI组件."""
        is_offline = self.window.offline_mode_manager.is_in_offline_mode()
        config_valid = self.window.config_valid
        
        button_enabled = False
        button_text = "!无法安装!"

        if state == self.STATE_READY:
            if is_offline or config_valid:
                button_enabled = True
                button_text = "开始安装"
        elif state in [self.STATE_DOWNLOADING, self.STATE_EXTRACTING, self.STATE_VERIFYING, self.STATE_INSTALLING]:
            button_text = "正在安装"
        elif state == self.STATE_COMPLETED:
            button_enabled = True
            button_text = "安装完成" # Or back to "开始安装"
        
        self.window.ui.start_install_btn.setEnabled(button_enabled)
        self.window.ui.start_install_text.setText(button_text)
        self.window.install_button_enabled = button_enabled

    def setRoundedCorners(self):
        """设置窗口圆角"""
        # 实现圆角窗口
        path = QPainterPath()
        path.addRoundedRect(self.window.rect(), 20, 20)
        mask = QRegion(path.toFillPolygon().toPolygon())
        self.window.setMask(mask)
        
        # 更新resize事件时更新圆角
        self.updateRoundedCorners = True
    
    def handle_mouse_press(self, event):
        """处理鼠标按下事件
        
        Args:
            event: 鼠标事件
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # 只有当鼠标在标题栏区域时才可以拖动
            if hasattr(self.ui, 'title_bar') and self.ui.title_bar.geometry().contains(event.position().toPoint()):
                self._is_dragging = True
                self._drag_position = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
            event.accept()
    
    def handle_mouse_move(self, event):
        """处理鼠标移动事件
        
        Args:
            event: 鼠标事件
        """
        if event.buttons() & Qt.MouseButton.LeftButton and self._is_dragging:
            self.window.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
    
    def handle_mouse_release(self, event):
        """处理鼠标释放事件
        
        Args:
            event: 鼠标事件
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()
    
    def handle_resize(self, event):
        """当窗口大小改变时更新圆角和维持纵横比
        
        Args:
            event: 窗口大小改变事件
        """
        # 计算基于当前宽度的合适高度，以维持16:9比例
        new_width = event.size().width()
        new_height = int(new_width / self.aspect_ratio)
        
        if new_height != event.size().height():
            # 阻止变形，保持比例
            self.window.resize(new_width, new_height)
        
        # 更新主容器大小
        if hasattr(self.ui, 'main_container'):
            self.ui.main_container.setGeometry(0, 0, new_width, new_height)
            
        # 更新内容容器大小    
        if hasattr(self.ui, 'content_container'):
            self.ui.content_container.setGeometry(0, 0, new_width, new_height)
            
        # 更新标题栏宽度和高度
        if hasattr(self.ui, 'title_bar'):
            self.ui.title_bar.setGeometry(0, 0, new_width, 35)
        
        # 更新菜单区域
        if hasattr(self.ui, 'menu_area'):
            self.ui.menu_area.setGeometry(0, 35, new_width, 30)
            
        # 更新内容区域大小
        if hasattr(self.ui, 'inner_content'):
            self.ui.inner_content.setGeometry(0, 65, new_width, new_height - 65)
            
        # 更新背景图大小
        if hasattr(self.ui, 'Mainbg'):
            self.ui.Mainbg.setGeometry(0, 0, new_width, new_height - 65)
            
        if hasattr(self.ui, 'loadbg'):
            self.ui.loadbg.setGeometry(0, 0, new_width, new_height - 65)
            
        # 调整按钮位置 - 固定在右侧
        right_margin = 20  # 减小右边距，使按钮更靠右
        if hasattr(self.ui, 'button_container'):
            btn_width = 211  # 扩大后的容器宽度
            btn_height = 111  # 扩大后的容器高度
            x_pos = new_width - btn_width - right_margin
            y_pos = int((new_height - 65) * 0.18) - 10  # 从0.28改为0.18，向上移动
            self.ui.button_container.setGeometry(x_pos, y_pos, btn_width, btn_height)
            
        # 添加禁/启用补丁按钮容器的位置调整
        if hasattr(self.ui, 'toggle_patch_container'):
            btn_width = 211  # 扩大后的容器宽度
            btn_height = 111  # 扩大后的容器高度
            x_pos = new_width - btn_width - right_margin
            y_pos = int((new_height - 65) * 0.36) - 10  # 从0.46改为0.36，向上移动
            self.ui.toggle_patch_container.setGeometry(x_pos, y_pos, btn_width, btn_height)
            
        # 添加卸载补丁按钮容器的位置调整
        if hasattr(self.ui, 'uninstall_container'):
            btn_width = 211  # 扩大后的容器宽度
            btn_height = 111  # 扩大后的容器高度
            x_pos = new_width - btn_width - right_margin
            y_pos = int((new_height - 65) * 0.54) - 10  # 从0.64改为0.54，向上移动
            self.ui.uninstall_container.setGeometry(x_pos, y_pos, btn_width, btn_height)
            
        if hasattr(self.ui, 'exit_container'):
            btn_width = 211  # 扩大后的容器宽度
            btn_height = 111  # 扩大后的容器高度
            x_pos = new_width - btn_width - right_margin
            y_pos = int((new_height - 65) * 0.72) - 10  # 从0.82改为0.72，向上移动
            self.ui.exit_container.setGeometry(x_pos, y_pos, btn_width, btn_height)
            
        # 更新圆角
        if hasattr(self, 'updateRoundedCorners') and self.updateRoundedCorners:
            path = QPainterPath()
            path.addRoundedRect(self.window.rect(), 20, 20)
            mask = QRegion(path.toFillPolygon().toPolygon())
            self.window.setMask(mask) 