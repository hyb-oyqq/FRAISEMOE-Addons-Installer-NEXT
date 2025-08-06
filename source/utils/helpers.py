import os
import sys
import base64
import hashlib
import concurrent.futures
import ctypes
import json
import psutil
from PySide6 import QtCore, QtWidgets
import re
from PySide6.QtGui import QIcon, QPixmap
from data.config import APP_NAME, CONFIG_FILE
from utils.logger import setup_logger

# 初始化logger
logger = setup_logger("helpers")

def resource_path(relative_path):
    """获取资源的绝对路径，适用于开发环境和Nuitka打包环境"""
    if getattr(sys, 'frozen', False):
        # Nuitka/PyInstaller创建的临时文件夹，并将路径存储在_MEIPASS中或与可执行文件同目录
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(sys.executable)
    else:
        # 在开发环境中运行
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        # 处理特殊的可执行文件和数据文件路径
        if relative_path in ("aria2c-fast_x64.exe", "cfst.exe"):
            return os.path.join(base_path, 'bin', relative_path)
        elif relative_path in ("ip.txt", "ipv6.txt"):
            return os.path.join(base_path, 'data', relative_path)
            
    return os.path.join(base_path, relative_path)

def load_base64_image(base64_str):
    pixmap = QPixmap()
    pixmap.loadFromData(base64.b64decode(base64_str))
    return pixmap

def load_image_from_file(file_path):
    """加载图像文件到QPixmap
    
    Args:
        file_path: 图像文件路径
        
    Returns:
        QPixmap: 加载的图像
    """
    if os.path.exists(file_path):
        return QPixmap(file_path)
    return QPixmap()

