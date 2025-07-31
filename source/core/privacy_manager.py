#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QPushButton, QCheckBox, QLabel, QMessageBox
from PySide6.QtCore import Qt

from data.privacy_policy import PRIVACY_POLICY_BRIEF
from data.config import CACHE, APP_NAME
from utils import msgbox_frame

class PrivacyManager:
    """隐私协议管理器，负责显示隐私协议对话框并处理用户选择"""
    
    def __init__(self):
        """初始化隐私协议管理器"""
        # 确保缓存目录存在
        os.makedirs(CACHE, exist_ok=True)
        self.config_file = os.path.join(CACHE, "privacy_config.json")
        self.privacy_accepted = self._load_privacy_config()
        
    def _load_privacy_config(self):
        """加载隐私协议配置
        
        Returns:
            bool: 用户是否已同意隐私协议
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config.get("privacy_accepted", False)
            except (json.JSONDecodeError, IOError) as e:
                print(f"读取隐私配置失败: {e}")
                # 如果读取失败，返回False，强制显示隐私协议
                return False
        return False
        
    def _save_privacy_config(self, accepted):
        """保存隐私协议配置
        
        Args:
            accepted: 用户是否同意隐私协议
            
        Returns:
            bool: 配置是否保存成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # 写入配置文件
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({
                    "privacy_accepted": accepted,
                    "version": "1.0"  # 添加版本号，便于将来升级隐私协议时使用
                }, f, indent=2)
                
            # 更新实例变量
            self.privacy_accepted = accepted
            return True
        except IOError as e:
            print(f"保存隐私协议配置失败: {e}")
            # 显示保存失败的提示
            QMessageBox.warning(
                None,
                f"配置保存警告 - {APP_NAME}",
                f"隐私设置无法保存到配置文件，下次启动时可能需要重新确认。\n\n错误信息：{e}"
            )
            return False
    
    def show_privacy_dialog(self):
        """显示隐私协议对话框
        
        Returns:
            bool: 用户是否同意隐私协议
        """
        # 如果用户已经同意了隐私协议，直接返回True不显示对话框
        if self.privacy_accepted:
            print("用户已同意隐私协议，无需再次显示")
            return True
            
        print("首次运行或用户未同意隐私协议，显示隐私对话框")
            
        # 创建隐私协议对话框
        dialog = QDialog()
        dialog.setWindowTitle(f"隐私政策 - {APP_NAME}")
        dialog.setMinimumSize(600, 400)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # 创建布局
        layout = QVBoxLayout(dialog)
        
        # 添加标题
        title_label = QLabel("请阅读并同意以下隐私政策")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 添加隐私协议文本框
        text_browser = QTextBrowser()
        text_browser.setMarkdown(PRIVACY_POLICY_BRIEF)
        text_browser.setOpenExternalLinks(True)
        layout.addWidget(text_browser)
        
        # 添加同意选择框
        checkbox = QCheckBox("我已阅读并同意上述隐私政策")
        layout.addWidget(checkbox)
        
        # 添加按钮
        buttons_layout = QHBoxLayout()
        agree_button = QPushButton("同意并继续")
        agree_button.setEnabled(False)  # 初始状态为禁用
        decline_button = QPushButton("不同意并退出")
        buttons_layout.addWidget(agree_button)
        buttons_layout.addWidget(decline_button)
        layout.addLayout(buttons_layout)
        
        # 连接选择框状态变化 - 修复勾选后按钮不亮起的问题
        def on_checkbox_state_changed(state):
            print(f"复选框状态变更为: {state}")
            agree_button.setEnabled(state == 2)  # Qt.Checked 在 PySide6 中值为 2
            
        checkbox.stateChanged.connect(on_checkbox_state_changed)
        
        # 连接按钮点击事件
        agree_button.clicked.connect(lambda: self._on_agree(dialog))
        decline_button.clicked.connect(lambda: self._on_decline(dialog))
        
        # 显示对话框
        result = dialog.exec()
        
        # 返回用户选择结果
        return self.privacy_accepted
        
    def _on_agree(self, dialog):
        """处理用户同意隐私协议
        
        Args:
            dialog: 对话框实例
        """
        # 保存配置并更新状态
        self._save_privacy_config(True)
        dialog.accept()
        
    def _on_decline(self, dialog):
        """处理用户拒绝隐私协议
        
        Args:
            dialog: 对话框实例
        """
        # 显示拒绝信息
        msg_box = msgbox_frame(
            f"退出 - {APP_NAME}",
            "\n您需要同意隐私政策才能使用本软件。\n软件将立即退出。\n",
            QMessageBox.Ok,
        )
        msg_box.exec()
        
        # 保存拒绝状态
        self._save_privacy_config(False)
        dialog.reject()
        
    def is_privacy_accepted(self):
        """检查用户是否已同意隐私协议
        
        Returns:
            bool: 用户是否已同意隐私协议
        """
        return self.privacy_accepted
        
    def reset_privacy_agreement(self):
        """重置隐私协议同意状态，用于测试或重新显示隐私协议
        
        Returns:
            bool: 重置是否成功
        """
        return self._save_privacy_config(False) 