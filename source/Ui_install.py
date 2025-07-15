# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'install.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################
from pic_data import img_data
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
def load_base64_image(base64_str):
    pixmap = QPixmap()
    pixmap.loadFromData(base64.b64decode(base64_str))
    return pixmap


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
        self.action_2 = QAction(MainWindows)
        self.action_2.setObjectName(u"action_2")
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
        self.start_install_btn = QPushButton(self.centralwidget)
        self.start_install_btn.setObjectName(u"start_install_btn")
        self.start_install_btn.setEnabled(True)
        self.start_install_btn.setGeometry(QRect(780, 250, 191, 91))
        self.start_install_btn.setAutoFillBackground(False)
        start_install_icon = QIcon()
        start_install_pixmap = load_base64_image(img_data["start_install_btn"])
        if not start_install_pixmap.isNull():
            start_install_icon.addPixmap(start_install_pixmap)
            self.start_install_btn.setIcon(start_install_icon)
        self.start_install_btn.setIcon(start_install_icon)
        self.start_install_btn.setIconSize(QSize(189, 110))
        self.start_install_btn.setCheckable(False)
        self.start_install_btn.setAutoRepeat(False)
        self.start_install_btn.setAutoDefault(False)
        self.start_install_btn.setFlat(True)
        self.exit_btn = QPushButton(self.centralwidget)
        self.exit_btn.setObjectName(u"exit_btn")
        self.exit_btn.setEnabled(True)
        self.exit_btn.setGeometry(QRect(780, 340, 191, 91))
        self.exit_btn.setAutoFillBackground(False)
        exit_icon = QIcon()
        exit_pixmap = load_base64_image(img_data["exit_btn"])
        if not exit_pixmap.isNull():
            exit_icon.addPixmap(exit_pixmap)
            self.exit_btn.setIcon(exit_icon)
        self.exit_btn.setIcon(exit_icon)
        self.exit_btn.setIconSize(QSize(189, 110))
        self.exit_btn.setCheckable(False)
        self.exit_btn.setFlat(True)
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
        self.start_install_btn.raise_()
        self.exit_btn.raise_()
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
        self.menu.addAction(self.action_2)

        self.retranslateUi(MainWindows)

        QMetaObject.connectSlotsByName(MainWindows)
    # setupUi

    def retranslateUi(self, MainWindows):
        MainWindows.setWindowTitle(QCoreApplication.translate("MainWindows", u" UI Test", None))
        self.action_2.setText(QCoreApplication.translate("MainWindows", u"\u68c0\u67e5\u66f4\u65b0(\u672a\u5b8c\u6210)", None))
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
        self.start_install_btn.setText("")
        self.exit_btn.setText("")
        self.menubg.setText("")
        self.menu.setTitle(QCoreApplication.translate("MainWindows", u"\u8bbe\u7f6e", None))
        self.menu_2.setTitle(QCoreApplication.translate("MainWindows", u"\u5173\u4e8e", None))
    # retranslateUi

