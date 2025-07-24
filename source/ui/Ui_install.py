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
    QTransform)
from PySide6.QtWidgets import (QApplication, QLabel, QMainWindow, QMenu,
    QMenuBar, QPushButton, QSizePolicy, QWidget)
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
        MainWindows.resize(1024, 576)
        MainWindows.setMinimumSize(QSize(1024, 576))
        MainWindows.setMaximumSize(QSize(1024, 576))
        MainWindows.setMouseTracking(False)
        MainWindows.setTabletTracking(False)
        MainWindows.setAcceptDrops(True)
        MainWindows.setAutoFillBackground(True)
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
        self.centralwidget.setAutoFillBackground(True)
        self.loadbg = QLabel(self.centralwidget)
        self.loadbg.setObjectName(u"loadbg")
        self.loadbg.setGeometry(QRect(0, 0, 1031, 561))
        self.loadbg.setPixmap(load_base64_image(img_data["loadbg"]))
        self.loadbg.setScaledContents(True)
        self.vol1bg = QLabel(self.centralwidget)
        self.vol1bg.setObjectName(u"vol1bg")
        self.vol1bg.setGeometry(QRect(0, 120, 93, 64))
        self.vol1bg.setPixmap(load_base64_image(img_data["vol1"]))
        self.vol1bg.setScaledContents(True)
        self.vol2bg = QLabel(self.centralwidget)
        self.vol2bg.setObjectName(u"vol2bg")
        self.vol2bg.setGeometry(QRect(0, 180, 93, 64))
        self.vol2bg.setPixmap(load_base64_image(img_data["vol2"]))
        self.vol2bg.setScaledContents(True)
        self.vol3bg = QLabel(self.centralwidget)
        self.vol3bg.setObjectName(u"vol3bg")
        self.vol3bg.setGeometry(QRect(0, 240, 93, 64))
        self.vol3bg.setPixmap(load_base64_image(img_data["vol3"]))
        self.vol3bg.setScaledContents(True)
        self.vol4bg = QLabel(self.centralwidget)
        self.vol4bg.setObjectName(u"vol4bg")
        self.vol4bg.setGeometry(QRect(0, 300, 93, 64))
        self.vol4bg.setPixmap(load_base64_image(img_data["vol4"]))
        self.vol4bg.setScaledContents(True)
        self.afterbg = QLabel(self.centralwidget)
        self.afterbg.setObjectName(u"afterbg")
        self.afterbg.setGeometry(QRect(0, 360, 93, 64))
        self.afterbg.setPixmap(load_base64_image(img_data["after"]))
        self.afterbg.setScaledContents(True)
        self.Mainbg = QLabel(self.centralwidget)
        self.Mainbg.setObjectName(u"Mainbg")
        self.Mainbg.setGeometry(QRect(0, 0, 1031, 561))
        self.Mainbg.setPixmap(load_base64_image(img_data["Mainbg"]))
        self.Mainbg.setScaledContents(True)
        
        # 使用新的按钮图片
        button_pixmap = load_image_from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "IMG", "BTN", "Button.png"))
        
        # 创建文本标签布局的按钮
        # 开始安装按钮 - 基于背景图片和标签组合
        self.button_container = QWidget(self.centralwidget)
        self.button_container.setObjectName(u"start_install_container")
        self.button_container.setGeometry(QRect(780, 250, 191, 91))
        # 不要隐藏容器，让动画系统来控制它的可见性和位置
        
        self.start_install_bg = QLabel(self.button_container)
        self.start_install_bg.setObjectName(u"start_install_bg")
        self.start_install_bg.setGeometry(QRect(0, 0, 191, 91))
        self.start_install_bg.setPixmap(button_pixmap)
        self.start_install_bg.setScaledContents(True)
        
        self.start_install_text = QLabel(self.button_container)
        self.start_install_text.setObjectName(u"start_install_text")
        self.start_install_text.setGeometry(QRect(0, -3, 191, 91))
        self.start_install_text.setText("开始安装")
        self.start_install_text.setFont(self.custom_font)
        self.start_install_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.start_install_text.setStyleSheet("color: black; letter-spacing: 1px;")
        
        # 点击区域透明按钮
        self.start_install_btn = QPushButton(self.button_container)
        self.start_install_btn.setObjectName(u"start_install_btn")
        self.start_install_btn.setGeometry(QRect(0, 0, 191, 91))
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
        self.exit_container = QWidget(self.centralwidget)
        self.exit_container.setObjectName(u"exit_container")
        self.exit_container.setGeometry(QRect(780, 340, 191, 91))
        # 不要隐藏容器，让动画系统来控制它的可见性和位置
        
        self.exit_bg = QLabel(self.exit_container)
        self.exit_bg.setObjectName(u"exit_bg")
        self.exit_bg.setGeometry(QRect(0, 0, 191, 91))
        self.exit_bg.setPixmap(button_pixmap)
        self.exit_bg.setScaledContents(True)
        
        self.exit_text = QLabel(self.exit_container)
        self.exit_text.setObjectName(u"exit_text")
        self.exit_text.setGeometry(QRect(0, -3, 191, 91))
        self.exit_text.setText("退出")
        self.exit_text.setFont(self.custom_font)
        self.exit_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.exit_text.setStyleSheet("color: black; letter-spacing: 1px;")
        
        # 点击区域透明按钮
        self.exit_btn = QPushButton(self.exit_container)
        self.exit_btn.setObjectName(u"exit_btn")
        self.exit_btn.setGeometry(QRect(0, 0, 191, 91))
        self.exit_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))  # 设置鼠标悬停时为手形光标
        self.exit_btn.setFlat(True)
        self.exit_btn.raise_()  # 确保按钮在最上层
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
        """)
        
        self.menubg = QLabel(self.centralwidget)
        self.menubg.setObjectName(u"menubg")
        self.menubg.setGeometry(QRect(710, 0, 321, 561))
        self.menubg.setPixmap(load_base64_image(img_data["menubg"]))
        self.menubg.setScaledContents(True)
        MainWindows.setCentralWidget(self.centralwidget)
        self.loadbg.raise_()
        self.vol1bg.raise_()
        self.vol2bg.raise_()
        self.vol3bg.raise_()
        self.vol4bg.raise_()
        self.afterbg.raise_()
        self.Mainbg.raise_()
        self.menubg.raise_()
        self.button_container.raise_()
        self.exit_container.raise_()
        self.menubar = QMenuBar(MainWindows)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1024, 21))
        self.menu = QMenu(self.menubar)
        self.menu.setObjectName(u"menu")
        self.menu_2 = QMenu(self.menubar)
        self.menu_2.setObjectName(u"menu_2")
        MainWindows.setMenuBar(self.menubar)

        self.menubar.addAction(self.menu.menuAction())
        self.menubar.addAction(self.menu_2.menuAction())
        self.menu.addSeparator()
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
        # 不再在这里设置文本，因为我们已经在setupUi中设置了
        # self.start_install_btn.setText("")
        # self.exit_btn.setText("")
        self.menubg.setText("")
        self.menu.setTitle(QCoreApplication.translate("MainWindows", u"\u8bbe\u7f6e", None))
        self.menu_2.setTitle(QCoreApplication.translate("MainWindows", u"\u5e2e\u52a9", None))
    # retranslateUi

