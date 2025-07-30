import os
import re

class GameDetector:
    """游戏检测器，用于识别游戏目录和版本"""
    
    def __init__(self, game_info, debug_manager=None):
        """初始化游戏检测器
        
        Args:
            game_info: 游戏信息字典，包含各版本的安装路径和可执行文件名
            debug_manager: 调试管理器实例，用于输出调试信息
        """
        self.game_info = game_info
        self.debug_manager = debug_manager
        
    def _is_debug_mode(self):
        """检查是否处于调试模式
        
        Returns:
            bool: 是否处于调试模式
        """
        if hasattr(self.debug_manager, 'ui_manager') and hasattr(self.debug_manager.ui_manager, 'debug_action'):
            return self.debug_manager.ui_manager.debug_action.isChecked()
        return False
        
    def identify_game_version(self, game_dir):
        """识别游戏版本
        
        Args:
            game_dir: 游戏目录路径
            
        Returns:
            str: 游戏版本名称，如果不是有效的游戏目录则返回None
        """
        debug_mode = self._is_debug_mode()
        
        if debug_mode:
            print(f"DEBUG: 尝试识别游戏版本: {game_dir}")
            
        # 先通过目录名称进行初步推测（这将作为递归搜索的提示）
        dir_name = os.path.basename(game_dir).lower()
        potential_version = None
        vol_num = None
        
        # 提取卷号或判断是否是After
        if "vol" in dir_name or "vol." in dir_name:
            vol_match = re.search(r"vol(?:\.|\s*)?(\d+)", dir_name)
            if vol_match:
                vol_num = vol_match.group(1)
                potential_version = f"NEKOPARA Vol.{vol_num}"
                if debug_mode:
                    print(f"DEBUG: 从目录名推测游戏版本: {potential_version}, 卷号: {vol_num}")
        elif "after" in dir_name:
            potential_version = "NEKOPARA After"
            if debug_mode:
                print(f"DEBUG: 从目录名推测游戏版本: NEKOPARA After")
        
        # 检查是否为NEKOPARA游戏目录
        # 通过检查游戏可执行文件来识别游戏版本
        for game_version, info in self.game_info.items():
            # 尝试多种可能的可执行文件名变体
            exe_variants = [
                info["exe"],                         # 标准文件名
                info["exe"] + ".nocrack",            # Steam加密版本
                info["exe"].replace(".exe", ""),     # 无扩展名版本
                info["exe"].replace("NEKOPARA", "nekopara").lower(),  # 全小写变体
                info["exe"].lower(),                 # 小写变体
                info["exe"].lower() + ".nocrack",    # 小写变体的Steam加密版本
            ]
            
            # 对于Vol.3可能有特殊名称
            if "Vol.3" in game_version:
                # 增加可能的卷3特定的变体
                exe_variants.extend([
                    "NEKOPARAVol3.exe", 
                    "NEKOPARAVol3.exe.nocrack",
                    "nekoparavol3.exe",
                    "nekoparavol3.exe.nocrack",
                    "nekopara_vol3.exe",
                    "nekopara_vol3.exe.nocrack",
                    "vol3.exe",
                    "vol3.exe.nocrack"
                ])
            
            for exe_variant in exe_variants:
                exe_path = os.path.join(game_dir, exe_variant)
                if os.path.exists(exe_path):
                    if debug_mode:
                        print(f"DEBUG: 通过可执行文件确认游戏版本: {game_version}, 文件: {exe_variant}")
                    return game_version
        
        # 如果没有直接匹配，尝试递归搜索
        if potential_version:
            # 从预测的版本中获取卷号或确认是否是After
            is_after = "After" in potential_version
            if not vol_num and not is_after:
                vol_match = re.search(r"Vol\.(\d+)", potential_version)
                if vol_match:
                    vol_num = vol_match.group(1)
            
            # 递归搜索可执行文件
            for root, dirs, files in os.walk(game_dir):
                for file in files:
                    file_lower = file.lower()
                    if file.endswith('.exe') or file.endswith('.exe.nocrack'):
                        # 检查文件名中是否包含卷号或关键词
                        if ((vol_num and (f"vol{vol_num}" in file_lower or 
                                         f"vol.{vol_num}" in file_lower or 
                                         f"vol {vol_num}" in file_lower)) or
                            (is_after and "after" in file_lower)):
                            if debug_mode:
                                print(f"DEBUG: 通过递归搜索确认游戏版本: {potential_version}, 文件: {file}")
                            return potential_version
        
        # 如果仍然没有找到，基于目录名的推测返回结果
        if potential_version:
            if debug_mode:
                print(f"DEBUG: 基于目录名返回推测的游戏版本: {potential_version}")
            return potential_version
            
        if debug_mode:
            print(f"DEBUG: 无法识别游戏版本: {game_dir}")
            
        return None
    
    def identify_game_directories_improved(self, selected_folder):
        """改进的游戏目录识别，支持大小写不敏感和特殊字符处理
        
        Args:
            selected_folder: 选择的上级目录
            
        Returns:
            dict: 游戏版本到游戏目录的映射
        """
        debug_mode = self._is_debug_mode()
        
        if debug_mode:
            print(f"--- 开始识别目录: {selected_folder} ---")
            
        game_paths = {}
        
        # 获取上级目录中的所有文件夹
        try:
            all_dirs = [d for d in os.listdir(selected_folder) if os.path.isdir(os.path.join(selected_folder, d))]
            if debug_mode:
                print(f"DEBUG: 找到以下子目录: {all_dirs}")
        except Exception as e:
            if debug_mode:
                print(f"DEBUG: 无法读取目录 {selected_folder}: {str(e)}")
            return {}
        
        for game, info in self.game_info.items():
            expected_dir = info["install_path"].split("/")[0]  # 例如 "NEKOPARA Vol. 1"
            expected_exe = info["exe"]  # 标准可执行文件名
            
            if debug_mode:
                print(f"DEBUG: 搜索游戏 {game}, 预期目录: {expected_dir}, 预期可执行文件: {expected_exe}")
            
            # 尝试不同的匹配方法
            found_dir = None
            
            # 1. 精确匹配
            if expected_dir in all_dirs:
                found_dir = expected_dir
                if debug_mode:
                    print(f"DEBUG: 精确匹配成功: {expected_dir}")
            
            # 2. 大小写不敏感匹配
            if not found_dir:
                for dir_name in all_dirs:
                    if expected_dir.lower() == dir_name.lower():
                        found_dir = dir_name
                        if debug_mode:
                            print(f"DEBUG: 大小写不敏感匹配成功: {dir_name}")
                        break
            
            # 3. 更模糊的匹配（允许特殊字符差异）
            if not found_dir:
                # 准备用于模糊匹配的正则表达式模式
                # 替换空格为可选空格或连字符，替换点为可选点
                pattern_text = expected_dir.replace(" ", "[ -]?").replace(".", "\\.?")
                pattern = re.compile(f"^{pattern_text}$", re.IGNORECASE)
                
                for dir_name in all_dirs:
                    if pattern.match(dir_name):
                        found_dir = dir_name
                        if debug_mode:
                            print(f"DEBUG: 模糊匹配成功: {dir_name} 匹配模式 {pattern_text}")
                        break
            
            # 4. 如果还是没找到，尝试更宽松的匹配
            if not found_dir:
                vol_match = re.search(r"vol(?:\.|\s*)?(\d+)", expected_dir, re.IGNORECASE)
                vol_num = None
                if vol_match:
                    vol_num = vol_match.group(1)
                    if debug_mode:
                        print(f"DEBUG: 提取卷号: {vol_num}")
                
                is_after = "after" in expected_dir.lower()
                
                for dir_name in all_dirs:
                    dir_lower = dir_name.lower()
                    
                    # 对于After特殊处理
                    if is_after and "after" in dir_lower:
                        found_dir = dir_name
                        if debug_mode:
                            print(f"DEBUG: After特殊匹配成功: {dir_name}")
                        break
                        
                    # 对于Vol特殊处理
                    if vol_num:
                        # 查找目录名中的卷号
                        dir_vol_match = re.search(r"vol(?:\.|\s*)?(\d+)", dir_lower)
                        if dir_vol_match and dir_vol_match.group(1) == vol_num:
                            found_dir = dir_name
                            if debug_mode:
                                print(f"DEBUG: 卷号匹配成功: {dir_name} 卷号 {vol_num}")
                            break
            
            # 如果找到匹配的目录，验证exe文件是否存在
            if found_dir:
                potential_path = os.path.join(selected_folder, found_dir)
                
                # 尝试多种可能的可执行文件名变体
                # 包括Steam加密版本和其他可能的变体
                exe_variants = [
                    expected_exe,                    # 标准文件名
                    expected_exe + ".nocrack",       # Steam加密版本
                    expected_exe.replace(".exe", ""),# 无扩展名版本
                    # Vol.3的特殊变体，因为它的文件名可能不一样
                    expected_exe.replace("NEKOPARA", "nekopara").lower(),  # 全小写变体
                    expected_exe.lower(),            # 小写变体
                    expected_exe.lower() + ".nocrack", # 小写变体的Steam加密版本
                ]
                
                # 对于Vol.3可能有特殊名称
                if "Vol.3" in game:
                    # 增加可能的卷3特定的变体
                    exe_variants.extend([
                        "NEKOPARAVol3.exe", 
                        "NEKOPARAVol3.exe.nocrack",
                        "nekoparavol3.exe",
                        "nekoparavol3.exe.nocrack",
                        "nekopara_vol3.exe",
                        "nekopara_vol3.exe.nocrack",
                        "vol3.exe",
                        "vol3.exe.nocrack"
                    ])
                
                exe_exists = False
                found_exe = None
                
                # 尝试所有可能的变体
                for exe_variant in exe_variants:
                    exe_path = os.path.join(potential_path, exe_variant)
                    if os.path.exists(exe_path):
                        exe_exists = True
                        found_exe = exe_variant
                        if debug_mode:
                            print(f"DEBUG: 验证成功，找到游戏可执行文件: {exe_variant}")
                        break
                
                # 如果没有直接找到，尝试递归搜索当前目录下的所有可执行文件
                if not exe_exists:
                    # 遍历当前目录下的所有文件和文件夹
                    for root, dirs, files in os.walk(potential_path):
                        for file in files:
                            file_lower = file.lower()
                            # 检查是否是游戏可执行文件（根据关键字）
                            if file.endswith('.exe') or file.endswith('.exe.nocrack'):
                                # 检查文件名中是否包含卷号或关键词
                                if "Vol." in game:
                                    vol_match = re.search(r"Vol\.(\d+)", game)
                                    if vol_match:
                                        vol_num = vol_match.group(1)
                                        if (f"vol{vol_num}" in file_lower or 
                                            f"vol.{vol_num}" in file_lower or 
                                            f"vol {vol_num}" in file_lower):
                                            exe_path = os.path.join(root, file)
                                            exe_exists = True
                                            found_exe = os.path.relpath(exe_path, potential_path)
                                            if debug_mode:
                                                print(f"DEBUG: 通过递归搜索找到游戏可执行文件: {found_exe}")
                                            break
                                elif "After" in game and "after" in file_lower:
                                    exe_path = os.path.join(root, file)
                                    exe_exists = True
                                    found_exe = os.path.relpath(exe_path, potential_path)
                                    if debug_mode:
                                        print(f"DEBUG: 通过递归搜索找到After游戏可执行文件: {found_exe}")
                                    break
                        if exe_exists:
                            break
                
                # 如果找到了可执行文件，将该目录添加到游戏目录列表
                if exe_exists:
                    game_paths[game] = potential_path
                    if debug_mode:
                        print(f"DEBUG: 验证成功，将 {potential_path} 添加为 {game} 的目录")
                else:
                    if debug_mode:
                        print(f"DEBUG: 未找到任何可执行文件变体，游戏 {game} 在 {potential_path} 未找到")
        
        if debug_mode:
            print(f"DEBUG: 最终识别的游戏目录: {game_paths}")
            print(f"--- 目录识别结束 ---")
            
        return game_paths 