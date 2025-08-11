#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QPushButton, QCheckBox, QLabel, QMessageBox
from PySide6.QtCore import Qt

from data.privacy_policy import PRIVACY_POLICY_BRIEF, get_local_privacy_policy, PRIVACY_POLICY_VERSION
from data.config import CACHE, APP_NAME, APP_VERSION
from utils import msgbox_frame
from utils.logger import setup_logger

class PrivacyManager:
    """隐私协议管理器，负责显示隐私协议对话框并处理用户选择"""
    
    def __init__(self):
        """初始化隐私协议管理器"""
        # 初始化日志
        self.logger = setup_logger("privacy_manager")
        self.logger.info("正在初始化隐私协议管理器")
        # 确保缓存目录存在
        os.makedirs(CACHE, exist_ok=True)
        self.config_file = os.path.join(CACHE, "privacy_config.json")
        self.privacy_config = self._load_privacy_config()
        
        # 获取隐私协议内容和版本
        self.logger.info("读取本地隐私协议文件")
        self.privacy_content, self.current_privacy_version, error = get_local_privacy_policy()
        if error:
            self.logger.warning(f"读取本地隐私协议文件警告: {error}")
            # 使用默认版本作为备用
            self.current_privacy_version = PRIVACY_POLICY_VERSION
        self.logger.info(f"隐私协议版本: {self.current_privacy_version}")
            
        # 检查隐私协议版本和用户同意状态
        self.privacy_accepted = self._check_privacy_acceptance()
        
    def _load_privacy_config(self):
        """加载隐私协议配置
        
        Returns:
            dict: 隐私协议配置信息
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"读取隐私配置失败: {e}")
                # 如果读取失败，返回空配置，强制显示隐私协议
                return {"privacy_accepted": False}
        return {"privacy_accepted": False}
    
    def _check_privacy_acceptance(self):
        """检查隐私协议是否需要重新同意
        
        如果隐私协议版本变更，则需要重新同意
        
        Returns:
            bool: 是否已有有效的隐私协议同意
        """
        # 获取存储的版本信息
        stored_privacy_version = self.privacy_config.get("privacy_version", "0.0.0")
        stored_app_version = self.privacy_config.get("app_version", "0.0.0")
        privacy_accepted = self.privacy_config.get("privacy_accepted", False)
        
        self.logger.info(f"存储的隐私协议版本: {stored_privacy_version}, 当前版本: {self.current_privacy_version}")
        self.logger.info(f"存储的应用版本: {stored_app_version}, 当前版本: {APP_VERSION}")
        self.logger.info(f"隐私协议接受状态: {privacy_accepted}")
        
        # 如果隐私协议版本变更，需要重新同意
        if stored_privacy_version != self.current_privacy_version:
            self.logger.info("隐私协议版本已变更，需要重新同意")
            return False
            
        # 返回当前的同意状态
        return privacy_accepted
        
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
            
            # 写入配置文件，包含应用版本和隐私协议版本
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({
                    "privacy_accepted": accepted,
                    "privacy_version": self.current_privacy_version,  # 保存当前隐私协议版本
                    "app_version": APP_VERSION  # 保存当前应用版本
                }, f, indent=2)
                
            # 更新实例变量
            self.privacy_accepted = accepted
            self.privacy_config = {
                "privacy_accepted": accepted,
                "privacy_version": self.current_privacy_version,
                "app_version": APP_VERSION
            }
            return True
        except IOError as e:
            self.logger.error(f"保存隐私协议配置失败: {e}")
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
            self.logger.info("用户已同意当前版本的隐私协议，无需再次显示")
            return True
            
        self.logger.info("首次运行或隐私协议版本变更，显示隐私对话框")
            
        # 创建隐私协议对话框
        dialog = QDialog()
        dialog.setWindowTitle(f"隐私政策 - {APP_NAME}")
        dialog.setMinimumSize(600, 400)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # 创建布局
        layout = QVBoxLayout(dialog)
        
        # 添加标题和版本信息
        title_label = QLabel(f"请阅读并同意以下隐私政策 (更新日期: {self.current_privacy_version})")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 添加隐私协议文本框
        text_browser = QTextBrowser()
        # 这里使用PRIVACY_POLICY_BRIEF而不是self.privacy_content，保持UI简洁
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
            self.logger.debug(f"复选框状态变更为: {state}")
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