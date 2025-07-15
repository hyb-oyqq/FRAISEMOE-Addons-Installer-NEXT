from PySide6.QtCore import (QPropertyAnimation, QParallelAnimationGroup,
                          QPoint, QEasingCurve, QTimer)
from PySide6.QtWidgets import QGraphicsOpacityEffect

class MultiStageAnimations:
    def __init__(self, ui):
        self.ui = ui
        # 获取画布尺寸
        self.canvas_width = ui.centralwidget.width()
        self.canvas_height = ui.centralwidget.height()
        
        # 动画时序配置
        self.animation_config = {
            "logo": {
                "delay_after": 2800
            },
            "mainbg": {
                "delay_after": 500
            }
        }
        
        # 第一阶段：Logo动画配置
        self.logo_widgets = [
            {"widget": ui.vol1bg, "delay": 0, "duration": 500, "end_pos": QPoint(0, 120)},
            {"widget": ui.vol2bg, "delay": 80, "duration": 500, "end_pos": QPoint(0, 180)},
            {"widget": ui.vol3bg, "delay": 160, "duration": 500, "end_pos": QPoint(0, 240)},
            {"widget": ui.vol4bg, "delay": 240, "duration": 500, "end_pos": QPoint(0, 300)},
            {"widget": ui.afterbg, "delay": 320, "duration": 500, "end_pos": QPoint(0, 360)}
        ]
        
        # 第二阶段：菜单元素
        self.menu_widgets = [
            {"widget": ui.menubg, "end_pos": QPoint(710, 0), "duration": 600},
            {"widget": ui.start_install_btn, "end_pos": QPoint(780, 250), "duration": 600},
            {"widget": ui.exit_btn, "end_pos": QPoint(780, 340), "duration": 600}
        ]
        
        self.animations = []
        self.timers = []
    def initialize(self):
        """初始化所有组件状态"""
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
            print("初始化支持栏动画")
        
        # 初始化菜单元素（底部外）
        for item in self.menu_widgets:
            widget = item["widget"]
            effect = QGraphicsOpacityEffect(widget)
            effect.setOpacity(0)
            widget.setGraphicsEffect(effect)
            widget.move(widget.x(), self.canvas_height + 100)
            widget.show()

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
        pos_anim.setEasingCurve(QEasingCurve.OutBack)
        
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
        """启动主背景淡入动画"""
        main_anim = QPropertyAnimation(self.ui.Mainbg.graphicsEffect(), b"opacity")
        main_anim.setDuration(800)
        main_anim.setStartValue(0)
        main_anim.setEndValue(1)
        main_anim.finished.connect(self.start_menu_animations)
        main_anim.start()
        self.animations.append(main_anim)

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
        for item in self.menu_widgets:
            anim_group = QParallelAnimationGroup()
            
            # 位置动画（从下往上）
            pos_anim = QPropertyAnimation(item["widget"], b"pos")
            pos_anim.setDuration(item["duration"])
            pos_anim.setStartValue(QPoint(item["end_pos"].x(), self.canvas_height + 100))
            pos_anim.setEndValue(item["end_pos"])
            pos_anim.setEasingCurve(QEasingCurve.OutBack)
            
            # 透明度动画
            opacity_anim = QPropertyAnimation(item["widget"].graphicsEffect(), b"opacity")
            opacity_anim.setDuration(item["duration"])
            opacity_anim.setStartValue(0)
            opacity_anim.setEndValue(1)
            
            anim_group.addAnimation(pos_anim)
            anim_group.addAnimation(opacity_anim)
            anim_group.start()
            self.animations.append(anim_group)
    def start_animations(self):
        """启动完整动画序列"""
        self.clear_animations()
        self.start_logo_animations()

    def clear_animations(self):
        """清理所有动画资源"""
        for timer in self.timers:
            timer.stop()
        for anim in self.animations:
            anim.stop()
        self.timers.clear()
        self.animations.clear()