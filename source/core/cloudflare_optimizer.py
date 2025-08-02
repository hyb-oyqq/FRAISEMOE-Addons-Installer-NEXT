import os
from urllib.parse import urlparse
from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap

from utils import msgbox_frame, resource_path
from workers import IpOptimizerThread


class CloudflareOptimizer:
    """Cloudflare IP优化器，负责处理IP优化和Cloudflare加速相关功能"""
    
    def __init__(self, main_window, hosts_manager):
        """初始化Cloudflare优化器
        
        Args:
            main_window: 主窗口实例，用于访问UI和状态
            hosts_manager: Hosts文件管理器实例
        """
        self.main_window = main_window
        self.hosts_manager = hosts_manager
        self.optimized_ip = None
        self.optimized_ipv6 = None
        self.optimization_done = False  # 标记是否已执行过优选
        self.countdown_finished = False # 标记倒计时是否结束
        self.optimizing_msg_box = None
        self.optimization_cancelled = False
        self.ip_optimizer_thread = None
        self.ipv6_optimizer_thread = None
        
    def is_optimization_done(self):
        """检查是否已完成优化
        
        Returns:
            bool: 是否已完成优化
        """
        return self.optimization_done
    
    def is_countdown_finished(self):
        """检查倒计时是否已完成
        
        Returns:
            bool: 倒计时是否已完成
        """
        return self.countdown_finished
        
    def get_optimized_ip(self):
        """获取优选的IP地址
        
        Returns:
            str: 优选的IP地址，如果未优选则为None
        """
        return self.optimized_ip
        
    def get_optimized_ipv6(self):
        """获取优选的IPv6地址
        
        Returns:
            str: 优选的IPv6地址，如果未优选则为None
        """
        return self.optimized_ipv6

    def start_ip_optimization(self, url):
        """开始IP优化过程
        
        Args:
            url: 用于优化的URL
        """
        # 创建取消状态标记
        self.optimization_cancelled = False
        self.countdown_finished = False
        
        # 检查是否启用了IPv6
        use_ipv6 = False
        if hasattr(self.main_window, 'config'):
            use_ipv6 = self.main_window.config.get("ipv6_enabled", False)
        
        # 如果启用了IPv6，显示警告消息
        if use_ipv6:
            ipv6_warning = QtWidgets.QMessageBox(self.main_window)
            ipv6_warning.setWindowTitle(f"IPv6优选警告 - {self.main_window.APP_NAME}")
            ipv6_warning.setText("\nIPv6优选比IPv4耗时更长且感知不强（预计耗时10分钟以上），不建议使用。\n\n确定要同时执行IPv6优选吗？\n")
            ipv6_warning.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            
            # 设置图标
            icon_path = resource_path(os.path.join("IMG", "ICO", "icon.png"))
            if os.path.exists(icon_path):
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    ipv6_warning.setWindowIcon(QIcon(pixmap))
            
            yes_button = ipv6_warning.addButton("是", QtWidgets.QMessageBox.ButtonRole.YesRole)
            no_button = ipv6_warning.addButton("否，仅使用IPv4", QtWidgets.QMessageBox.ButtonRole.NoRole)
            cancel_button = ipv6_warning.addButton("取消优选", QtWidgets.QMessageBox.ButtonRole.RejectRole)
            
            ipv6_warning.setDefaultButton(no_button)
            ipv6_warning.exec()
            
            if ipv6_warning.clickedButton() == cancel_button:
                # 用户取消了优选
                self.optimization_cancelled = True
                return
                
            # 根据用户选择调整IPv6设置
            if ipv6_warning.clickedButton() == no_button:
                use_ipv6 = False
                # 临时覆盖配置（不保存到文件）
                if hasattr(self.main_window, 'config'):
                    self.main_window.config["ipv6_enabled"] = False
        
        # 准备提示信息
        optimization_msg = "\n正在优选Cloudflare IP，请稍候...\n\n"
        if use_ipv6:
            optimization_msg += "已启用IPv6支持，同时进行IPv4和IPv6优选。\n这可能需要10分钟以上，请耐心等待喵~\n"
        else:
            optimization_msg += "这可能需要5-10分钟，请耐心等待喵~\n"
            
        # 使用Cloudflare图标创建消息框
        self.optimizing_msg_box = msgbox_frame(
            f"通知 - {self.main_window.APP_NAME}",
            optimization_msg
        )
        # 设置Cloudflare图标
        cf_icon_path = resource_path("IMG/ICO/cloudflare_logo_icon.ico")
        if os.path.exists(cf_icon_path):
            cf_pixmap = QPixmap(cf_icon_path)
            if not cf_pixmap.isNull():
                self.optimizing_msg_box.setWindowIcon(QIcon(cf_pixmap))
                self.optimizing_msg_box.setIconPixmap(cf_pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, 
                                                             Qt.TransformationMode.SmoothTransformation))
        
        # 添加取消按钮
        self.optimizing_msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Cancel)
        self.optimizing_msg_box.buttonClicked.connect(self._on_optimization_dialog_clicked)
        self.optimizing_msg_box.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        # 创建并启动优化线程
        self.ip_optimizer_thread = IpOptimizerThread(url)
        self.ip_optimizer_thread.finished.connect(self.on_ipv4_optimization_finished)
        
        # 如果启用IPv6，同时启动IPv6优化线程
        if use_ipv6:
            print("IPv6已启用，将同时优选IPv6地址")
            self.ipv6_optimizer_thread = IpOptimizerThread(url, use_ipv6=True)
            self.ipv6_optimizer_thread.finished.connect(self.on_ipv6_optimization_finished)
            self.ipv6_optimizer_thread.start()
            
        # 启动IPv4优化线程
        self.ip_optimizer_thread.start()
        
        # 显示消息框（非模态，不阻塞）
        self.optimizing_msg_box.open()
        
    def _on_optimization_dialog_clicked(self, button):
        """处理优化对话框按钮点击
        
        Args:
            button: 被点击的按钮
        """
        if button.text() == "Cancel":  # 如果是取消按钮
            # 标记已取消
            self.optimization_cancelled = True
            
            # 停止优化线程
            if hasattr(self, 'ip_optimizer_thread') and self.ip_optimizer_thread and self.ip_optimizer_thread.isRunning():
                self.ip_optimizer_thread.stop()
                
            if hasattr(self, 'ipv6_optimizer_thread') and self.ipv6_optimizer_thread and self.ipv6_optimizer_thread.isRunning():
                self.ipv6_optimizer_thread.stop()
                
            # 恢复主窗口状态
            self.main_window.setEnabled(True)
            self.main_window.ui.start_install_text.setText("开始安装")
            
            # 显示取消消息
            QtWidgets.QMessageBox.information(
                self.main_window,
                f"已取消 - {self.main_window.APP_NAME}",
                "\n已取消IP优选和安装过程。\n"
            )
            
    def on_ipv4_optimization_finished(self, ip):
        """IPv4优化完成后的处理
        
        Args:
            ip: 优选的IP地址，如果失败则为空字符串
        """
        # 如果已经取消，则不继续处理
        if hasattr(self, 'optimization_cancelled') and self.optimization_cancelled:
            return
            
        self.optimized_ip = ip
        print(f"IPv4优选完成，结果: {ip if ip else '未找到合适的IP'}")
        
        # 检查是否还有IPv6优化正在运行
        if hasattr(self, 'ipv6_optimizer_thread') and self.ipv6_optimizer_thread and self.ipv6_optimizer_thread.isRunning():
            print("等待IPv6优选完成...")
            return
        
        # 所有优选都已完成，继续处理
        self.optimization_done = True
        self.countdown_finished = False  # 确保倒计时标志重置
        
        # 关闭提示框
        if hasattr(self, 'optimizing_msg_box') and self.optimizing_msg_box:
            if self.optimizing_msg_box.isVisible():
                self.optimizing_msg_box.accept()
            self.optimizing_msg_box = None
        
        # 处理优选结果
        self._process_optimization_results()
            
    def on_ipv6_optimization_finished(self, ipv6):
        """IPv6优化完成后的处理
        
        Args:
            ipv6: 优选的IPv6地址，如果失败则为空字符串
        """
        # 如果已经取消，则不继续处理
        if hasattr(self, 'optimization_cancelled') and self.optimization_cancelled:
            return
            
        self.optimized_ipv6 = ipv6
        print(f"IPv6优选完成，结果: {ipv6 if ipv6 else '未找到合适的IPv6'}")
        
        # 检查IPv4优化是否已完成
        if hasattr(self, 'ip_optimizer_thread') and self.ip_optimizer_thread and self.ip_optimizer_thread.isRunning():
            print("等待IPv4优选完成...")
            return
            
        # 所有优选都已完成，继续处理
        self.optimization_done = True
        self.countdown_finished = False  # 确保倒计时标志重置
        
        # 关闭提示框
        if hasattr(self, 'optimizing_msg_box') and self.optimizing_msg_box:
            if self.optimizing_msg_box.isVisible():
                self.optimizing_msg_box.accept()
            self.optimizing_msg_box = None
        
        # 处理优选结果
        self._process_optimization_results()
    
    def _process_optimization_results(self):
        """处理优选的IP结果，显示相应提示"""
        use_ipv6 = False
        if hasattr(self.main_window, 'config'):
            use_ipv6 = self.main_window.config.get("ipv6_enabled", False)
            
        # 判断优选结果
        ipv4_success = bool(self.optimized_ip)
        ipv6_success = bool(self.optimized_ipv6) if use_ipv6 else False
        
        # 临时启用窗口以显示对话框
        self.main_window.setEnabled(True)
        
        hostname = urlparse(self.main_window.current_url).hostname if hasattr(self.main_window, 'current_url') else None
        
        if not ipv4_success and (not use_ipv6 or not ipv6_success):
            # 两种IP都没有优选成功
            msg_box = QtWidgets.QMessageBox(self.main_window)
            msg_box.setWindowTitle(f"优选失败 - {self.main_window.APP_NAME}")
            
            fail_message = "\n未能找到合适的Cloudflare "
            if use_ipv6:
                fail_message += "IPv4和IPv6地址"
            else:
                fail_message += "IP地址"
                
            fail_message += "，将使用默认网络进行下载。\n\n10秒后自动继续..."
            
            msg_box.setText(fail_message)
            msg_box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            ok_button = msg_box.addButton("确定 (10)", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
            cancel_button = msg_box.addButton("取消安装", QtWidgets.QMessageBox.ButtonRole.RejectRole)
            
            # 创建计时器实现倒计时
            countdown = 10
            timer = QTimer(self.main_window)
            
            def update_countdown():
                nonlocal countdown
                countdown -= 1
                ok_button.setText(f"确定 ({countdown})")
                if countdown <= 0:
                    timer.stop()
                    if msg_box.isVisible():
                        msg_box.accept()
            
            timer.timeout.connect(update_countdown)
            timer.start(1000)  # 每秒更新一次
            
            # 显示对话框并等待用户响应
            result = msg_box.exec()
            
            # 停止计时器
            timer.stop()
            
            # 如果用户点击了取消安装
            if msg_box.clickedButton() == cancel_button:
                # 恢复主窗口状态
                self.main_window.setEnabled(True)
                self.main_window.ui.start_install_text.setText("开始安装")
                return False
                
            # 用户点击了继续，重新禁用主窗口
            self.main_window.setEnabled(False)
            # 标记倒计时已完成
            self.countdown_finished = True
            return True
        else:
            # 至少有一种IP优选成功
            success_message = ""
            if ipv4_success:
                success_message += f"IPv4: {self.optimized_ip}\n"
                
            if ipv6_success:
                success_message += f"IPv6: {self.optimized_ipv6}\n"
                
            if hostname:
                # 先清理可能存在的旧记录（只清理一次）
                self.hosts_manager.clean_hostname_entries(hostname)
                
                success = False
                
                # 应用优选IP到hosts文件
                if ipv4_success:
                    success = self.hosts_manager.apply_ip(hostname, self.optimized_ip, clean=False) or success
                    
                # 如果启用IPv6并且找到了IPv6地址，也应用到hosts
                if ipv6_success:
                    success = self.hosts_manager.apply_ip(hostname, self.optimized_ipv6, clean=False) or success
                
                if success:
                    msg_box = QtWidgets.QMessageBox(self.main_window)
                    msg_box.setWindowTitle(f"成功 - {self.main_window.APP_NAME}")
                    msg_box.setText(f"\n已将优选IP应用到hosts文件：\n{success_message}\n10秒后自动继续...")
                    msg_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
                    ok_button = msg_box.addButton("确定 (10)", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
                    cancel_button = msg_box.addButton("取消安装", QtWidgets.QMessageBox.ButtonRole.RejectRole)
                    
                    # 创建计时器实现倒计时
                    countdown = 10
                    timer = QTimer(self.main_window)
                    
                    def update_countdown():
                        nonlocal countdown
                        countdown -= 1
                        ok_button.setText(f"确定 ({countdown})")
                        if countdown <= 0:
                            timer.stop()
                            if msg_box.isVisible():
                                msg_box.accept()
                    
                    timer.timeout.connect(update_countdown)
                    timer.start(1000)  # 每秒更新一次
                    
                    # 显示对话框并等待用户响应
                    result = msg_box.exec()
                    
                    # 停止计时器
                    timer.stop()
                    
                    # 如果用户点击了取消安装
                    if msg_box.clickedButton() == cancel_button:
                        # 恢复主窗口状态
                        self.main_window.setEnabled(True)
                        self.main_window.ui.start_install_text.setText("开始安装")
                        return False
                else:
                    QtWidgets.QMessageBox.critical(
                        self.main_window, 
                        f"错误 - {self.main_window.APP_NAME}", 
                        "\n修改hosts文件失败，请检查程序是否以管理员权限运行。\n"
                    )
                    # 恢复主窗口状态
                    self.main_window.ui.start_install_text.setText("开始安装")
                    return False
                
                # 用户点击了继续，重新禁用主窗口
                self.main_window.setEnabled(False)
                # 标记倒计时已完成
                self.countdown_finished = True
                
            return True
            
    def stop_optimization(self):
        """停止正在进行的IP优化"""
        if hasattr(self, 'ip_optimizer_thread') and self.ip_optimizer_thread and self.ip_optimizer_thread.isRunning():
            self.ip_optimizer_thread.stop()
            self.ip_optimizer_thread.wait()
            
        if hasattr(self, 'ipv6_optimizer_thread') and self.ipv6_optimizer_thread and self.ipv6_optimizer_thread.isRunning():
            self.ipv6_optimizer_thread.stop()
            self.ipv6_optimizer_thread.wait()
            
        if hasattr(self, 'optimizing_msg_box') and self.optimizing_msg_box:
            if self.optimizing_msg_box.isVisible():
                self.optimizing_msg_box.accept()
            self.optimizing_msg_box = None 