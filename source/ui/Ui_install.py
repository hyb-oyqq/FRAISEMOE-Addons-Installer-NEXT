from data.pic_data import img_data
from PySide6.QtGui import QPixmap
import base64
from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform, QPainterPath, QRegion)
from PySide6.QtWidgets import (QApplication, QLabel, QMainWindow, QMenu,
    QMenuBar, QPushButton, QSizePolicy, QWidget, QHBoxLayout)
import os

def load_base64_image(base64_str):
    pixmap = QPixmap()
    pixmap.loadFromData(base64.b64decode(base64_str))
    return pixmap

def load_image_from_file(file_path):
    if os.path.exists(file_path):
        return QPixmap(file_path)
    return QPixmap()

class Ui_MainWindows(object):
    def setupUi(self, MainWindows):
        if not MainWindows.objectName():
            MainWindows.setObjectName(u"MainWindows")
        MainWindows.setEnabled(True)
        # 调整窗口默认大小为1280x720以匹配背景图片
        MainWindows.resize(1280, 720)
        # 移除最大和最小尺寸限制，允许自由缩放
        # MainWindows.setMinimumSize(QSize(1024, 576))
        # MainWindows.setMaximumSize(QSize(1024, 576))
        MainWindows.setMouseTracking(False)
        MainWindows.setTabletTracking(False)
        MainWindows.setAcceptDrops(True)
        MainWindows.setAutoFillBackground(False)
        MainWindows.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        MainWindows.setAnimated(True)
        MainWindows.setDocumentMode(False)
        MainWindows.setDockNestingEnabled(False)
        
        # 加载自定义字体
        font_id = QFontDatabase.addApplicationFont(os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts", "SmileySans-Oblique.ttf"))
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0] if font_id != -1 else "Arial"
        self.custom_font = QFont(font_family, 16)  # 创建字体对象，大小为16
        self.custom_font.setWeight(QFont.Weight.Medium)  # 设置为中等粗细，不要太粗
        
        self.centralwidget = QWidget(MainWindows)
        self.centralwidget.setObjectName(u"centralwidget")
        self.centralwidget.setAutoFillBackground(False)  # 修改为False以支持透明背景
        self.centralwidget.setStyleSheet("""
            QWidget#centralwidget {
                background-color: transparent;
            }
        """)

        # 圆角背景容器
        self.main_container = QWidget(self.centralwidget)
        self.main_container.setObjectName(u"main_container")
        self.main_container.setGeometry(QRect(0, 0, 1280, 720))
        self.main_container.setStyleSheet("""
            QWidget#main_container {
                background-color: #C5DDFC;
                border-radius: 20px;
                border: 1px solid #A4C2F4;
            }
        """)

        # 内容容器 - 用于限制内容在圆角范围内
        self.content_container = QWidget(self.main_container)
        self.content_container.setObjectName(u"content_container")
        self.content_container.setGeometry(QRect(0, 0, 1280, 720))
        self.content_container.setStyleSheet("""
            QWidget#content_container {
                background-color: transparent;
                border-radius: 20px;
            }
        """)
        
        # 添加圆角裁剪，确保内容在圆角范围内
        rect = QRect(0, 0, 1280, 720)
        path = QPainterPath()
        path.addRoundedRect(rect, 20, 20)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.content_container.setMask(region)

        # 禁用裁剪，这可能导致窗口变形
        # rect = self.content_container.rect()
        # path = QPainterPath()
        # path.addRoundedRect(rect, 20, 20)
        # self.content_container.setMask(QRegion(path.toFillPolygon().toPolygon()))

        # 标题栏
        self.title_bar = QWidget(self.content_container)
        self.title_bar.setObjectName(u"title_bar")
        self.title_bar.setGeometry(QRect(0, 0, 1280, 30))
        self.title_bar.setStyleSheet("""
            QWidget#title_bar {
                background-color: #A4C2F4;
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
                border-bottom: 1px solid #8AB4F8;
            }
        """)

        # 标题栏布局
        self.title_layout = QHBoxLayout(self.title_bar)
        self.title_layout.setSpacing(10)
        self.title_layout.setContentsMargins(10, 0, 10, 0)

        # 添加最小化和关闭按钮到标题栏
        self.minimize_btn = QPushButton(self.title_bar)
        self.minimize_btn.setObjectName(u"minimize_btn")
        self.minimize_btn.setMinimumSize(QSize(24, 24))
        self.minimize_btn.setMaximumSize(QSize(24, 24))
        self.minimize_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFC107;
                border-radius: 12px;
                border: none;
            }
            QPushButton:hover {
                background-color: #FFD54F;
            }
            QPushButton:pressed {
                background-color: #FFA000;
            }
        """)
        self.minimize_btn.setText("—")
        self.minimize_btn.setFont(QFont(font_family, 10))

        self.close_btn = QPushButton(self.title_bar)
        self.close_btn.setObjectName(u"close_btn")
        self.close_btn.setMinimumSize(QSize(24, 24))
        self.close_btn.setMaximumSize(QSize(24, 24))
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                border-radius: 12px;
                border: none;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #EF5350;
            }
            QPushButton:pressed {
                background-color: #D32F2F;
            }
        """)
        self.close_btn.setText("×")
        self.close_btn.setFont(QFont(font_family, 14))

        # 标题文本
        self.title_label = QLabel(self.title_bar)
        self.title_label.setObjectName(u"title_label")
        self.title_label.setText("FraiseMoe Addons Manager")
        title_font = QFont(font_family, 12)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #333333; padding-left: 10px;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 添加按钮到标题栏布局
        self.title_layout.addWidget(self.title_label)
        self.title_layout.addStretch(1)
        self.title_layout.addWidget(self.minimize_btn)
        self.title_layout.addSpacing(5)
        self.title_layout.addWidget(self.close_btn)

        # 菜单区域
        self.menu_area = QWidget(self.content_container)
        self.menu_area.setObjectName(u"menu_area")
        self.menu_area.setGeometry(QRect(0, 30, 1024, 25))
        self.menu_area.setStyleSheet("""
            QWidget#menu_area {
                background-color: #D4E4FC;
                border-bottom: 1px solid #A4C2F4;
            }
        """)

        # 创建菜单栏在菜单区域中
        self.menubar = QMenuBar(self.menu_area)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(10, 2, 200, 20))
        self.menubar.setStyleSheet("""
            QMenuBar {
                background-color: transparent;
                color: #333333;
                font-weight: bold;
                spacing: 5px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 1px 8px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: rgba(0, 0, 0, 0.1);
            }
            QMenuBar::item:pressed {
                background-color: rgba(0, 0, 0, 0.15);
            }
            QMenu {
                background-color: #D4E4FC;
                border: 1px solid #A4C2F4;
                border-radius: 6px;
                padding: 5px;
                margin: 2px;
            }
            QMenu::item {
                padding: 6px 25px 6px 20px;
                color: #333333;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(0, 0, 0, 0.1);
            }
        """)

        # 内容子容器
        self.inner_content = QWidget(self.content_container)
        self.inner_content.setObjectName(u"inner_content")
        # 确保宽度足够大，保证右侧元素完全显示
        self.inner_content.setGeometry(QRect(0, 55, 1280, 665))
        self.inner_content.setStyleSheet("""
            QWidget#inner_content {
                background-color: transparent;
                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 20px;
            }
        """)
        
        # 添加底部圆角裁剪
        inner_rect = QRect(0, 0, 1280, 665)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner_rect, 20, 20)
        inner_region = QRegion(inner_path.toFillPolygon().toPolygon())
        self.inner_content.setMask(inner_region)

        # 确保底部的圆角正确显示
        # 在菜单背景区域下方添加一个底部圆角装饰器
        # self.bottom_corner_left = QWidget(self.main_container)
        # self.bottom_corner_left.setObjectName(u"bottom_corner_left")
        # self.bottom_corner_left.setGeometry(QRect(0, 556, 20, 20))
        # self.bottom_corner_left.setStyleSheet("""
        #     QWidget#bottom_corner_left {
        #         background-color: #C5DDFC;
        #         border-bottom-left-radius: 20px;
        #     }
        # """)

        # self.bottom_corner_right = QWidget(self.main_container)
        # self.bottom_corner_right.setObjectName(u"bottom_corner_right")
        # self.bottom_corner_right.setGeometry(QRect(1004, 556, 20, 20))
        # self.bottom_corner_right.setStyleSheet("""
        #     QWidget#bottom_corner_right {
        #         background-color: #C5DDFC;
        #         border-bottom-right-radius: 20px;
        #     }
        # """)

        self.menu = QMenu(self.menubar)
        self.menu.setObjectName(u"menu")
        self.menu_2 = QMenu(self.menubar)
        self.menu_2.setObjectName(u"menu_2")

        self.menubar.addAction(self.menu.menuAction())
        self.menubar.addAction(self.menu_2.menuAction())
        self.menu.addSeparator()
        
        # 在主容器中添加背景和内容元素
        # 修改loadbg使用title_bg1.png作为整个背景
        # 原来的loadbg保持不变
        self.loadbg = QLabel(self.inner_content)
        self.loadbg.setObjectName(u"loadbg")
        self.loadbg.setGeometry(QRect(0, 0, 1280, 665))  # 调整尺寸
        self.loadbg.setPixmap(load_base64_image(img_data["loadbg"]))
        self.loadbg.setScaledContents(True)
        
        self.vol1bg = QLabel(self.inner_content)
        self.vol1bg.setObjectName(u"vol1bg")
        self.vol1bg.setGeometry(QRect(0, 150, 93, 64))
        self.vol1bg.setPixmap(load_base64_image(img_data["vol1"]))
        self.vol1bg.setScaledContents(True)
        
        self.vol2bg = QLabel(self.inner_content)
        self.vol2bg.setObjectName(u"vol2bg")
        self.vol2bg.setGeometry(QRect(0, 210, 93, 64))
        self.vol2bg.setPixmap(load_base64_image(img_data["vol2"]))
        self.vol2bg.setScaledContents(True)
        
        self.vol3bg = QLabel(self.inner_content)
        self.vol3bg.setObjectName(u"vol3bg")
        self.vol3bg.setGeometry(QRect(0, 270, 93, 64))
        self.vol3bg.setPixmap(load_base64_image(img_data["vol3"]))
        self.vol3bg.setScaledContents(True)
        
        self.vol4bg = QLabel(self.inner_content)
        self.vol4bg.setObjectName(u"vol4bg")
        self.vol4bg.setGeometry(QRect(0, 330, 93, 64))
        self.vol4bg.setPixmap(load_base64_image(img_data["vol4"]))
        self.vol4bg.setScaledContents(True)
        
        self.afterbg = QLabel(self.inner_content)
        self.afterbg.setObjectName(u"afterbg")
        self.afterbg.setGeometry(QRect(0, 390, 93, 64))
        self.afterbg.setPixmap(load_base64_image(img_data["after"]))
        self.afterbg.setScaledContents(True)
        
        # 修复Mainbg位置并使用title_bg1.png作为背景图片
        self.Mainbg = QLabel(self.inner_content)
        self.Mainbg.setObjectName(u"Mainbg")
        self.Mainbg.setGeometry(QRect(0, 0, 1280, 665))  # 调整尺寸
        self.Mainbg.setPixmap(load_image_from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "IMG", "BG", "title_bg1.png")))
        self.Mainbg.setScaledContents(True)
        
        # 使用新的按钮图片
        button_pixmap = load_image_from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "IMG", "BTN", "Button.png"))
        
        # 创建文本标签布局的按钮
        # 开始安装按钮 - 基于背景图片和标签组合
        self.button_container = QWidget(self.inner_content)
        self.button_container.setObjectName(u"start_install_container")
        self.button_container.setGeometry(QRect(1050, 285, 211, 111))  # 扩大容器尺寸，预留动画空间
        # 不要隐藏容器，让动画系统来控制它的可见性和位置

        # 使用原来的按钮背景图片
        self.start_install_bg = QLabel(self.button_container)
        self.start_install_bg.setObjectName(u"start_install_bg")
        self.start_install_bg.setGeometry(QRect(10, 10, 191, 91))  # 居中放置在扩大的容器中
        self.start_install_bg.setPixmap(button_pixmap)
        self.start_install_bg.setScaledContents(True)

        self.start_install_text = QLabel(self.button_container)
        self.start_install_text.setObjectName(u"start_install_text")
        self.start_install_text.setGeometry(QRect(10, 7, 191, 91))  # 居中放置在扩大的容器中
        self.start_install_text.setText("开始安装")
        self.start_install_text.setFont(self.custom_font)
        self.start_install_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.start_install_text.setStyleSheet("letter-spacing: 1px;")

        # 点击区域透明按钮
        self.start_install_btn = QPushButton(self.button_container)
        self.start_install_btn.setObjectName(u"start_install_btn")
        self.start_install_btn.setGeometry(QRect(10, 10, 191, 91))  # 居中放置在扩大的容器中
        self.start_install_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))  # 设置鼠标悬停时为手形光标
        self.start_install_btn.setFlat(True)
        self.start_install_btn.raise_()  # 确保按钮在最上层
        self.start_install_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
        """)
        
        # 退出按钮 - 基于背景图片和标签组合
        self.exit_container = QWidget(self.inner_content)
        self.exit_container.setObjectName(u"exit_container")
        self.exit_container.setGeometry(QRect(1050, 415, 211, 111))  # 扩大容器尺寸，预留动画空间
        # 不要隐藏容器，让动画系统来控制它的可见性和位置

        # 使用原来的按钮背景图片
        self.exit_bg = QLabel(self.exit_container)
        self.exit_bg.setObjectName(u"exit_bg")
        self.exit_bg.setGeometry(QRect(10, 10, 191, 91))  # 居中放置在扩大的容器中
        self.exit_bg.setPixmap(button_pixmap)
        self.exit_bg.setScaledContents(True)

        self.exit_text = QLabel(self.exit_container)
        self.exit_text.setObjectName(u"exit_text")
        self.exit_text.setGeometry(QRect(10, 7, 191, 91))  # 居中放置在扩大的容器中
        self.exit_text.setText("退出程序")
        self.exit_text.setFont(self.custom_font)
        self.exit_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.exit_text.setStyleSheet("letter-spacing: 1px;")
        
        # 点击区域透明按钮
        self.exit_btn = QPushButton(self.exit_container)
        self.exit_btn.setObjectName(u"exit_btn")
        self.exit_btn.setGeometry(QRect(10, 10, 191, 91))  # 居中放置在扩大的容器中
        self.exit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))  # 设置鼠标悬停时为手形光标
        self.exit_btn.setFlat(True)
        self.exit_btn.raise_()  # 确保按钮在最上层
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
        """)
        
        # 注释掉menubg，移除右侧背景区域
        # self.menubg = QLabel(self.inner_content)
        # self.menubg.setObjectName(u"menubg")
        # # 将X坐标调整为720，以使背景图片更靠右
        # self.menubg.setGeometry(QRect(720, 0, 321, 521))
        # self.menubg.setPixmap(load_base64_image(img_data["menubg"]))
        # self.menubg.setScaledContents(True)
        
        # 恢复按钮位置
        # self.exit_container = QWidget(self.inner_content)
        # self.exit_container.setObjectName(u"exit_container")
        # self.exit_container.setGeometry(QRect(780, 340, 191, 91))  # 恢复到原来的位置 780
        
        MainWindows.setCentralWidget(self.centralwidget)
        
        # 调整层级顺序
        self.loadbg.raise_()
        self.vol1bg.raise_()
        self.vol2bg.raise_()
        self.vol3bg.raise_()
        self.vol4bg.raise_()
        self.afterbg.raise_()
        self.Mainbg.raise_()
        # self.menubg.raise_()  # 注释掉menubg
        # 不再需要底部圆角装饰器
        # self.bottom_corner_left.raise_()
        # self.bottom_corner_right.raise_()
        self.button_container.raise_()
        self.exit_container.raise_()
        self.menu_area.raise_()  # 确保菜单区域在背景之上
        self.title_bar.raise_()  # 确保标题栏在最上层
        
        # 保留原有菜单栏，调整到主容器内部
        # self.menubar = QMenuBar(self.main_container)
        # self.menubar.setObjectName(u"menubar")
        # self.menubar.setGeometry(QRect(0, 0, 1024, 21))
        # self.menu = QMenu(self.menubar)
        # self.menu.setObjectName(u"menu")
        # self.menu_2 = QMenu(self.menubar)
        # self.menu_2.setObjectName(u"menu_2")
        # 不再调用MainWindows.setMenuBar，而是手动将菜单栏添加到主容器
        # MainWindows.setMenuBar(self.menubar)

        # self.menubar.addAction(self.menu.menuAction())
        # self.menubar.addAction(self.menu_2.menuAction())
        # self.menu.addSeparator()
        self.retranslateUi(MainWindows)

        QMetaObject.connectSlotsByName(MainWindows)
    # setupUi

    def retranslateUi(self, MainWindows):
        MainWindows.setWindowTitle(QCoreApplication.translate("MainWindows", u" UI Test", None))
        self.loadbg.setText("")
        self.vol1bg.setText("")
        self.vol2bg.setText("")
        self.vol3bg.setText("")
        self.vol4bg.setText("")
        self.afterbg.setText("")
        self.Mainbg.setText("")
#if QT_CONFIG(accessibility)
        self.start_install_btn.setAccessibleDescription("")
#endif // QT_CONFIG(accessibility)
        # self.menubg.setText("") # 注释掉menubg
        self.menu.setTitle(QCoreApplication.translate("MainWindows", u"\u8bbe\u7f6e", None))
        self.menu_2.setTitle(QCoreApplication.translate("MainWindows", u"\u5e2e\u52a9", None))
    # retranslateUi