def msgbox_frame(title, text, buttons=QtWidgets.QMessageBox.StandardButton.NoButton):
    msg_box = QtWidgets.QMessageBox()
    msg_box.setWindowTitle(title)
    msg_box.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
    
    # 直接加载图标文件
    icon_path = resource_path(os.path.join("IMG", "ICO", "icon.png"))
    if os.path.exists(icon_path):
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            msg_box.setWindowIcon(QIcon(pixmap))
            msg_box.setIconPixmap(pixmap.scaled(64, 64, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
    else:
        msg_box.setIcon(QtWidgets.QMessageBox.Icon.Information)
        
    msg_box.setText(text)
    msg_box.setStandardButtons(buttons)
    return msg_box

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_config(config):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except IOError as e:
        logger.error(f"Error saving config: {e}")


class HashManager:
    def __init__(self, HASH_SIZE):
        self.HASH_SIZE = HASH_SIZE

    def hash_calculate(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(self.HASH_SIZE), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def calculate_hashes_in_parallel(self, file_paths):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_file = {
                executor.submit(self.hash_calculate, path): path for path in file_paths
            }
            results = {}
            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    results[file_path] = future.result()
                except Exception as e:
                    results[file_path] = None # Mark as failed
                    logger.error(f"Error calculating hash for {file_path}: {e}")
        return results

    def hash_pop_window(self, check_type="default", is_offline=False):
        """显示文件检验窗口
        
        Args:
            check_type: 检查类型，可以是 'pre'(预检查), 'after'(后检查), 'extraction'(解压后检查), 'offline_extraction'(离线解压), 'offline_verify'(离线验证)
            is_offline: 是否处于离线模式
            
        Returns:
            QMessageBox: 消息框实例
        """
        message = "\n正在检验文件状态...\n"
        
        if is_offline:
            # 离线模式的消息
            if check_type == "pre":
                message = "\n正在检查游戏文件以确定需要安装的补丁...\n"
            elif check_type == "after":
                message = "\n正在检验本地文件完整性...\n"
            elif check_type == "offline_verify":
                message = "\n正在验证本地补丁压缩文件完整性...\n"
            elif check_type == "offline_extraction":
                message = "\n正在解压安装补丁文件...\n"
            else:
                message = "\n正在处理离线补丁文件...\n"
        else:
            # 在线模式的消息
            if check_type == "pre":
                message = "\n正在检查游戏文件以确定需要安装的补丁...\n"
            elif check_type == "after":
                message = "\n正在检验本地文件完整性...\n"
            elif check_type == "extraction":
                message = "\n正在验证下载的解压文件完整性...\n"
        
        msg_box = msgbox_frame(f"通知 - {APP_NAME}", message)
        msg_box.open()
        QtWidgets.QApplication.processEvents()
        return msg_box

    def cfg_pre_hash_compare(self, install_paths, plugin_hash, installed_status):
        status_copy = installed_status.copy()
        debug_mode = False
        
        # 尝试检测是否处于调试模式
        try:
            from data.config import CACHE
            debug_file = os.path.join(os.path.dirname(CACHE), "debug_mode.txt")
            debug_mode = os.path.exists(debug_file)
        except:
            pass
        
        for game_version, install_path in install_paths.items():
            if not os.path.exists(install_path):
                status_copy[game_version] = False
                if debug_mode:
                    logger.debug(f"DEBUG: 哈希预检查 - {game_version} 补丁文件不存在: {install_path}")
                continue

            try:
                expected_hash = plugin_hash.get(game_version, "")
                if not expected_hash:
                    if debug_mode:
                        logger.debug(f"DEBUG: 哈希预检查 - {game_version} 没有预期哈希值，跳过哈希检查")
                    # 当没有预期哈希值时，保持当前状态不变
                    continue
                    
                file_hash = self.hash_calculate(install_path)
                
                if debug_mode:
                    logger.debug(f"DEBUG: 哈希预检查 - {game_version}")
                    logger.debug(f"DEBUG: 文件路径: {install_path}")
                    logger.debug(f"DEBUG: 预期哈希值: {expected_hash}")
                    logger.debug(f"DEBUG: 实际哈希值: {file_hash}")
                    logger.debug(f"DEBUG: 哈希匹配: {file_hash == expected_hash}")
                
                if file_hash == expected_hash:
                    status_copy[game_version] = True
                    if debug_mode:
                        logger.debug(f"DEBUG: 哈希预检查 - {game_version} 哈希匹配成功")
                else:
                    status_copy[game_version] = False
                    if debug_mode:
                        logger.debug(f"DEBUG: 哈希预检查 - {game_version} 哈希不匹配")
            except Exception as e:
                status_copy[game_version] = False
                if debug_mode:
                    logger.debug(f"DEBUG: 哈希预检查异常 - {game_version}: {str(e)}")
        
        return status_copy

    def cfg_after_hash_compare(self, install_paths, plugin_hash, installed_status):
        debug_mode = False
        
        # 尝试检测是否处于调试模式
        try:
            from data.config import CACHE
            debug_file = os.path.join(os.path.dirname(CACHE), "debug_mode.txt")
            debug_mode = os.path.exists(debug_file)
        except:
            pass
            
        file_paths = [
            install_paths[game] for game in plugin_hash if installed_status.get(game)
        ]
        hash_results = self.calculate_hashes_in_parallel(file_paths)

        for game, expected_hash in plugin_hash.items():
            if installed_status.get(game):
                file_path = install_paths[game]
                file_hash = hash_results.get(file_path)
                
                if debug_mode:
                    logger.debug(f"DEBUG: 哈希后检查 - {game}")
                    logger.debug(f"DEBUG: 文件路径: {file_path}")
                    logger.debug(f"DEBUG: 预期哈希值: {expected_hash}")
                    logger.debug(f"DEBUG: 实际哈希值: {file_hash if file_hash else '计算失败'}")
                
                if file_hash is None:
                    installed_status[game] = False
                    if debug_mode:
                        logger.debug(f"DEBUG: 哈希后检查失败 - 无法计算文件哈希值: {game}")
                    return {
                        "passed": False,
                        "game": game,
                        "message": f"\n无法计算 {game} 的文件哈希值，文件可能已损坏或被占用。\n"
                    }

                if file_hash != expected_hash:
                    installed_status[game] = False
                    if debug_mode:
                        logger.debug(f"DEBUG: 哈希后检查失败 - 哈希值不匹配: {game}")
                    return {
                        "passed": False,
                        "game": game,
                        "message": f"\n检测到 {game} 的文件哈希值不匹配。\n"
                    }
        
        if debug_mode:
            logger.debug(f"DEBUG: 哈希后检查通过 - 所有文件哈希值匹配")
        return {"passed": True}

class AdminPrivileges:
    def __init__(self):
        self.required_exes = [
            "nekopara_vol1.exe",
            "nekopara_vol2.exe",
            "NEKOPARAvol3.exe",
            "NEKOPARAvol3.exe.nocrack",
            "nekopara_vol4.exe",
            "nekopara_after.exe",
        ]

    def is_admin(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def request_admin_privileges(self):
        if not self.is_admin():
            msg_box = msgbox_frame(
                f"权限检测 - {APP_NAME}",
                "\n需要管理员权限运行此程序\n",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            )
            try:
                reply = msg_box.exec()
                if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                    try:
                        ctypes.windll.shell32.ShellExecuteW(
                            None, "runas", sys.executable, " ".join(sys.argv), None, 1
                        )
                    except Exception as e:
                        msg_box = msgbox_frame(
                            f"错误 - {APP_NAME}",
                            f"\n请求管理员权限失败\n\n【错误信息】：{e}\n",
                            QtWidgets.QMessageBox.StandardButton.Ok,
                        )
                        msg_box.exec()
                    sys.exit(1)
                else:
                    msg_box = msgbox_frame(
                        f"权限检测 - {APP_NAME}",
                        "\n无法获取管理员权限，程序将退出\n",
                        QtWidgets.QMessageBox.StandardButton.Ok,
                        )
                    msg_box.exec()
                    sys.exit(1)
            except KeyboardInterrupt:
                logger.warning("管理员权限请求被用户中断")
                msg_box = msgbox_frame(
                    f"权限检测 - {APP_NAME}",
                    "\n操作被中断，程序将退出\n",
                    QtWidgets.QMessageBox.StandardButton.Ok,
                )
                msg_box.exec()
                sys.exit(1)
            except Exception as e:
                logger.error(f"管理员权限请求时发生错误: {e}")
                msg_box = msgbox_frame(
                    f"错误 - {APP_NAME}",
                    f"\n请求管理员权限时发生未知错误\n\n【错误信息】：{e}\n",
                    QtWidgets.QMessageBox.StandardButton.Ok,
                )
                msg_box.exec()
                sys.exit(1)

    def check_and_terminate_processes(self):
        try:
            for proc in psutil.process_iter(["pid", "name"]):
                proc_name = proc.info["name"].lower() if proc.info["name"] else ""
                
                # 检查进程名是否匹配任何需要终止的游戏进程
                for exe in self.required_exes:
                    if exe.lower() == proc_name:
                        # 获取不带.nocrack的游戏名称用于显示
                        display_name = exe.replace(".nocrack", "")
                        
                        msg_box = msgbox_frame(
                            f"进程检测 - {APP_NAME}",
                            f"\n检测到游戏正在运行： {display_name} \n\n是否终止？\n",
                            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                        )
                        try:
                            reply = msg_box.exec()
                            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                                try:
                                    proc.terminate()
                                    proc.wait(timeout=3)
                                except psutil.AccessDenied:
                                    msg_box = msgbox_frame(
                                        f"错误 - {APP_NAME}",
                                        f"\n无法关闭游戏： {display_name} \n\n请手动关闭后重启应用\n",
                                        QtWidgets.QMessageBox.StandardButton.Ok,
                                    )
                                    msg_box.exec()
                                    sys.exit(1)
                            else:
                                msg_box = msgbox_frame(
                                    f"进程检测 - {APP_NAME}",
                                    f"\n未关闭的游戏： {display_name} \n\n请手动关闭后重启应用\n",
                                    QtWidgets.QMessageBox.StandardButton.Ok,
                                )
                                msg_box.exec()
                                sys.exit(1)
                        except KeyboardInterrupt:
                            logger.warning(f"进程 {display_name} 终止操作被用户中断")
                            raise
                        except Exception as e:
                            logger.error(f"进程 {display_name} 终止操作时发生错误: {e}")
                            raise
        except KeyboardInterrupt:
            logger.warning("进程检查被用户中断")
            raise
        except Exception as e:
            logger.error(f"进程检查时发生错误: {e}")
            raise

class HostsManager:
    def __init__(self):
        self.hosts_path = os.path.join(os.environ['SystemRoot'], 'System32', 'drivers', 'etc', 'hosts')
        self.backup_path = os.path.join(os.path.dirname(self.hosts_path), f'hosts.bak.{APP_NAME}')
        self.original_content = None
        self.modified = False
        self.modified_hostnames = set()  # 跟踪被修改的主机名
        self.auto_restore_disabled = False  # 是否禁用自动还原hosts

    def get_hostname_entries(self, hostname):
        """获取hosts文件中指定域名的所有IP记录
        
        Args:
            hostname: 要查询的域名
            
        Returns:
            list: 域名对应的IP地址列表，如果未找到则返回空列表
        """
        try:
            # 如果original_content为空，先读取hosts文件
            if not self.original_content:
                try:
                    with open(self.hosts_path, 'r', encoding='utf-8') as f:
                        self.original_content = f.read()
                except Exception as e:
                    logger.error(f"读取hosts文件失败: {e}")
                    return []
            
            # 解析hosts文件中的每一行
            ip_addresses = []
            lines = self.original_content.splitlines()
            
            for line in lines:
                # 跳过注释和空行
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # 分割行内容获取IP和域名
                parts = line.split()
                if len(parts) >= 2:  # 至少包含IP和一个域名
                    ip = parts[0]
                    domains = parts[1:]
                    
                    # 如果当前行包含目标域名
                    if hostname in domains:
                        ip_addresses.append(ip)
            
            return ip_addresses
            
        except Exception as e:
            logger.error(f"获取hosts记录失败: {e}")
            return []
            
    def backup(self):
        if not AdminPrivileges().is_admin():
            logger.warning("需要管理员权限来备份hosts文件。")
            return False
        try:
            with open(self.hosts_path, 'r', encoding='utf-8') as f:
                self.original_content = f.read()
            with open(self.backup_path, 'w', encoding='utf-8') as f:
                f.write(self.original_content)
            logger.info(f"Hosts文件已备份到: {self.backup_path}")
            return True
        except IOError as e:
            logger.error(f"备份hosts文件失败: {e}")
            msg_box = msgbox_frame(f"错误 - {APP_NAME}", f"\n无法备份hosts文件，请检查权限。\n\n【错误信息】：{e}\n", QtWidgets.QMessageBox.StandardButton.Ok)
            msg_box.exec()
            return False
    
    def clean_hostname_entries(self, hostname):
        """清理hosts文件中指定域名的所有记录
        
        Args:
            hostname: 要清理的域名
            
        Returns:
            bool: 清理是否成功
        """
        if not self.original_content:
            if not self.backup():
                return False
        
        # 确保original_content不为None
        if not self.original_content:
            logger.error("无法读取hosts文件内容，操作中止。")
            return False
            
        if not AdminPrivileges().is_admin():
            logger.warning("需要管理员权限来修改hosts文件。")
            return False
            
        try:
            lines = self.original_content.splitlines()
            new_lines = [line for line in lines if hostname not in line]
            
            # 如果没有变化，不需要写入
            if len(new_lines) == len(lines):
                logger.info(f"Hosts文件中没有找到 {hostname} 的记录")
                return True
                
            with open(self.hosts_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
            
            # 更新原始内容
            self.original_content = '\n'.join(new_lines)
            logger.info(f"已从hosts文件中清理 {hostname} 的记录")
            return True
        except IOError as e:
            logger.error(f"清理hosts文件失败: {e}")
            return False

    def apply_ip(self, hostname, ip_address, clean=True):
        if not self.original_content:
            if not self.backup():
                return False
        
        if not self.original_content: # 再次检查，确保backup成功
            logger.error("无法读取hosts文件内容，操作中止。")
            return False

        if not AdminPrivileges().is_admin():
            logger.warning("需要管理员权限来修改hosts文件。")
            return False
        
        try:
            # 首先清理已有的同域名记录（如果需要）
            if clean:
                self.clean_hostname_entries(hostname)
            
            # 然后添加新记录
            lines = self.original_content.splitlines()
            new_entry = f"{ip_address}\t{hostname}"
            lines.append(f"\n# Added by {APP_NAME}")
            lines.append(new_entry)
            
            with open(self.hosts_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            # 更新原始内容
            self.original_content = '\n'.join(lines)
            self.modified = True
            # 记录被修改的主机名，用于最终清理
            self.modified_hostnames.add(hostname)
            logger.info(f"Hosts文件已更新: {new_entry}")
            return True
        except IOError as e:
            logger.error(f"修改hosts文件失败: {e}")
            msg_box = msgbox_frame(f"错误 - {APP_NAME}", f"\n无法修改hosts文件，请检查权限。\n\n【错误信息】：{e}\n", QtWidgets.QMessageBox.StandardButton.Ok)
            msg_box.exec()
            return False

    def set_auto_restore_disabled(self, disabled):
        """设置是否禁用自动还原hosts
        
        Args:
            disabled: 是否禁用自动还原hosts
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 更新状态
            self.auto_restore_disabled = disabled
            
            # 从配置文件读取当前配置
            from utils import load_config, save_config
            config = load_config()
            
            # 更新配置
            config['disable_auto_restore_hosts'] = disabled
            
            # 保存配置
            save_config(config)
            
            logger.info(f"已{'禁用' if disabled else '启用'}自动还原hosts")
            return True
        except Exception as e:
            logger.error(f"设置自动还原hosts状态失败: {e}")
            return False
            
    def is_auto_restore_disabled(self):
        """检查是否禁用了自动还原hosts
        
        Returns:
            bool: 是否禁用自动还原hosts
        """
        from utils import load_config
        config = load_config()
        auto_restore_disabled = config.get('disable_auto_restore_hosts', False)
        self.auto_restore_disabled = auto_restore_disabled
        return auto_restore_disabled

    def check_and_clean_all_entries(self):
        """检查并清理所有由本应用程序添加的hosts记录
        
        Returns:
            bool: 清理是否成功
        """
        # 如果禁用了自动还原，则不执行清理操作
        if self.is_auto_restore_disabled():
            logger.info("已禁用自动还原hosts，跳过清理操作")
            return True
            
        if not AdminPrivileges().is_admin():
            logger.warning("需要管理员权限来检查和清理hosts文件。")
            return False
            
        try:
            # 读取当前hosts文件内容
            with open(self.hosts_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
                
            lines = current_content.splitlines()
            new_lines = []
            skip_next = False
            
            for line in lines:
                # 如果上一行是我们的注释标记，跳过当前行
                if skip_next:
                    skip_next = False
                    continue
                    
                # 检查是否是我们添加的注释行
                if f"# Added by {APP_NAME}" in line:
                    skip_next = True  # 跳过下一行（实际的hosts记录）
                    continue
                    
                # 保留其他所有行
                new_lines.append(line)
                
            # 检查是否有变化
            if len(new_lines) == len(lines):
                logger.info("Hosts文件中没有找到由本应用添加的记录")
                return True
                
            # 写回清理后的内容
            with open(self.hosts_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
                
            logger.info(f"已清理所有由 {APP_NAME} 添加的hosts记录")
            return True
                
        except IOError as e:
            logger.error(f"检查和清理hosts文件失败: {e}")
            return False

    def restore(self):
        # 如果禁用了自动还原，则不执行还原操作
        if self.is_auto_restore_disabled():
            logger.info("已禁用自动还原hosts，跳过还原操作")
            return True
            
        if not self.modified:
            if os.path.exists(self.backup_path):
                try:
                    os.remove(self.backup_path)
                except OSError:
                    pass
            # 即使没有修改过，也检查一次是否有残留
            self.check_and_clean_all_entries()
            return True

        if not AdminPrivileges().is_admin():
            logger.warning("需要管理员权限来恢复hosts文件。")
            return False
            
        if self.original_content:
            try:
                with open(self.hosts_path, 'w', encoding='utf-8') as f:
                    f.write(self.original_content)
                self.modified = False
                logger.info("Hosts文件已从内存恢复。")
                if os.path.exists(self.backup_path):
                    try:
                        os.remove(self.backup_path)
                    except OSError:
                        pass
                # 恢复后再检查一次是否有残留
                self.check_and_clean_all_entries()
                return True
            except (IOError, OSError) as e:
                logger.error(f"从内存恢复hosts文件失败: {e}")
                return self.restore_from_backup_file()
        else:
            return self.restore_from_backup_file()

    def restore_from_backup_file(self):
        if not os.path.exists(self.backup_path):
            logger.warning("未找到hosts备份文件，无法恢复。")
            # 即使没有备份文件，也尝试清理可能的残留
            self.check_and_clean_all_entries()
            return False
        try:
            with open(self.backup_path, 'r', encoding='utf-8') as bf:
                backup_content = bf.read()
            with open(self.hosts_path, 'w', encoding='utf-8') as hf:
                hf.write(backup_content)
            os.remove(self.backup_path)
            self.modified = False
            logger.info("Hosts文件已从备份文件恢复。")
            # 恢复后再检查一次是否有残留
            self.check_and_clean_all_entries()
            return True
        except (IOError, OSError) as e:
            logger.error(f"从备份文件恢复hosts失败: {e}")
            msg_box = msgbox_frame(f"警告 - {APP_NAME}", f"\n自动恢复hosts文件失败，请手动从 {self.backup_path} 恢复。\n\n【错误信息】：{e}\n", QtWidgets.QMessageBox.StandardButton.Ok)
            msg_box.exec()
            # 尽管恢复失败，仍然尝试清理可能的残留
            self.check_and_clean_all_entries()
            return False