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

# 导入配置常量
from data.config import APP_NAME, APP_VERSION

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
                background-color: #E96948;
                border-radius: 20px;
                border: 1px solid #E96948;
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

        # 标题栏
        self.title_bar = QWidget(self.content_container)
        self.title_bar.setObjectName(u"title_bar")
        self.title_bar.setGeometry(QRect(0, 0, 1280, 35))  # 减小高度从40到35
        self.title_bar.setStyleSheet("""
            QWidget#title_bar {
                background-color: #E96948;
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
                border-bottom: 1px solid #F47A5B;
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
        # 直接使用APP_NAME并添加版本号
        self.title_label.setText(f"{APP_NAME} v{APP_VERSION}")
        title_font = QFont(font_family, 14)  # 减小字体从16到14
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

        # 修改菜单区域 - 确保足够宽以容纳更多菜单项
        self.menu_area = QWidget(self.content_container)
        self.menu_area.setObjectName(u"menu_area")
        self.menu_area.setGeometry(QRect(0, 35, 1280, 30))  # 调整位置从40到35，高度从35到30
        self.menu_area.setStyleSheet("""
            QWidget#menu_area {
                background-color: #E96948;
            }
        """)
        
        # 不再使用菜单栏，改用普通按钮
        # 创建菜单按钮字体
        menu_font = QFont(font_family, 14)  # 进一步减小字体大小到14
        menu_font.setBold(True)
        
        # 设置按钮
        self.settings_btn = QPushButton("设置", self.menu_area)
        self.settings_btn.setObjectName(u"settings_btn")
        self.settings_btn.setGeometry(QRect(20, 1, 80, 28))  # 调整高度和Y位置
        self.settings_btn.setFont(menu_font)
        self.settings_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton:hover {
                background-color: #F47A5B;
                border-radius: 4px;
            }
            QPushButton:pressed {
                background-color: #D25A3C;
                border-radius: 4px;
            }
        """)
        
        # 帮助按钮
        self.help_btn = QPushButton("帮助", self.menu_area)
        self.help_btn.setObjectName(u"help_btn")
        self.help_btn.setGeometry(QRect(120, 1, 80, 28))  # 调整高度和Y位置
        self.help_btn.setFont(menu_font)
        self.help_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.help_btn.setStyleSheet(self.settings_btn.styleSheet())
        
        # 将原来的菜单项移到全局，方便访问
        self.menu = QMenu(self.content_container)
        self.menu.setObjectName(u"menu")
        self.menu.setTitle("设置")
        self.menu.setFont(menu_font)
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #E96948;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border: 1px solid #F47A5B;
                padding: 8px;
                border-radius: 6px;
                margin-top: 2px;
            }
            QMenu::item {
                padding: 6px 20px 6px 15px;
                background-color: transparent;
                min-width: 120px;
                color: white;
            }
            QMenu::item:selected {
                background-color: #F47A5B;
                border-radius: 4px;
            }
            QMenu::separator {
                height: 1px;
                background-color: #F47A5B;
                margin: 5px 15px;
            }
        """)
        
        self.menu_2 = QMenu(self.content_container)
        self.menu_2.setObjectName(u"menu_2")
        self.menu_2.setTitle("帮助")
        self.menu_2.setFont(menu_font)
        self.menu_2.setStyleSheet(self.menu.styleSheet())
        
        # 连接按钮点击事件到显示对应菜单
        self.settings_btn.clicked.connect(lambda: self.show_menu(self.menu, self.settings_btn))
        self.help_btn.clicked.connect(lambda: self.show_menu(self.menu_2, self.help_btn))
        
        # 预留位置给未来可能的第三个按钮
        # 第三个按钮可以这样添加:
        # self.third_btn = QPushButton("第三项", self.menu_area)
        # self.third_btn.setObjectName(u"third_btn")
        # self.third_btn.setGeometry(QRect(320, 0, 120, 35))
        # self.third_btn.setFont(menu_font)
        # self.third_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # self.third_btn.setStyleSheet(self.settings_btn.styleSheet())
        # self.third_btn.clicked.connect(lambda: self.show_menu(self.menu_3, self.third_btn))
        
        # 内容子容器
        self.inner_content = QWidget(self.content_container)
        self.inner_content.setObjectName(u"inner_content")
        # 确保宽度足够大，保证右侧元素完全显示
        self.inner_content.setGeometry(QRect(0, 65, 1280, 655))  # 调整Y位置从75到65，高度从645到655
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

        # 在主容器中添加背景和内容元素
        # 修改loadbg使用title_bg1.png作为整个背景
        # 原来的loadbg保持不变
        self.loadbg = QLabel(self.inner_content)
        self.loadbg.setObjectName(u"loadbg")
        self.loadbg.setGeometry(QRect(0, 0, 1280, 655))  # 调整高度从645到655
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
        self.Mainbg.setGeometry(QRect(0, 0, 1280, 655))  # 调整高度从645到655
        self.Mainbg.setPixmap(load_image_from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "IMG", "BG", "title_bg1.png")))
        self.Mainbg.setScaledContents(True)
        
        # 使用新的按钮图片
        button_pixmap = load_image_from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "IMG", "BTN", "Button.png"))
        
        # 创建文本标签布局的按钮
        # 开始安装按钮 - 基于背景图片和标签组合
        # 调整开始安装按钮的位置
        self.button_container = QWidget(self.inner_content)
        self.button_container.setObjectName(u"start_install_container")
        self.button_container.setGeometry(QRect(1050, 200, 211, 111))  # 调整Y坐标，上移至200
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

        # 添加卸载补丁按钮 - 新增
        self.uninstall_container = QWidget(self.inner_content)
        self.uninstall_container.setObjectName(u"uninstall_container")
        self.uninstall_container.setGeometry(QRect(1050, 310, 211, 111))  # 调整Y坐标，位于310位置

        # 使用相同的按钮背景图片
        self.uninstall_bg = QLabel(self.uninstall_container)
        self.uninstall_bg.setObjectName(u"uninstall_bg")
        self.uninstall_bg.setGeometry(QRect(10, 10, 191, 91))  # 居中放置在扩大的容器中
        self.uninstall_bg.setPixmap(button_pixmap)
        self.uninstall_bg.setScaledContents(True)

        self.uninstall_text = QLabel(self.uninstall_container)
        self.uninstall_text.setObjectName(u"uninstall_text")
        self.uninstall_text.setGeometry(QRect(10, 7, 191, 91))  # 居中放置在扩大的容器中
        self.uninstall_text.setText("卸载补丁")
        self.uninstall_text.setFont(self.custom_font)
        self.uninstall_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.uninstall_text.setStyleSheet("letter-spacing: 1px;")

        # 点击区域透明按钮
        self.uninstall_btn = QPushButton(self.uninstall_container)
        self.uninstall_btn.setObjectName(u"uninstall_btn")
        self.uninstall_btn.setGeometry(QRect(10, 10, 191, 91))  # 居中放置在扩大的容器中
        self.uninstall_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))  # 设置鼠标悬停时为手形光标
        self.uninstall_btn.setFlat(True)
        self.uninstall_btn.raise_()  # 确保按钮在最上层
        self.uninstall_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
        """)
        
        # 退出按钮 - 基于背景图片和标签组合，调整位置
        self.exit_container = QWidget(self.inner_content)
        self.exit_container.setObjectName(u"exit_container")
        self.exit_container.setGeometry(QRect(1050, 420, 211, 111))  # 调整Y坐标，下移至420
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
        
        MainWindows.setCentralWidget(self.centralwidget)
        
        # 调整层级顺序
        self.loadbg.raise_()
        self.vol1bg.raise_()
        self.vol2bg.raise_()
        self.vol3bg.raise_()
        self.vol4bg.raise_()
        self.afterbg.raise_()
        self.Mainbg.raise_()
        self.button_container.raise_()
        self.uninstall_container.raise_()  # 添加新按钮到层级顺序
        self.exit_container.raise_()
        self.menu_area.raise_()  # 确保菜单区域在背景之上
        # self.menubar.raise_()  # 不再需要菜单栏
        self.settings_btn.raise_()  # 确保设置按钮在上层
        self.help_btn.raise_()  # 确保帮助按钮在上层
        self.title_bar.raise_()  # 确保标题栏在最上层
        
        self.retranslateUi(MainWindows)

        QMetaObject.connectSlotsByName(MainWindows)
    # setupUi

    def retranslateUi(self, MainWindows):
        MainWindows.setWindowTitle(QCoreApplication.translate("MainWindows", f"{APP_NAME} v{APP_VERSION}", None))
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
        self.menu.setTitle(QCoreApplication.translate("MainWindows", u"设置", None))
        self.menu_2.setTitle(QCoreApplication.translate("MainWindows", u"帮助", None))
    # retranslateUi

    def show_menu(self, menu, button):
        """显示菜单
        
        Args:
            menu: 要显示的菜单
            button: 触发菜单的按钮
        """
        # 计算菜单显示位置
        pos = button.mapToGlobal(button.rect().bottomLeft())
        menu.exec(pos)

