import os
import hashlib
import shutil
import tempfile
import py7zr
from PySide6.QtWidgets import QMessageBox

from data.config import PLUGIN, PLUGIN_HASH, GAME_INFO
from utils import msgbox_frame

class OfflineModeManager:
    """离线模式管理器，用于管理离线模式下的补丁安装和检测"""
    
    def __init__(self, main_window):
        """初始化离线模式管理器
        
        Args:
            main_window: 主窗口实例，用于访问UI和状态
        """
        self.main_window = main_window
        self.app_name = main_window.APP_NAME if hasattr(main_window, 'APP_NAME') else ""
        self.offline_patches = {}  # 存储离线补丁信息 {补丁名称: 文件路径}
        self.is_offline_mode = False
        
    def _is_debug_mode(self):
        """检查是否处于调试模式
        
        Returns:
            bool: 是否处于调试模式
        """
        try:
            if hasattr(self.main_window, 'debug_manager') and self.main_window.debug_manager:
                if hasattr(self.main_window.debug_manager, '_is_debug_mode'):
                    # 尝试直接从debug_manager获取状态
                    return self.main_window.debug_manager._is_debug_mode()
                elif hasattr(self.main_window, 'config'):
                    # 如果debug_manager还没准备好，尝试从配置中获取
                    return self.main_window.config.get('debug_mode', False)
            # 如果以上都不可行，返回False
            return False
        except Exception:
            # 捕获任何异常，默认返回False
            return False
        
    def scan_for_offline_patches(self, directory=None):
        """扫描指定目录（默认为软件所在目录）查找离线补丁文件
        
        Args:
            directory: 要扫描的目录，如果为None则使用软件所在目录
            
        Returns:
            dict: 找到的补丁文件 {补丁名称: 文件路径}
        """
        if directory is None:
            # 获取软件所在目录
            directory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        debug_mode = self._is_debug_mode()
        if debug_mode:
            print(f"DEBUG: 扫描离线补丁文件，目录: {directory}")
            
        # 要查找的补丁文件名
        patch_files = ["vol.1.7z", "vol.2.7z", "vol.3.7z", "vol.4.7z", "after.7z"]
        
        found_patches = {}
        
        # 扫描目录中的文件
        for file in os.listdir(directory):
            if file.lower() in patch_files:
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path):
                    patch_name = file.lower()
                    found_patches[patch_name] = file_path
                    if debug_mode:
                        print(f"DEBUG: 找到离线补丁文件: {patch_name} 路径: {file_path}")
                        
        self.offline_patches = found_patches
        return found_patches
        
    def has_offline_patches(self):
        """检查是否有可用的离线补丁文件
        
        Returns:
            bool: 是否有可用的离线补丁
        """
        if not self.offline_patches:
            self.scan_for_offline_patches()
            
        return len(self.offline_patches) > 0
        
    def set_offline_mode(self, enabled):
        """设置离线模式状态
        
        Args:
            enabled: 是否启用离线模式
            
        Returns:
            bool: 是否成功设置离线模式
        """
        debug_mode = self._is_debug_mode()
        
        if enabled:
            # 检查是否有离线补丁文件
            if not self.has_offline_patches() and not debug_mode:
                msgbox_frame(
                    f"离线模式错误 - {self.app_name}",
                    "\n未找到任何离线补丁文件，无法启用离线模式。\n\n请将补丁文件放置在软件所在目录后再尝试。\n",
                    QMessageBox.StandardButton.Ok
                ).exec()
                return False
                
            if debug_mode:
                print("DEBUG: 已启用离线模式（调试模式下允许强制启用）")
                
        self.is_offline_mode = enabled
        
        # 更新窗口标题
        if hasattr(self.main_window, 'setWindowTitle'):
            from data.config import APP_NAME, APP_VERSION
            mode_indicator = "[离线模式]" if enabled else "[在线模式]"
            self.main_window.setWindowTitle(f"{APP_NAME} v{APP_VERSION} {mode_indicator}")
            
            # 同时更新UI中的标题标签
            if hasattr(self.main_window, 'ui') and hasattr(self.main_window.ui, 'title_label'):
                self.main_window.ui.title_label.setText(f"{APP_NAME} v{APP_VERSION} {mode_indicator}")
        
        if debug_mode:
            print(f"DEBUG: 离线模式已{'启用' if enabled else '禁用'}")
            
        return True
        
    def get_offline_patch_path(self, game_version):
        """根据游戏版本获取对应的离线补丁文件路径
        
        Args:
            game_version: 游戏版本名称，如"NEKOPARA Vol.1"
            
        Returns:
            str: 离线补丁文件路径，如果没有找到则返回None
        """
        # 确保已扫描过补丁文件
        if not self.offline_patches:
            self.scan_for_offline_patches()
            
        # 根据游戏版本获取对应的补丁文件名
        patch_file = None
        
        if "Vol.1" in game_version:
            patch_file = "vol.1.7z"
        elif "Vol.2" in game_version:
            patch_file = "vol.2.7z"
        elif "Vol.3" in game_version:
            patch_file = "vol.3.7z"
        elif "Vol.4" in game_version:
            patch_file = "vol.4.7z"
        elif "After" in game_version:
            patch_file = "after.7z"
            
        # 检查是否有对应的补丁文件
        if patch_file and patch_file in self.offline_patches:
            return self.offline_patches[patch_file]
            
        return None
        
    def prepare_offline_patch(self, game_version, target_path):
        """准备离线补丁文件，复制到缓存目录
        
        Args:
            game_version: 游戏版本名称
            target_path: 目标路径（通常是缓存目录中的路径）
            
        Returns:
            bool: 是否成功准备补丁文件
        """
        source_path = self.get_offline_patch_path(game_version)
        
        if not source_path:
            return False
            
        debug_mode = self._is_debug_mode()
        
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # 复制文件
            shutil.copy2(source_path, target_path)
            
            if debug_mode:
                print(f"DEBUG: 已复制离线补丁文件 {source_path} 到 {target_path}")
                
            return True
        except Exception as e:
            if debug_mode:
                print(f"DEBUG: 复制离线补丁文件失败: {e}")
            return False
            
    def verify_patch_hash(self, game_version, file_path):
        """验证补丁文件的哈希值
        
        Args:
            game_version: 游戏版本名称
            file_path: 补丁压缩包文件路径
            
        Returns:
            bool: 哈希值是否匹配
        """
        # 获取预期的哈希值
        expected_hash = None
        
        if "Vol.1" in game_version:
            expected_hash = PLUGIN_HASH.get("vol1", "")
        elif "Vol.2" in game_version:
            expected_hash = PLUGIN_HASH.get("vol2", "")
        elif "Vol.3" in game_version:
            expected_hash = PLUGIN_HASH.get("vol3", "")
        elif "Vol.4" in game_version:
            expected_hash = PLUGIN_HASH.get("vol4", "")
        elif "After" in game_version:
            expected_hash = PLUGIN_HASH.get("after", "")
            
        if not expected_hash:
            print(f"DEBUG: 未找到 {game_version} 的预期哈希值")
            return False
            
        debug_mode = self._is_debug_mode()
        
        if debug_mode:
            print(f"DEBUG: 开始验证离线补丁文件: {file_path}")
            print(f"DEBUG: 游戏版本: {game_version}")
            print(f"DEBUG: 预期哈希值: {expected_hash}")
            
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                if debug_mode:
                    print(f"DEBUG: 补丁文件不存在: {file_path}")
                return False
                
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if debug_mode:
                print(f"DEBUG: 补丁文件大小: {file_size} 字节")
                
            if file_size == 0:
                if debug_mode:
                    print(f"DEBUG: 补丁文件大小为0，无效文件")
                return False
                
            # 创建临时目录用于解压文件
            with tempfile.TemporaryDirectory() as temp_dir:
                if debug_mode:
                    print(f"DEBUG: 创建临时目录: {temp_dir}")
                    
                # 解压补丁文件
                try:
                    if debug_mode:
                        print(f"DEBUG: 开始解压文件: {file_path}")
                        
                    with py7zr.SevenZipFile(file_path, mode="r") as archive:
                        # 获取压缩包内文件列表
                        file_list = archive.getnames()
                        if debug_mode:
                            print(f"DEBUG: 压缩包内文件列表: {file_list}")
                            
                        # 解压所有文件
                        archive.extractall(path=temp_dir)
                        
                        if debug_mode:
                            print(f"DEBUG: 解压完成")
                            # 列出解压后的文件
                            extracted_files = []
                            for root, dirs, files in os.walk(temp_dir):
                                for file in files:
                                    extracted_files.append(os.path.join(root, file))
                            print(f"DEBUG: 解压后的文件列表: {extracted_files}")
                except Exception as e:
                    if debug_mode:
                        print(f"DEBUG: 解压补丁文件失败: {e}")
                        print(f"DEBUG: 错误类型: {type(e).__name__}")
                        import traceback
                        print(f"DEBUG: 错误堆栈: {traceback.format_exc()}")
                    return False
                
                # 获取补丁文件路径
                patch_file = None
                if "Vol.1" in game_version:
                    patch_file = os.path.join(temp_dir, "vol.1", "adultsonly.xp3")
                elif "Vol.2" in game_version:
                    patch_file = os.path.join(temp_dir, "vol.2", "adultsonly.xp3")
                elif "Vol.3" in game_version:
                    patch_file = os.path.join(temp_dir, "vol.3", "update00.int")
                elif "Vol.4" in game_version:
                    patch_file = os.path.join(temp_dir, "vol.4", "vol4adult.xp3")
                elif "After" in game_version:
                    patch_file = os.path.join(temp_dir, "after", "afteradult.xp3")
                
                if not patch_file or not os.path.exists(patch_file):
                    if debug_mode:
                        print(f"DEBUG: 未找到解压后的补丁文件: {patch_file}")
                        # 尝试查找可能的替代文件
                        alternative_files = []
                        for root, dirs, files in os.walk(temp_dir):
                            for file in files:
                                if file.endswith('.xp3') or file.endswith('.int'):
                                    alternative_files.append(os.path.join(root, file))
                        if alternative_files:
                            print(f"DEBUG: 找到可能的替代文件: {alternative_files}")
                        
                        # 检查解压目录结构
                        print(f"DEBUG: 检查解压目录结构:")
                        for root, dirs, files in os.walk(temp_dir):
                            print(f"DEBUG: 目录: {root}")
                            print(f"DEBUG: 子目录: {dirs}")
                            print(f"DEBUG: 文件: {files}")
                    return False
                
                if debug_mode:
                    print(f"DEBUG: 找到解压后的补丁文件: {patch_file}")
                    
                # 计算补丁文件哈希值
                try:
                    with open(patch_file, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    
                    # 比较哈希值
                    result = file_hash.lower() == expected_hash.lower()
                    
                    if debug_mode:
                        print(f"DEBUG: 补丁文件 {patch_file} 哈希值验证: {'成功' if result else '失败'}")
                        print(f"DEBUG: 预期哈希值: {expected_hash}")
                        print(f"DEBUG: 实际哈希值: {file_hash}")
                        
                    return result
                except Exception as e:
                    if debug_mode:
                        print(f"DEBUG: 计算补丁文件哈希值失败: {e}")
                        print(f"DEBUG: 错误类型: {type(e).__name__}")
                    return False
        except Exception as e:
            if debug_mode:
                print(f"DEBUG: 验证补丁哈希值失败: {e}")
                print(f"DEBUG: 错误类型: {type(e).__name__}")
                import traceback
                print(f"DEBUG: 错误堆栈: {traceback.format_exc()}")
            return False
            
    def is_offline_mode_available(self):
        """检查是否可以使用离线模式
        
        Returns:
            bool: 是否可以使用离线模式
        """
        # 在调试模式下始终允许离线模式
        if self._is_debug_mode():
            return True
            
        # 检查是否有离线补丁文件
        return self.has_offline_patches()
        
    def is_in_offline_mode(self):
        """检查当前是否处于离线模式
        
        Returns:
            bool: 是否处于离线模式
        """
        return self.is_offline_mode

    def install_offline_patches(self, selected_games):
        """直接安装离线补丁，完全绕过下载模块
        
        Args:
            selected_games: 用户选择安装的游戏列表
            
        Returns:
            bool: 是否成功启动安装流程
        """
        debug_mode = self._is_debug_mode()
        
        if debug_mode:
            print(f"DEBUG: 开始离线安装流程，选择的游戏: {selected_games}")
            
        if not self.is_in_offline_mode():
            if debug_mode:
                print("DEBUG: 当前不是离线模式，无法使用离线安装")
            return False
            
        # 确保已扫描过补丁文件
        if not self.offline_patches:
            self.scan_for_offline_patches()
            
        if not self.offline_patches:
            if debug_mode:
                print("DEBUG: 未找到任何离线补丁文件")
            msgbox_frame(
                f"离线安装错误 - {self.app_name}",
                "\n未找到任何离线补丁文件，无法进行离线安装。\n\n请将补丁文件放置在软件所在目录后再尝试。\n",
                QMessageBox.StandardButton.Ok
            ).exec()
            return False
            
        # 获取游戏目录
        game_dirs = self.main_window.game_detector.identify_game_directories_improved(
            self.main_window.download_manager.selected_folder
        )
        
        if not game_dirs:
            if debug_mode:
                print("DEBUG: 未识别到任何游戏目录")
            return False
            
        # 显示文件检验窗口
        self.main_window.hash_msg_box = self.main_window.hash_manager.hash_pop_window(check_type="pre", is_offline=True)
        
        # 获取安装路径
        install_paths = self.main_window.download_manager.get_install_paths()
        
        # 创建并启动哈希线程进行预检查
        self.main_window.hash_thread = self.main_window.create_hash_thread("pre", install_paths)
        self.main_window.hash_thread.pre_finished.connect(
            lambda updated_status: self.on_offline_pre_hash_finished(updated_status, game_dirs, selected_games)
        )
        self.main_window.hash_thread.start()
        
        return True
        
    def on_offline_pre_hash_finished(self, updated_status, game_dirs, selected_games):
        """离线模式下的哈希预检查完成处理
        
        Args:
            updated_status: 更新后的安装状态
            game_dirs: 识别到的游戏目录
            selected_games: 用户选择安装的游戏列表
        """
        debug_mode = self._is_debug_mode()
        
        # 更新安装状态
        self.main_window.installed_status = updated_status
        
        # 关闭哈希检查窗口
        if self.main_window.hash_msg_box and self.main_window.hash_msg_box.isVisible():
            self.main_window.hash_msg_box.accept()
            self.main_window.hash_msg_box = None
            
        # 重新启用主窗口
        self.main_window.setEnabled(True)
        
        # 过滤出需要安装的游戏
        installable_games = []
        for game_version in selected_games:
            if game_version in game_dirs and not self.main_window.installed_status.get(game_version, False):
                # 检查是否有对应的离线补丁
                if self.get_offline_patch_path(game_version):
                    installable_games.append(game_version)
                elif debug_mode:
                    print(f"DEBUG: 未找到 {game_version} 的离线补丁文件，跳过")
                    
        if not installable_games:
            if debug_mode:
                print("DEBUG: 没有需要安装的游戏或未找到对应的离线补丁")
            msgbox_frame(
                f"离线安装信息 - {self.app_name}",
                "\n没有需要安装的游戏或未找到对应的离线补丁文件。\n",
                QMessageBox.StandardButton.Ok
            ).exec()
            self.main_window.ui.start_install_text.setText("开始安装")
            return
            
        # 开始安装流程
        if debug_mode:
            print(f"DEBUG: 开始离线安装流程，安装游戏: {installable_games}")
            
        # 创建安装任务列表
        install_tasks = []
        for game_version in installable_games:
            # 获取离线补丁文件路径
            patch_file = self.get_offline_patch_path(game_version)
            if not patch_file:
                continue
                
            # 获取游戏目录
            game_folder = game_dirs.get(game_version)
            if not game_folder:
                continue
                
            # 获取目标路径
            if "Vol.1" in game_version:
                _7z_path = os.path.join(PLUGIN, "vol.1.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
            elif "Vol.2" in game_version:
                _7z_path = os.path.join(PLUGIN, "vol.2.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
            elif "Vol.3" in game_version:
                _7z_path = os.path.join(PLUGIN, "vol.3.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
            elif "Vol.4" in game_version:
                _7z_path = os.path.join(PLUGIN, "vol.4.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
            elif "After" in game_version:
                _7z_path = os.path.join(PLUGIN, "after.7z")
                plugin_path = os.path.join(PLUGIN, GAME_INFO[game_version]["plugin_path"])
            else:
                continue
                
            # 添加到安装任务列表
            install_tasks.append((patch_file, game_folder, game_version, _7z_path, plugin_path))
            
        # 开始执行第一个安装任务
        if install_tasks:
            self.process_next_offline_install_task(install_tasks)
        else:
            self.main_window.ui.start_install_text.setText("开始安装")
            
    def process_next_offline_install_task(self, install_tasks):
        """处理下一个离线安装任务
        
        Args:
            install_tasks: 安装任务列表，每个任务是一个元组 (patch_file, game_folder, game_version, _7z_path, plugin_path)
        """
        debug_mode = self._is_debug_mode()
        
        if not install_tasks:
            # 所有任务完成，进行后检查
            if debug_mode:
                print("DEBUG: 所有离线安装任务完成，进行后检查")
            self.main_window.after_hash_compare()
            return
            
        # 获取下一个任务
        patch_file, game_folder, game_version, _7z_path, plugin_path = install_tasks.pop(0)
        
        if debug_mode:
            print(f"DEBUG: 处理离线安装任务: {game_version}")
            print(f"DEBUG: 补丁文件: {patch_file}")
            print(f"DEBUG: 游戏目录: {game_folder}")
            
        # 确保目标目录存在
        os.makedirs(os.path.dirname(_7z_path), exist_ok=True)
        
        try:
            # 复制补丁文件到缓存目录
            shutil.copy2(patch_file, _7z_path)
            
            if debug_mode:
                print(f"DEBUG: 已复制补丁文件到缓存目录: {_7z_path}")
                print(f"DEBUG: 开始验证补丁文件哈希值")
                
            # 获取预期的哈希值
            expected_hash = None
            if "Vol.1" in game_version:
                expected_hash = PLUGIN_HASH.get("vol1", "")
            elif "Vol.2" in game_version:
                expected_hash = PLUGIN_HASH.get("vol2", "")
            elif "Vol.3" in game_version:
                expected_hash = PLUGIN_HASH.get("vol3", "")
            elif "Vol.4" in game_version:
                expected_hash = PLUGIN_HASH.get("vol4", "")
            elif "After" in game_version:
                expected_hash = PLUGIN_HASH.get("after", "")
                
            if debug_mode and expected_hash:
                print(f"DEBUG: 预期哈希值: {expected_hash}")
            
            # 显示哈希验证窗口 - 使用离线特定消息
            self.main_window.hash_msg_box = self.main_window.hash_manager.hash_pop_window(check_type="offline_verify", is_offline=True)
            
            # 验证补丁文件哈希
            hash_valid = self.verify_patch_hash(game_version, _7z_path)
            
            # 关闭哈希验证窗口
            if self.main_window.hash_msg_box and self.main_window.hash_msg_box.isVisible():
                self.main_window.hash_msg_box.close()
                self.main_window.hash_msg_box = None
            
            if hash_valid:
                if debug_mode:
                    print(f"DEBUG: 补丁文件哈希验证成功，开始解压")
                
                # 显示解压窗口 - 使用离线特定消息
                self.main_window.hash_msg_box = self.main_window.hash_manager.hash_pop_window(check_type="offline_extraction", is_offline=True)
                
                try:
                    # 创建解压线程
                    extraction_thread = self.main_window.create_extraction_thread(
                        _7z_path, game_folder, plugin_path, game_version
                    )
                    
                    # 正确连接信号
                    extraction_thread.finished.connect(
                        lambda success, error, game_ver: self.on_extraction_thread_finished(
                            success, error, game_ver, install_tasks
                        )
                    )
                    
                    # 启动解压线程
                    extraction_thread.start()
                except Exception as e:
                    if debug_mode:
                        print(f"DEBUG: 创建或启动解压线程失败: {e}")
                    
                    # 关闭解压窗口
                    if self.main_window.hash_msg_box and self.main_window.hash_msg_box.isVisible():
                        self.main_window.hash_msg_box.close()
                        self.main_window.hash_msg_box = None
                    
                    # 显示错误消息
                    msgbox_frame(
                        f"解压错误 - {self.app_name}",
                        f"\n{game_version} 的解压过程中发生错误: {str(e)}\n\n跳过此游戏的安装。\n",
                        QMessageBox.StandardButton.Ok
                    ).exec()
                    
                    # 继续下一个任务
                    self.process_next_offline_install_task(install_tasks)
            else:
                if debug_mode:
                    print(f"DEBUG: 补丁文件哈希验证失败")
                    
                # 显示错误消息
                msgbox_frame(
                    f"哈希验证失败 - {self.app_name}",
                    f"\n{game_version} 的补丁文件哈希验证失败，可能已损坏或被篡改。\n\n跳过此游戏的安装。\n",
                    QMessageBox.StandardButton.Ok
                ).exec()
                
                # 继续下一个任务
                self.process_next_offline_install_task(install_tasks)
        except Exception as e:
            if debug_mode:
                print(f"DEBUG: 离线安装任务处理失败: {e}")
                
            # 显示错误消息
            msgbox_frame(
                f"安装错误 - {self.app_name}",
                f"\n{game_version} 的安装过程中发生错误: {str(e)}\n\n跳过此游戏的安装。\n",
                QMessageBox.StandardButton.Ok
            ).exec()
            
            # 继续下一个任务
            self.process_next_offline_install_task(install_tasks)
    
    def on_extraction_thread_finished(self, success, error_message, game_version, remaining_tasks):
        """解压线程完成后的处理
        
        Args:
            success: 是否解压成功
            error_message: 错误信息
            game_version: 游戏版本
            remaining_tasks: 剩余的安装任务列表
        """
        debug_mode = self._is_debug_mode()
        
        # 关闭解压窗口
        if self.main_window.hash_msg_box and self.main_window.hash_msg_box.isVisible():
            self.main_window.hash_msg_box.close()
            self.main_window.hash_msg_box = None
        
        if debug_mode:
            print(f"DEBUG: 离线解压完成，状态: {'成功' if success else '失败'}")
            if not success:
                print(f"DEBUG: 错误信息: {error_message}")
        
        if not success:
            # 显示错误消息
            msgbox_frame(
                f"解压失败 - {self.app_name}",
                f"\n{game_version} 的补丁解压失败。\n\n错误信息: {error_message}\n\n跳过此游戏的安装。\n",
                QMessageBox.StandardButton.Ok
            ).exec()
            
            # 更新安装状态
            self.main_window.installed_status[game_version] = False
        else:
            # 更新安装状态
            self.main_window.installed_status[game_version] = True
        
        # 处理下一个任务
        self.process_next_offline_install_task(remaining_tasks)
            
    def on_offline_extraction_finished(self, remaining_tasks):
        """离线模式下的解压完成处理（旧方法，保留兼容性）
        
        Args:
            remaining_tasks: 剩余的安装任务列表
        """
        debug_mode = self._is_debug_mode()
        
        if debug_mode:
            print("DEBUG: 离线解压完成，继续处理下一个任务")
            
        # 处理下一个任务
        self.process_next_offline_install_task(remaining_tasks) 