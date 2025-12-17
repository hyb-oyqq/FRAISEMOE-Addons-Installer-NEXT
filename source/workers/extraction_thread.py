import os
import shutil
import py7zr
import tempfile
import traceback
from PySide6.QtCore import QThread, Signal
from config.config import PLUGIN, GAME_INFO
import time  # 用于时间计算
import threading
import queue
from concurrent.futures import TimeoutError

class ExtractionThread(QThread):
    finished = Signal(bool, str, str)  # success, error_message, game_version
    progress = Signal(int, str)  # 添加进度信号，传递进度百分比和状态信息

    def __init__(self, _7z_path, game_folder, plugin_path, game_version, parent=None, extracted_path=None):
        super().__init__(parent)
        self._7z_path = _7z_path
        self.game_folder = game_folder
        self.plugin_path = plugin_path
        self.game_version = game_version
        self.extracted_path = extracted_path  # 添加已解压文件路径参数

    def run(self):
        try:
            # 确保游戏目录存在
            os.makedirs(self.game_folder, exist_ok=True)

            def update_progress(percent: int, message: str):
                try:
                    self.progress.emit(percent, message)
                except Exception:
                    pass
            
            # 记录调试信息
            from utils.logger import setup_logger
            debug_logger = setup_logger("extraction_thread")
            debug_logger.info(f"====== 开始处理 {self.game_version} 补丁文件 ======")
            debug_logger.info(f"压缩包路径: {self._7z_path}")
            debug_logger.info(f"游戏目录: {self.game_folder}")
            debug_logger.info(f"插件路径: {self.plugin_path}")

            update_progress(0, f"开始处理 {self.game_version} 的补丁文件...")

            # 支持外部请求中断
            if self.isInterruptionRequested():
                self.finished.emit(False, "操作已取消", self.game_version)
                return

            # 如果提供了已解压文件路径，直接使用它
            if self.extracted_path and os.path.exists(self.extracted_path):
                update_progress(20, f"正在复制 {self.game_version} 的补丁文件...\n(在此过程中可能会卡顿或无响应，请不要关闭软件)")

                # 直接复制已解压的文件到游戏目录
                target_file = os.path.join(self.game_folder, os.path.basename(self.plugin_path))
                shutil.copy(self.extracted_path, target_file)

                update_progress(60, f"正在完成 {self.game_version} 的补丁安装...")

                # 对于NEKOPARA After，还需要复制签名文件
                if self.game_version == "NEKOPARA After":
                    try:
                        update_progress(70, f"正在处理 {self.game_version} 的签名文件...")
                        # 从已解压文件的目录中获取签名文件
                        extracted_dir = os.path.dirname(self.extracted_path)
                        sig_filename = os.path.basename(GAME_INFO[self.game_version]["sig_path"])
                        sig_path = os.path.join(extracted_dir, sig_filename)

                        # 尝试多种可能的签名文件路径
                        if not os.path.exists(sig_path):
                            # 尝试在同级目录查找
                            sig_path = os.path.join(os.path.dirname(extracted_dir), sig_filename)
                        
                        # 如果签名文件存在，则复制它
                        if os.path.exists(sig_path):
                            target_sig = os.path.join(self.game_folder, sig_filename)
                            shutil.copy(sig_path, target_sig)
                            update_progress(80, f"签名文件复制完成")
                        else:
                            # 如果签名文件不存在，则使用原始路径
                            sig_path = os.path.join(PLUGIN, GAME_INFO[self.game_version]["sig_path"])
                            if os.path.exists(sig_path):
                                target_sig = os.path.join(self.game_folder, os.path.basename(sig_path))
                                shutil.copy(sig_path, target_sig)
                                update_progress(80, f"使用内置签名文件完成")
                            else:
                                update_progress(80, f"未找到签名文件，继续安装主补丁文件")
                    except Exception as sig_err:
                        # 签名文件处理失败时记录错误但不中断主流程
                        update_progress(80, f"签名文件处理失败: {str(sig_err)}")

                update_progress(100, f"{self.game_version} 补丁文件处理完成")
                self.finished.emit(True, "", self.game_version)
                return

            # 否则解压源压缩包到临时目录，再复制目标文件
            update_progress(10, f"正在打开 {self.game_version} 的补丁压缩包...")

            with py7zr.SevenZipFile(self._7z_path, mode="r") as archive:
                # 获取压缩包内的文件列表
                file_list = archive.getnames()
                
                # 详细记录压缩包中的所有文件
                debug_logger.debug(f"压缩包内容分析:")
                debug_logger.debug(f"- 文件总数: {len(file_list)}")
                for i, f in enumerate(file_list):
                    is_folder = f.endswith('/') or f.endswith('\\')
                    file_type = '文件夹' if is_folder else '文件'
                    debug_logger.debug(f"  {i+1}. {f} - 类型: {file_type}")

                update_progress(20, f"正在分析 {self.game_version} 的补丁文件...")

                update_progress(30, f"正在解压 {self.game_version} 的补丁文件...\n(在此过程中可能会卡顿或无响应，请不要关闭软件)")

                with tempfile.TemporaryDirectory() as temp_dir:
                    # 查找主补丁文件和签名文件
                    target_filename = os.path.basename(self.plugin_path)
                    # 只有NEKOPARA After版本才需要查找签名文件
                    if self.game_version == "NEKOPARA After":
                        sig_filename = target_filename + ".sig"  # 签名文件名
                        debug_logger.debug(f"查找主补丁文件: {target_filename}")
                        debug_logger.debug(f"查找签名文件: {sig_filename}")
                    else:
                        sig_filename = None
                        debug_logger.debug(f"查找主补丁文件: {target_filename}")
                        debug_logger.debug(f"{self.game_version} 不需要签名文件")
                    
                    target_file_in_archive = None
                    sig_file_in_archive = None
                    
                    # 对于NEKOPARA After，增加特殊处理
                    if self.game_version == "NEKOPARA After":
                        # 增加专门的检查，同时识别主补丁和签名文件
                        debug_logger.debug("执行NEKOPARA After特殊补丁文件识别")
                        
                        # 查找主补丁和签名文件
                        for file_path in file_list:
                            basename = os.path.basename(file_path)
                            
                            # 查找主补丁文件
                            if basename == "afteradult.xp3" and not basename.endswith('.sig'):
                                target_file_in_archive = file_path
                                debug_logger.debug(f"找到精确匹配的After主补丁文件: {target_file_in_archive}")
                                
                            # 查找签名文件
                            elif basename == "afteradult.xp3.sig" or basename.endswith('.sig'):
                                sig_file_in_archive = file_path
                                debug_logger.debug(f"找到After签名文件: {sig_file_in_archive}")
                        
                        # 如果没找到主补丁文件，寻找可能的替代文件
                        if not target_file_in_archive:
                            for file_path in file_list:
                                if "afteradult.xp3" in file_path and not file_path.endswith('.sig'):
                                    target_file_in_archive = file_path
                                    debug_logger.debug(f"找到备选After主补丁文件: {target_file_in_archive}")
                                    break
                    else:
                        # 标准处理逻辑
                        for file_path in file_list:
                            basename = os.path.basename(file_path)
                            
                            # 查找主补丁文件
                            if basename == target_filename and not basename.endswith('.sig'):
                                target_file_in_archive = file_path
                                debug_logger.debug(f"在压缩包中找到主补丁文件: {target_file_in_archive}")
                            
                            # 查找签名文件
                            elif basename == sig_filename:
                                sig_file_in_archive = file_path
                                debug_logger.debug(f"在压缩包中找到签名文件: {sig_file_in_archive}")
                        
                        # 如果没有找到精确匹配的主补丁文件，使用更宽松的搜索
                        if not target_file_in_archive:
                            debug_logger.warning(f"没有找到精确匹配的主补丁文件，尝试更宽松的搜索")
                            for file_path in file_list:
                                if target_filename in file_path and not file_path.endswith('.sig'):
                                    target_file_in_archive = file_path
                                    debug_logger.info(f"在压缩包中找到可能的主补丁文件: {target_file_in_archive}")
                                    break

                    # 如果找不到主补丁文件，使用回退方案：提取全部内容
                    if not target_file_in_archive:
                        debug_logger.warning(f"未能识别正确的主补丁文件，将提取所有文件并尝试查找")
                        
                        # 提取所有文件到临时目录
                        update_progress(30, f"正在解压所有文件...")
                        archive.extractall(path=temp_dir)
                        debug_logger.debug(f"已提取所有文件到临时目录")
                        
                        # 在提取的文件中查找主补丁文件和签名文件
                        found_main = False
                        found_sig = False
                        
                        for root, dirs, files in os.walk(temp_dir):
                            for file in files:
                                # 查找主补丁文件
                                if file == target_filename and not file.endswith('.sig'):
                                    extracted_file_path = os.path.join(root, file)
                                    file_size = os.path.getsize(extracted_file_path)
                                    debug_logger.debug(f"在提取的文件中找到主补丁文件: {extracted_file_path}, 大小: {file_size} 字节")
                                    
                                    # 复制到目标位置
                                    target_path = os.path.join(self.game_folder, target_filename)
                                    shutil.copy2(extracted_file_path, target_path)
                                    debug_logger.debug(f"已复制主补丁文件到: {target_path}")
                                    found_main = True
                                
                                # 查找签名文件
                                elif file == sig_filename or file.endswith('.sig'):
                                    extracted_sig_path = os.path.join(root, file)
                                    sig_size = os.path.getsize(extracted_sig_path)
                                    debug_logger.debug(f"在提取的文件中找到签名文件: {extracted_sig_path}, 大小: {sig_size} 字节")
                                    
                                    # 复制到目标位置
                                    sig_target = os.path.join(self.game_folder, sig_filename)
                                    shutil.copy2(extracted_sig_path, sig_target)
                                    debug_logger.debug(f"已复制签名文件到: {sig_target}")
                                    found_sig = True
                                
                                # 如果两个文件都找到，可以停止遍历
                                if found_main and found_sig:
                                    debug_logger.debug("已找到所有需要的文件，停止遍历")
                                    break
                            
                            if found_main and found_sig:
                                break
                                    
                        if not found_main:
                            debug_logger.error(f"无法找到主补丁文件，安装失败")
                            raise FileNotFoundError(f"在压缩包中未找到主补丁文件 {target_filename}")
                            
                        # 只有NEKOPARA After版本才需要处理签名文件
                        if self.game_version == "NEKOPARA After":
                            # 签名文件没找到不影响主流程，但记录警告
                            if not found_sig:
                                debug_logger.warning(f"未找到签名文件 {sig_filename}，但继续安装主补丁文件")
                        else:
                            debug_logger.info(f"{self.game_version} 不需要签名文件，跳过签名文件处理")
                    else:
                        # 准备要解压的文件列表
                        files_to_extract = [target_file_in_archive]
                        # 只有NEKOPARA After版本才需要解压签名文件
                        if self.game_version == "NEKOPARA After" and sig_file_in_archive:
                            files_to_extract.append(sig_file_in_archive)
                            debug_logger.debug(f"将同时解压主补丁文件和签名文件: {files_to_extract}")
                        else:
                            debug_logger.debug(f"将仅解压主补丁文件: {files_to_extract}")
                        
                        # 解压选定的文件到临时目录
                        debug_logger.debug(f"开始解压选定文件到临时目录: {temp_dir}")
                        
                        # 设置解压超时时间（秒）
                        extract_timeout = 180  # 3分钟超时
                        debug_logger.debug(f"设置解压超时: {extract_timeout}秒")
                        
                        # 创建子线程执行解压
                        import threading
                        import queue
                        
                        extract_result = queue.Queue()
                        
                        def extract_files():
                            try:
                                archive.extract(path=temp_dir, targets=files_to_extract)
                                extract_result.put(("success", None))
                            except Exception as e:
                                extract_result.put(("error", e))
                        
                        extract_thread = threading.Thread(target=extract_files)
                        extract_thread.daemon = True
                        extract_thread.start()
                        
                        # 每5秒更新一次进度，最多等待设定的超时时间
                        total_waited = 0
                        while extract_thread.is_alive() and total_waited < extract_timeout:
                            update_progress(30 + int(30 * total_waited / extract_timeout), 
                                f"正在解压文件...已等待{total_waited}秒")
                            extract_thread.join(5)  # 等待5秒
                            total_waited += 5
                        
                        # 检查是否超时
                        if extract_thread.is_alive():
                            debug_logger.error(f"解压超时（超过{extract_timeout}秒）")
                            raise TimeoutError(f"解压超时（超过{extract_timeout}秒），请检查补丁文件是否完整")
                        
                        # 检查解压结果
                        if not extract_result.empty():
                            status, error = extract_result.get()
                            if status == "error":
                                debug_logger.error(f"解压错误: {error}")
                                raise error
                        
                        debug_logger.debug(f"文件解压完成")

                        update_progress(60, f"正在复制 {self.game_version} 的补丁文件...")

                        # 复制主补丁文件到游戏目录
                        extracted_file_path = os.path.join(temp_dir, target_file_in_archive)
                        
                        # 检查解压后的文件是否存在及其大小
                        if os.path.exists(extracted_file_path):
                            file_size = os.path.getsize(extracted_file_path)
                            debug_logger.debug(f"解压后的主补丁文件存在: {extracted_file_path}, 大小: {file_size} 字节")
                        else:
                            debug_logger.error(f"解压后的主补丁文件不存在: {extracted_file_path}")
                            raise FileNotFoundError(f"解压后的文件不存在: {extracted_file_path}")

                        # 构建目标路径并复制
                        target_path = os.path.join(self.game_folder, target_filename)
                        debug_logger.debug(f"复制主补丁文件: {extracted_file_path} 到 {target_path}")
                        shutil.copy2(extracted_file_path, target_path)
                        
                        # 验证主补丁文件是否成功复制
                        if os.path.exists(target_path):
                            target_size = os.path.getsize(target_path)
                            debug_logger.debug(f"主补丁文件成功复制: {target_path}, 大小: {target_size} 字节")
                        else:
                            debug_logger.error(f"主补丁文件复制失败: {target_path}")
                            raise FileNotFoundError(f"目标文件复制失败: {target_path}")
                            
                        # 只有NEKOPARA After版本才需要处理签名文件
                        if self.game_version == "NEKOPARA After":
                            # 如果有找到签名文件，也复制它
                            if sig_file_in_archive:
                                update_progress(80, f"正在复制签名文件...")
                                extracted_sig_path = os.path.join(temp_dir, sig_file_in_archive)
                                
                                if os.path.exists(extracted_sig_path):
                                    sig_size = os.path.getsize(extracted_sig_path)
                                    debug_logger.debug(f"解压后的签名文件存在: {extracted_sig_path}, 大小: {sig_size} 字节")
                                    
                                    # 复制签名文件到游戏目录
                                    sig_target = os.path.join(self.game_folder, sig_filename)
                                    shutil.copy2(extracted_sig_path, sig_target)
                                    debug_logger.debug(f"签名文件成功复制: {sig_target}")
                                else:
                                    debug_logger.warning(f"解压后的签名文件不存在: {extracted_sig_path}")
                            else:
                                debug_logger.warning(f"压缩包中没有找到签名文件，但继续安装主补丁文件")
                        else:
                            debug_logger.info(f"{self.game_version} 不需要签名文件，跳过签名文件处理")

                update_progress(100, f"{self.game_version} 补丁文件解压完成")
                self.finished.emit(True, "", self.game_version)
        except (py7zr.Bad7zFile, FileNotFoundError, Exception) as e:
            try:
                self.progress.emit(100, f"处理 {self.game_version} 的补丁文件失败")
            except Exception:
                pass
            self.finished.emit(False, f"\n文件操作失败，请重试\n\n【错误信息】：{e}\n", self.game_version) 

 