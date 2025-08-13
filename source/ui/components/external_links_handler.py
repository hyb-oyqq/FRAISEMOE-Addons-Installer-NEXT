"""
外部链接处理器
负责处理所有外部链接打开和关于信息显示
"""

import webbrowser
import locale
import sys
import subprocess
import os
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt

from config.config import APP_NAME, APP_VERSION
from utils import msgbox_frame


class ExternalLinksHandler:
    """外部链接处理器类"""
    
    def __init__(self, main_window, dialog_factory=None):
        """初始化外部链接处理器
        
        Args:
            main_window: 主窗口实例
            dialog_factory: 对话框工厂实例
        """
        self.main_window = main_window
        self.dialog_factory = dialog_factory
    
    def open_project_home_page(self):
        """打开项目主页"""
        webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT")
        
    def open_github_page(self):
        """打开项目GitHub页面"""
        webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT")
    
    def open_faq_page(self):
        """打开常见问题页面"""
        # 根据系统语言选择FAQ页面
        system_lang = locale.getdefaultlocale()[0]
        if system_lang and system_lang.startswith('zh'):
            webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT/blob/master/FAQ.md")
        else:
            webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT/blob/master/FAQ-en.md")
    
    def open_issues_page(self):
        """打开GitHub问题页面"""
        webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT/issues")
    
    def open_qq_group(self):
        """打开QQ群链接"""
        webbrowser.open("https://qm.qq.com/q/g9i04i5eec")
        
    def open_privacy_policy(self):
        """打开完整隐私协议（在GitHub上）"""
        webbrowser.open("https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT/blob/master/PRIVACY.md")

    def show_about_dialog(self):
        """显示关于对话框"""
        about_text = f"""
            <p><b>{APP_NAME} v{APP_VERSION}</b></p>
            <p>GitHub: <a href="https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT">https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT</a></p>
            <p>原作: <a href="https://github.com/Yanam1Anna">Yanam1Anna</a></p>
            <p>此应用根据 <a href="https://github.com/hyb-oyqq/FRAISEMOE-Addons-Installer-NEXT/blob/master/LICENSE">GPL-3.0 许可证</a> 授权。</p>
            <br>
            <p><b>感谢:</b></p>
            <p>- <a href="https://github.com/HTony03">HTony03</a>：对原项目部分源码的重构、逻辑优化和功能实现提供了支持。</p>
            <p>- <a href="https://github.com/ABSIDIA">钨鸮</a>：对于云端资源存储提供了支持。</p>
            <p>- <a href="https://github.com/XIU2/CloudflareSpeedTest">XIU2/CloudflareSpeedTest</a>：提供了 IP 优选功能的核心支持。</p>
            <p>- <a href="https://github.com/hosxy/aria2-fast">hosxy/aria2-fast</a>：提供了修改版aria2c，提高了下载速度和性能。</p>
        """
        msg_box = msgbox_frame(
            f"关于 - {APP_NAME}",
            about_text,
            QMessageBox.StandardButton.Ok,
        )
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.exec()

    def revoke_privacy_agreement(self):
        """撤回隐私协议同意，并重启软件"""
        # 创建确认对话框
        if self.dialog_factory:
            response = self.dialog_factory.show_confirmation_dialog(
                "确认操作",
                "\n您确定要撤回隐私协议同意吗？\n\n撤回后软件将立即重启，您需要重新阅读并同意隐私协议。\n"
            )
        else:
            msg_box = msgbox_frame(
                f"确认操作 - {APP_NAME}",
                "\n您确定要撤回隐私协议同意吗？\n\n撤回后软件将立即重启，您需要重新阅读并同意隐私协议。\n",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            response = msg_box.exec() == QMessageBox.StandardButton.Yes
        
        if response:
            try:
                from core.managers.privacy_manager import PrivacyManager
                
                privacy_manager = PrivacyManager()
                if privacy_manager.reset_privacy_agreement():
                    # 显示重启提示
                    if self.dialog_factory:
                        self.dialog_factory.show_simple_message(
                            "操作成功",
                            "\n已成功撤回隐私协议同意。\n\n软件将立即重启。\n"
                        )
                    else:
                        restart_msg = msgbox_frame(
                            f"操作成功 - {APP_NAME}",
                            "\n已成功撤回隐私协议同意。\n\n软件将立即重启。\n",
                            QMessageBox.StandardButton.Ok
                        )
                        restart_msg.exec()
                    
                    # 重启应用程序
                    python_executable = sys.executable
                    script_path = os.path.abspath(sys.argv[0])
                    subprocess.Popen([python_executable, script_path])
                    sys.exit(0)
                else:
                    if self.dialog_factory:
                        self.dialog_factory.show_simple_message(
                            "操作失败",
                            "\n撤回隐私协议同意失败。\n\n请检查应用权限或稍后再试。\n",
                            "error"
                        )
                    else:
                        msgbox_frame(
                            f"操作失败 - {APP_NAME}",
                            "\n撤回隐私协议同意失败。\n\n请检查应用权限或稍后再试。\n",
                            QMessageBox.StandardButton.Ok
                        ).exec()
            except Exception as e:
                error_message = f"\n撤回隐私协议同意时发生错误：\n\n{str(e)}\n"
                if self.dialog_factory:
                    self.dialog_factory.show_simple_message("错误", error_message, "error")
                else:
                    msgbox_frame(
                        f"错误 - {APP_NAME}",
                        error_message,
                        QMessageBox.StandardButton.Ok
                    ).exec()