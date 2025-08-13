import sys
from PySide6.QtCore import (QObject, QPropertyAnimation, QParallelAnimationGroup,
                          QPoint, QEasingCurve, QTimer, Signal, QRect)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QPushButton
from PySide6.QtGui import QColor

class MultiStageAnimations(QObject):
    animation_finished = Signal()
    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.parent = parent  # 保存父窗口引用以获取当前尺寸
        
        # 获取画布尺寸 - 动态从父窗口获取
        if parent:
            self.canvas_width = parent.width()
            self.canvas_height = parent.height()
        else:
            # 默认尺寸
            self.canvas_width = 1280
            self.canvas_height = 720
        
        # 动画时序配置
        self.animation_config = {
            "logo": {
                "delay_after": 2800
            },
            "mainbg": {
                "delay_after": 500
            },
            "button_click": {
                "scale_duration": 100,
                "scale_min": 0.95,
                "scale_max": 1.0
            }
        }
        
        # 第一阶段：Logo动画配置，根据新布局调整Y坐标
        self.logo_widgets = [
            {"widget": ui.vol1bg, "delay": 0, "duration": 500, "end_pos": QPoint(0, 150)},
            {"widget": ui.vol2bg, "delay": 80, "duration": 500, "end_pos": QPoint(0, 210)},
            {"widget": ui.vol3bg, "delay": 160, "duration": 500, "end_pos": QPoint(0, 270)},
            {"widget": ui.vol4bg, "delay": 240, "duration": 500, "end_pos": QPoint(0, 330)},
            {"widget": ui.afterbg, "delay": 320, "duration": 500, "end_pos": QPoint(0, 390)}
        ]
        
        # 第二阶段：菜单元素，位置会在开始动画时动态计算
        self.menu_widgets = [
            # 移除菜单背景动画
            # {"widget": ui.menubg, "end_pos": QPoint(720, 55), "duration": 600},
            {"widget": ui.button_container, "end_pos": None, "duration": 600},
            {"widget": ui.toggle_patch_container, "end_pos": None, "duration": 600},  # 添加禁/启用补丁按钮
            {"widget": ui.uninstall_container, "end_pos": None, "duration": 600},  # 添加卸载补丁按钮
            {"widget": ui.exit_container, "end_pos": None, "duration": 600}
        ]
        
        self.animations = []
        self.timers = []
        
        # 设置按钮点击动画
        self.setup_button_click_animations()
    
    def setup_button_click_animations(self):
        """设置按钮点击动画"""
        # 为开始安装按钮添加点击动画
        self.ui.start_install_btn.pressed.connect(
            lambda: self.start_button_click_animation(self.ui.button_container)
        )
        self.ui.start_install_btn.released.connect(
            lambda: self.end_button_click_animation(self.ui.button_container)
        )
        
        # 为卸载补丁按钮添加点击动画
        self.ui.uninstall_btn.pressed.connect(
            lambda: self.start_button_click_animation(self.ui.uninstall_container)
        )
        self.ui.uninstall_btn.released.connect(
            lambda: self.end_button_click_animation(self.ui.uninstall_container)
        )
        
        # 为退出按钮添加点击动画
        self.ui.exit_btn.pressed.connect(
            lambda: self.start_button_click_animation(self.ui.exit_container)
        )
        self.ui.exit_btn.released.connect(
            lambda: self.end_button_click_animation(self.ui.exit_container)
        )
    
    def start_button_click_animation(self, button_container):
        """开始按钮点击动画"""
        # 创建缩放动画
        scale_anim = QPropertyAnimation(button_container.children()[0], b"geometry")  # 只对按钮背景应用动画
        scale_anim.setDuration(self.animation_config["button_click"]["scale_duration"])
        
        # 获取当前几何形状
        current_geometry = button_container.children()[0].geometry()
        
        # 计算缩放后的几何形状（保持中心点不变）
        scale_factor = self.animation_config["button_click"]["scale_min"]
        width_diff = current_geometry.width() * (1 - scale_factor) / 2
        height_diff = current_geometry.height() * (1 - scale_factor) / 2
        
        new_geometry = QRect(
            current_geometry.x() + width_diff,
            current_geometry.y() + height_diff,
            current_geometry.width() * scale_factor,
            current_geometry.height() * scale_factor
        )
        
        scale_anim.setEndValue(new_geometry)
        scale_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # 启动动画
        scale_anim.start()
        self.animations.append(scale_anim)
        
        # 对文本标签也应用同样的动画
        text_anim = QPropertyAnimation(button_container.children()[1], b"geometry")
        text_anim.setDuration(self.animation_config["button_click"]["scale_duration"])
        text_geometry = button_container.children()[1].geometry()
        
        new_text_geometry = QRect(
            text_geometry.x() + width_diff,
            text_geometry.y() + height_diff,
            text_geometry.width() * scale_factor,
            text_geometry.height() * scale_factor
        )
        
        text_anim.setEndValue(new_text_geometry)
        text_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        text_anim.start()
        self.animations.append(text_anim)
    
    def end_button_click_animation(self, button_container):
        """结束按钮点击动画，恢复正常外观"""
        # 创建恢复动画 - 对背景
        scale_anim = QPropertyAnimation(button_container.children()[0], b"geometry")
        scale_anim.setDuration(self.animation_config["button_click"]["scale_duration"])
        
        # 恢复到原始大小 (10,10,191,91)
        original_geometry = QRect(10, 10, 191, 91)
        scale_anim.setEndValue(original_geometry)
        scale_anim.setEasingCurve(QEasingCurve.Type.OutElastic)
        
        # 启动动画
        scale_anim.start()
        self.animations.append(scale_anim)
        
        # 恢复文本标签
        text_anim = QPropertyAnimation(button_container.children()[1], b"geometry")
        text_anim.setDuration(self.animation_config["button_click"]["scale_duration"])
        
        # 恢复文本到原始大小 (10,7,191,91)
        text_anim.setEndValue(QRect(10, 7, 191, 91))
        text_anim.setEasingCurve(QEasingCurve.Type.OutElastic)
        text_anim.start()
        self.animations.append(text_anim)

    def initialize(self):
        """初始化所有组件状态"""
        # 更新画布尺寸
        if self.parent:
            self.canvas_width = self.parent.width()
            self.canvas_height = self.parent.height()
        
        # 设置Mainbg初始状态
        effect = QGraphicsOpacityEffect(self.ui.Mainbg)
        effect.setOpacity(0)
        self.ui.Mainbg.setGraphicsEffect(effect)
        
        # 初始化Logo位置（移到左侧外）
        for item in self.logo_widgets:
            widget = item["widget"]
            effect = QGraphicsOpacityEffect(widget)
            effect.setOpacity(0)
            widget.setGraphicsEffect(effect)
            widget.move(-widget.width(), item["end_pos"].y())
            widget.show()
            # 初始化支持栏动画，这是内部处理，不需要日志输出
        
        # 初始化菜单元素（底部外）
        for item in self.menu_widgets:
            widget = item["widget"]
            effect = QGraphicsOpacityEffect(widget)
            effect.setOpacity(0)
            widget.setGraphicsEffect(effect)
            widget.move(widget.x(), self.canvas_height + 100)
            widget.show()
            
        # 禁用所有按钮，直到动画完成
        self.ui.start_install_btn.setEnabled(False)  # 动画期间禁用
        self.ui.uninstall_btn.setEnabled(False)
        self.ui.exit_btn.setEnabled(False)

    def start_logo_animations(self):
        """启动Logo动画序列"""
        for item in self.logo_widgets:
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(
                lambda w=item["widget"], d=item["duration"], pos=item["end_pos"]: 
                self.animate_logo(w, pos, d)
            )
            timer.start(item["delay"])
            self.timers.append(timer)

    def animate_logo(self, widget, end_pos, duration):
        """执行单个Logo动画"""
        anim_group = QParallelAnimationGroup()
        
        # 位置动画
        pos_anim = QPropertyAnimation(widget, b"pos")
        pos_anim.setDuration(duration)
        pos_anim.setStartValue(QPoint(-widget.width(), end_pos.y()))
        pos_anim.setEndValue(end_pos)
        pos_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        # 透明度动画
        opacity_anim = QPropertyAnimation(widget.graphicsEffect(), b"opacity")
        opacity_anim.setDuration(duration)
        opacity_anim.setStartValue(0)
        opacity_anim.setEndValue(1)
        
        anim_group.addAnimation(pos_anim)
        anim_group.addAnimation(opacity_anim)
        
        # 最后一个Logo动画完成后添加延迟
        if widget == self.logo_widgets[-1]["widget"]:
            anim_group.finished.connect(
                lambda: QTimer.singleShot(
                    self.animation_config["logo"]["delay_after"],
                    self.start_mainbg_animation
                )
            )
        
        anim_group.start()
        self.animations.append(anim_group)

    def start_mainbg_animation(self):
        """启动主背景淡入动画（带延迟）"""
        main_anim = QPropertyAnimation(self.ui.Mainbg.graphicsEffect(), b"opacity")
        main_anim.setDuration(800)
        main_anim.setStartValue(0)
        main_anim.setEndValue(1)
        main_anim.finished.connect(
            lambda: QTimer.singleShot(
                self.animation_config["mainbg"]["delay_after"],
                self.start_menu_animations
            )
        )
        main_anim.start()
        self.animations.append(main_anim)
    def start_menu_animations(self):
        """启动菜单动画（从下往上）"""
        # 更新按钮最终位置
        self._update_button_positions()
        
        # 跟踪最后一个动画，用于连接finished信号
        last_anim = None
        
        for item in self.menu_widgets:
            anim_group = QParallelAnimationGroup()
            
            # 位置动画（从下往上）
            pos_anim = QPropertyAnimation(item["widget"], b"pos")
            pos_anim.setDuration(item["duration"])
            pos_anim.setStartValue(QPoint(item["end_pos"].x(), self.canvas_height + 100))
            pos_anim.setEndValue(item["end_pos"])
            pos_anim.setEasingCurve(QEasingCurve.Type.OutBack)
            
            # 透明度动画
            opacity_anim = QPropertyAnimation(item["widget"].graphicsEffect(), b"opacity")
            opacity_anim.setDuration(item["duration"])
            opacity_anim.setStartValue(0)
            opacity_anim.setEndValue(1)
            
            anim_group.addAnimation(pos_anim)
            anim_group.addAnimation(opacity_anim)

            # 记录最后一个按钮的动画
            if item["widget"] == self.ui.exit_container:
                last_anim = anim_group

            anim_group.start()
            self.animations.append(anim_group)
            
        # 在最后一个动画完成时发出信号
        if last_anim:
            last_anim.finished.connect(self.animation_finished.emit)
    
    def _update_button_positions(self):
        """更新按钮最终位置"""
        # 根据当前窗口大小动态计算按钮位置
        if self.parent:
            width = self.parent.width()
            height = self.parent.height()
            
            # 计算按钮位置
            right_margin = 20  # 减小右边距，使按钮更靠右
            
            # 开始安装按钮
            if hasattr(self.ui, 'button_container'):
                btn_width = self.ui.button_container.width()
                x_pos = width - btn_width - right_margin
                y_pos = int((height - 65) * 0.18) - 10  # 从0.28改为0.18，向上移动
                
                # 更新动画目标位置
                for item in self.menu_widgets:
                    if item["widget"] == self.ui.button_container:
                        item["end_pos"] = QPoint(x_pos, y_pos)
            
            # 禁用补丁按钮
            if hasattr(self.ui, 'toggle_patch_container'):
                btn_width = self.ui.toggle_patch_container.width()
                x_pos = width - btn_width - right_margin
                y_pos = int((height - 65) * 0.36) - 10  # 从0.46改为0.36，向上移动
                
                # 更新动画目标位置
                for item in self.menu_widgets:
                    if item["widget"] == self.ui.toggle_patch_container:
                        item["end_pos"] = QPoint(x_pos, y_pos)
                
            # 卸载补丁按钮
            if hasattr(self.ui, 'uninstall_container'):
                btn_width = self.ui.uninstall_container.width()
                x_pos = width - btn_width - right_margin
                y_pos = int((height - 65) * 0.54) - 10  # 从0.64改为0.54，向上移动
                
                # 更新动画目标位置
                for item in self.menu_widgets:
                    if item["widget"] == self.ui.uninstall_container:
                        item["end_pos"] = QPoint(x_pos, y_pos)
                
            # 退出按钮
            if hasattr(self.ui, 'exit_container'):
                btn_width = self.ui.exit_container.width()
                x_pos = width - btn_width - right_margin
                y_pos = int((height - 65) * 0.72) - 10  # 从0.82改为0.72，向上移动
                
                # 更新动画目标位置
                for item in self.menu_widgets:
                    if item["widget"] == self.ui.exit_container:
                        item["end_pos"] = QPoint(x_pos, y_pos)
        else:
            # 默认位置
            for item in self.menu_widgets:
                if item["widget"] == self.ui.button_container:
                    item["end_pos"] = QPoint(1050, 200)
                elif item["widget"] == self.ui.toggle_patch_container:
                    item["end_pos"] = QPoint(1050, 310)
                elif item["widget"] == self.ui.uninstall_container:
                    item["end_pos"] = QPoint(1050, 420)
                elif item["widget"] == self.ui.exit_container:
                    item["end_pos"] = QPoint(1050, 530)
    
    def start_animations(self):
        """启动完整动画序列"""
        self.clear_animations()
        
        # 确保按钮在动画开始时被禁用
        self.ui.start_install_btn.setEnabled(False)  # 动画期间禁用
        self.ui.uninstall_btn.setEnabled(False)
        self.ui.exit_btn.setEnabled(False)
        
        self.start_logo_animations()

    def clear_animations(self):
        """清理所有动画资源"""
        for timer in self.timers:
            timer.stop()
        for anim in self.animations:
            anim.stop()
        self.timers.clear()
        self.animations.clear()