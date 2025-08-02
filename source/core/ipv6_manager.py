import os
import sys
import time
import subprocess
import urllib.request
import ssl
import threading
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit, QProgressBar, QMessageBox

from data.config import APP_NAME
from utils import msgbox_frame


class IPv6Manager:
    """管理IPv6相关功能的类"""

    def __init__(self, main_window):
        """初始化IPv6管理器
        
        Args:
            main_window: 主窗口实例，用于显示对话框和访问配置
        """
        self.main_window = main_window
        self.config = getattr(main_window, 'config', {})
        
    def check_ipv6_availability(self):
        """检查IPv6是否可用
        
        通过访问IPv6专用图片URL测试IPv6连接
        
        Returns:
            bool: IPv6是否可用
        """
        import urllib.request
        import time
        
        print("开始检测IPv6可用性...")
        
        try:
            # 获取IPv6测试请求
            ipv6_test_url, req, context = self._get_ipv6_test_request()
            
            # 设置3秒超时，避免长时间等待
            start_time = time.time()
            with urllib.request.urlopen(req, timeout=3, context=context) as response:
                # 读取图片数据
                image_data = response.read()
                
                # 检查是否成功
                if response.status == 200 and len(image_data) > 0:
                    elapsed = time.time() - start_time
                    print(f"IPv6测试成功! 用时: {elapsed:.2f}秒")
                    return True
                else:
                    print(f"IPv6测试失败: 状态码 {response.status}")
                    return False
        except Exception as e:
            print(f"IPv6测试失败: {e}")
            return False
            
    def _get_ipv6_test_request(self):
        """获取IPv6测试请求
        
        Returns:
            tuple: (测试URL, 请求对象, SSL上下文)
        """
        import urllib.request
        import ssl
        
        # IPv6测试URL - 这是一个只能通过IPv6访问的资源
        ipv6_test_url = "https://ipv6.testipv6.cn/images-nc/knob_green.png?&testdomain=www.test-ipv6.com&testname=sites"
        
        # 创建SSL上下文
        context = ssl._create_unverified_context()
        
        # 创建请求并添加常见的HTTP头
        req = urllib.request.Request(ipv6_test_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        req.add_header('Accept', 'image/webp,image/apng,image/*,*/*;q=0.8')
        
        return ipv6_test_url, req, context
        
    def get_ipv6_address(self):
        """获取公网IPv6地址
        
        Returns:
            str: IPv6地址，如果失败则返回None
        """
        try:
            # 使用curl命令获取IPv6地址
            process = subprocess.Popen(
                ["curl", "-6", "6.ipw.cn"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            # 设置超时
            timeout = 5  # 5秒超时
            start_time = time.time()
            while process.poll() is None and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            # 如果进程仍在运行，则强制终止
            if process.poll() is None:
                process.terminate()
                print("获取IPv6地址超时")
                return None
                
            stdout, stderr = process.communicate()
            
            if process.returncode == 0 and stdout.strip():
                ipv6_address = stdout.strip()
                print(f"获取到IPv6地址: {ipv6_address}")
                return ipv6_address
            else:
                print("未能获取到IPv6地址")
                if stderr:
                    print(f"错误信息: {stderr}")
                return None
        
        except Exception as e:
            print(f"获取IPv6地址失败: {e}")
            return None
            
    def show_ipv6_details(self):
        """显示IPv6连接详情"""
        class SignalEmitter(QObject):
            update_signal = Signal(str)
            complete_signal = Signal(bool, float)
        
        # 创建对话框
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle(f"IPv6连接测试 - {APP_NAME}")
        dialog.resize(500, 300)
        
        # 创建布局
        layout = QVBoxLayout(dialog)
        
        # 创建状态标签
        status_label = QLabel("正在测试IPv6连接...", dialog)
        layout.addWidget(status_label)
        
        # 创建进度条
        progress = QProgressBar(dialog)
        progress.setRange(0, 0)  # 不确定进度
        layout.addWidget(progress)
        
        # 创建结果文本框
        result_text = QTextEdit(dialog)
        result_text.setReadOnly(True)
        layout.addWidget(result_text)
        
        # 创建关闭按钮
        close_button = QPushButton("关闭", dialog)
        close_button.clicked.connect(dialog.accept)
        close_button.setEnabled(False)  # 测试完成前禁用
        layout.addWidget(close_button)
        
        # 信号发射器
        signal_emitter = SignalEmitter()
        
        # 连接信号
        signal_emitter.update_signal.connect(
            lambda text: result_text.append(text)
        )
        
        def on_test_complete(success, elapsed_time):
            # 停止进度条动画
            progress.setRange(0, 100)
            progress.setValue(100 if success else 0)
            
            # 更新状态
            if success:
                status_label.setText(f"IPv6连接测试完成: 可用 (用时: {elapsed_time:.2f}秒)")
            else:
                status_label.setText("IPv6连接测试完成: 不可用")
            
            # 启用关闭按钮
            close_button.setEnabled(True)
        
        signal_emitter.complete_signal.connect(on_test_complete)
        
        # 测试函数
        def test_ipv6():
            try:
                signal_emitter.update_signal.emit("正在测试IPv6连接，请稍候...")
                
                # 先进行标准的IPv6连接测试
                signal_emitter.update_signal.emit("正在进行标准IPv6连接测试...")
                
                # 使用IPv6测试URL
                ipv6_test_url, req, context = self._get_ipv6_test_request()
                ipv6_connected = False
                ipv6_test_elapsed_time = 0
                
                try:
                    # 设置5秒超时
                    start_time = time.time()
                    signal_emitter.update_signal.emit(f"开始连接: {ipv6_test_url}")
                    
                    # 尝试下载图片
                    with urllib.request.urlopen(req, timeout=5, context=context) as response:
                        image_data = response.read()
                        
                        # 计算耗时
                        elapsed_time = time.time() - start_time
                        ipv6_test_elapsed_time = elapsed_time
                        
                        # 检查是否成功
                        if response.status == 200 and len(image_data) > 0:
                            ipv6_connected = True
                            signal_emitter.update_signal.emit(f"✓ 成功! 已下载 {len(image_data)} 字节")
                            signal_emitter.update_signal.emit(f"✓ 响应时间: {elapsed_time:.2f}秒")
                        else:
                            signal_emitter.update_signal.emit(f"✗ 失败: 状态码 {response.status}")
                            signal_emitter.update_signal.emit("\n结论: 您的网络不支持IPv6连接 ✗")
                            signal_emitter.complete_signal.emit(False, 0)
                            return
                            
                except Exception as e:
                    signal_emitter.update_signal.emit(f"✗ 连接失败: {e}")
                    signal_emitter.update_signal.emit("\n结论: 您的网络不支持IPv6连接 ✗")
                    signal_emitter.complete_signal.emit(False, 0)
                    return
                
                # 如果IPv6连接测试成功，再尝试获取公网IPv6地址
                if ipv6_connected:
                    signal_emitter.update_signal.emit("\n正在获取您的公网IPv6地址...")
                    
                    try:
                        # 使用curl命令获取IPv6地址
                        process = subprocess.Popen(
                            ["curl", "-6", "6.ipw.cn"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            encoding='utf-8',
                            errors='replace',
                            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                        )
                        
                        # 设置超时
                        timeout = 5  # 5秒超时
                        start_time = time.time()
                        while process.poll() is None and (time.time() - start_time) < timeout:
                            time.sleep(0.1)
                        
                        # 如果进程仍在运行，则强制终止
                        if process.poll() is None:
                            process.terminate()
                            signal_emitter.update_signal.emit("✗ 获取IPv6地址超时")
                        else:
                            stdout, stderr = process.communicate()
                            
                            if process.returncode == 0 and stdout.strip():
                                ipv6_address = stdout.strip()
                                signal_emitter.update_signal.emit(f"✓ 获取到的IPv6地址: {ipv6_address}")
                            else:
                                signal_emitter.update_signal.emit("✗ 未能获取到IPv6地址")
                                if stderr:
                                    signal_emitter.update_signal.emit(f"错误信息: {stderr}")
                    
                    except Exception as e:
                        signal_emitter.update_signal.emit(f"✗ 获取IPv6地址失败: {e}")
                    
                    # 输出最终结论
                    signal_emitter.update_signal.emit("\n结论: 您的网络支持IPv6连接 ✓")
                    signal_emitter.complete_signal.emit(True, ipv6_test_elapsed_time)
                    return
                
            except Exception as e:
                signal_emitter.update_signal.emit(f"测试过程中出错: {e}")
                signal_emitter.complete_signal.emit(False, 0)
        
        # 启动测试线程
        threading.Thread(target=test_ipv6, daemon=True).start()
        
        # 显示对话框
        dialog.exec()
        
    def toggle_ipv6_support(self, enabled):
        """切换IPv6支持
        
        Args:
            enabled: 是否启用IPv6支持
        """
        print(f"Toggle IPv6 support: {enabled}")
        
        # 如果用户尝试启用IPv6，检查系统是否支持IPv6并发出警告
        if enabled:
            # 先显示警告提示
            warning_msg_box = self._create_message_box(
                "警告", 
                "\n目前IPv6支持功能仍在测试阶段，可能会发生意料之外的bug！\n\n您确定需要启用吗？\n",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            response = warning_msg_box.exec()
            
            # 如果用户选择不启用，直接返回
            if response != QMessageBox.StandardButton.Yes:
                return False
            
            # 用户确认启用后，继续检查IPv6可用性
            ipv6_available = self.check_ipv6_availability()
                
            if not ipv6_available:
                msg_box = self._create_message_box("错误", "\n未检测到可用的IPv6连接，无法启用IPv6支持。\n\n请确保您的网络环境支持IPv6且已正确配置。\n")
                msg_box.exec()
                return False
                
        # 保存设置到配置
        if self.config is not None:
            self.config["ipv6_enabled"] = enabled
            # 直接使用utils.save_config保存配置
            from utils import save_config
            save_config(self.config)
            
        # 显示设置已保存的消息
        status = "启用" if enabled else "禁用"
        msg_box = self._create_message_box("IPv6设置", f"\nIPv6支持已{status}。新的设置将在下一次下载时生效。\n")
        msg_box.exec()
        return True
        
    def _create_message_box(self, title, message, buttons=QMessageBox.StandardButton.Ok):
        """创建统一风格的消息框
        
        Args:
            title: 消息框标题
            message: 消息内容
            buttons: 按钮类型，默认为确定按钮
        
        Returns:
            QMessageBox: 配置好的消息框实例
        """
        msg_box = msgbox_frame(
            f"{title} - {APP_NAME}",
            message,
            buttons,
        )
        return msg_box 