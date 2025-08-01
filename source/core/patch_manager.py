import os
import shutil
from PySide6.QtWidgets import QMessageBox

class PatchManager:
    """补丁管理器，用于处理补丁的安装和卸载"""
    
    def __init__(self, app_name, game_info, debug_manager=None):
        """初始化补丁管理器
        
        Args:
            app_name: 应用程序名称，用于显示消息框标题
            game_info: 游戏信息字典，包含各版本的安装路径和可执行文件名
            debug_manager: 调试管理器实例，用于输出调试信息
        """
        self.app_name = app_name
        self.game_info = game_info
        self.debug_manager = debug_manager
        self.installed_status = {}  # 游戏版本的安装状态
        
    def _is_debug_mode(self):
        """检查是否处于调试模式
        
        Returns:
            bool: 是否处于调试模式
        """
        if hasattr(self.debug_manager, 'ui_manager') and hasattr(self.debug_manager.ui_manager, 'debug_action'):
            return self.debug_manager.ui_manager.debug_action.isChecked()
        return False
    
    def initialize_status(self):
        """初始化所有游戏版本的安装状态"""
        self.installed_status = {f"NEKOPARA Vol.{i}": False for i in range(1, 5)}
        self.installed_status["NEKOPARA After"] = False
        
    def update_status(self, game_version, is_installed):
        """更新游戏版本的安装状态
        
        Args:
            game_version: 游戏版本
            is_installed: 是否已安装
        """
        self.installed_status[game_version] = is_installed
        
    def get_status(self, game_version=None):
        """获取游戏版本的安装状态
        
        Args:
            game_version: 游戏版本，如果为None则返回所有状态
            
        Returns:
            bool或dict: 指定版本的安装状态或所有版本的安装状态
        """
        if game_version:
            return self.installed_status.get(game_version, False)
        return self.installed_status
    
    def uninstall_patch(self, game_dir, game_version, silent=False):
        """卸载补丁
        
        Args:
            game_dir: 游戏目录路径
            game_version: 游戏版本
            silent: 是否静默模式(不显示弹窗)
            
        Returns:
            bool: 卸载成功返回True，失败返回False
            dict: 在silent=True时，返回包含卸载结果信息的字典
        """
        debug_mode = self._is_debug_mode()
        
        if game_version not in self.game_info:
            if not silent:
                QMessageBox.critical(
                    None,
                    f"错误 - {self.app_name}",
                    f"\n无法识别游戏版本: {game_version}\n",
                    QMessageBox.StandardButton.Ok,
                )
            return False if not silent else {"success": False, "message": f"无法识别游戏版本: {game_version}", "files_removed": 0}
        
        if debug_mode:
            print(f"DEBUG: 开始卸载 {game_version} 补丁，目录: {game_dir}")
            
        try:
            files_removed = 0
            
            # 获取可能的补丁文件路径
            install_path_base = os.path.basename(self.game_info[game_version]["install_path"])
            patch_file_path = os.path.join(game_dir, install_path_base)
            
            # 尝试查找补丁文件，支持不同大小写
            patch_files_to_check = [
                patch_file_path,
                patch_file_path.lower(),
                patch_file_path.upper(),
                patch_file_path.replace("_", ""),
                patch_file_path.replace("_", "-"),
            ]
            
            # 查找并删除补丁文件
            patch_file_found = False
            for patch_path in patch_files_to_check:
                if os.path.exists(patch_path):
                    patch_file_found = True
                    os.remove(patch_path)
                    files_removed += 1
                    if debug_mode:
                        print(f"DEBUG: 已删除补丁文件: {patch_path}")
            
            if not patch_file_found and debug_mode:
                print(f"DEBUG: 未找到补丁文件，检查了以下路径: {patch_files_to_check}")
                
            # 检查是否有额外的签名文件 (.sig)
            if game_version == "NEKOPARA After":
                for patch_path in patch_files_to_check:
                    sig_file_path = f"{patch_path}.sig"
                    if os.path.exists(sig_file_path):
                        os.remove(sig_file_path)
                        files_removed += 1
                        if debug_mode:
                            print(f"DEBUG: 已删除签名文件: {sig_file_path}")
            
            # 删除patch文件夹
            patch_folders_to_check = [
                os.path.join(game_dir, "patch"),
                os.path.join(game_dir, "Patch"),
                os.path.join(game_dir, "PATCH"),
            ]
            
            for patch_folder in patch_folders_to_check:
                if os.path.exists(patch_folder):
                    shutil.rmtree(patch_folder)
                    files_removed += 1
                    if debug_mode:
                        print(f"DEBUG: 已删除补丁文件夹: {patch_folder}")
            
            # 删除game/patch文件夹
            game_folders = ["game", "Game", "GAME"]
            patch_folders = ["patch", "Patch", "PATCH"]
            
            for game_folder in game_folders:
                for patch_folder in patch_folders:
                    game_patch_folder = os.path.join(game_dir, game_folder, patch_folder)
                    if os.path.exists(game_patch_folder):
                        shutil.rmtree(game_patch_folder)
                        files_removed += 1
                        if debug_mode:
                            print(f"DEBUG: 已删除game/patch文件夹: {game_patch_folder}")
            
            # 删除配置文件
            config_files = ["config.json", "Config.json", "CONFIG.JSON"]
            script_files = ["scripts.json", "Scripts.json", "SCRIPTS.JSON"]
            
            for game_folder in game_folders:
                game_path = os.path.join(game_dir, game_folder)
                if os.path.exists(game_path):
                    # 删除配置文件
                    for config_file in config_files:
                        config_path = os.path.join(game_path, config_file)
                        if os.path.exists(config_path):
                            os.remove(config_path)
                            files_removed += 1
                            if debug_mode:
                                print(f"DEBUG: 已删除配置文件: {config_path}")
                    
                    # 删除脚本文件
                    for script_file in script_files:
                        script_path = os.path.join(game_path, script_file)
                        if os.path.exists(script_path):
                            os.remove(script_path)
                            files_removed += 1
                            if debug_mode:
                                print(f"DEBUG: 已删除脚本文件: {script_path}")
            
            # 更新安装状态
            self.installed_status[game_version] = False
            
            # 在非静默模式且非批量卸载模式下显示卸载成功消息
            if not silent and game_version != "all":
                # 显示卸载成功消息
                if files_removed > 0:
                    QMessageBox.information(
                        None,
                        f"卸载完成 - {self.app_name}",
                        f"\n{game_version} 补丁卸载成功！\n共删除 {files_removed} 个文件/文件夹。\n",
                        QMessageBox.StandardButton.Ok,
                    )
                else:
                    QMessageBox.warning(
                        None,
                        f"警告 - {self.app_name}",
                        f"\n未找到 {game_version} 的补丁文件，可能未安装补丁或已被移除。\n",
                        QMessageBox.StandardButton.Ok,
                    )
            
            # 卸载成功
            if silent:
                return {"success": True, "message": f"{game_version} 补丁卸载成功", "files_removed": files_removed}
            return True
            
        except Exception as e:
            # 在非静默模式且非批量卸载模式下显示卸载失败消息
            if not silent and game_version != "all":
                # 显示卸载失败消息
                error_message = f"\n卸载 {game_version} 补丁时出错：\n\n{str(e)}\n"
                if debug_mode:
                    print(f"DEBUG: 卸载错误 - {str(e)}")
                    
                QMessageBox.critical(
                    None,
                    f"卸载失败 - {self.app_name}",
                    error_message,
                    QMessageBox.StandardButton.Ok,
                )
            
            # 卸载失败
            if silent:
                return {"success": False, "message": f"卸载 {game_version} 补丁时出错: {str(e)}", "files_removed": 0}
            return False
    
    def batch_uninstall_patches(self, game_dirs):
        """批量卸载多个游戏的补丁
        
        Args:
            game_dirs: 游戏版本到游戏目录的映射字典
            
        Returns:
            tuple: (成功数量, 失败数量, 详细结果列表)
        """
        success_count = 0
        fail_count = 0
        debug_mode = self._is_debug_mode()
        results = []
        
        for version, path in game_dirs.items():
            try:
                # 在批量模式下使用静默卸载
                result = self.uninstall_patch(path, version, silent=True)
                
                if isinstance(result, dict):  # 使用了静默模式
                    if result["success"]:
                        success_count += 1
                    else:
                        fail_count += 1
                    results.append({
                        "version": version,
                        "success": result["success"],
                        "message": result["message"],
                        "files_removed": result["files_removed"]
                    })
                else:  # 兼容旧代码，不应该执行到这里
                    if result:
                        success_count += 1
                    else:
                        fail_count += 1
                    results.append({
                        "version": version,
                        "success": result,
                        "message": f"{version} 卸载{'成功' if result else '失败'}",
                        "files_removed": 0
                    })
                    
            except Exception as e:
                if debug_mode:
                    print(f"DEBUG: 卸载 {version} 时出错: {str(e)}")
                fail_count += 1
                results.append({
                    "version": version,
                    "success": False,
                    "message": f"卸载出错: {str(e)}",
                    "files_removed": 0
                })
                
        return success_count, fail_count, results
    
    def show_uninstall_result(self, success_count, fail_count, results=None):
        """显示批量卸载结果
        
        Args:
            success_count: 成功卸载的数量
            fail_count: 卸载失败的数量
            results: 详细结果列表，如果提供，会显示更详细的信息
        """
        result_text = f"\n批量卸载完成！\n成功: {success_count} 个\n失败: {fail_count} 个\n"
        
        # 如果有详细结果，添加到消息中
        if results:
            success_list = [r["version"] for r in results if r["success"]]
            fail_list = [r["version"] for r in results if not r["success"]]
            
            if success_list:
                result_text += f"\n【成功卸载】：\n{chr(10).join(success_list)}\n"
            
            if fail_list:
                result_text += f"\n【卸载失败】：\n{chr(10).join(fail_list)}\n"
        
        QMessageBox.information(
            None,
            f"批量卸载完成 - {self.app_name}",
            result_text,
            QMessageBox.StandardButton.Ok,
        ) 

    def check_patch_installed(self, game_dir, game_version):
        """检查游戏是否已安装补丁
        
        Args:
            game_dir: 游戏目录路径
            game_version: 游戏版本
            
        Returns:
            bool: 如果已安装补丁返回True，否则返回False
        """
        debug_mode = self._is_debug_mode()
        
        if game_version not in self.game_info:
            return False
            
        # 获取可能的补丁文件路径
        install_path_base = os.path.basename(self.game_info[game_version]["install_path"])
        patch_file_path = os.path.join(game_dir, install_path_base)
        
        # 尝试查找补丁文件，支持不同大小写
        patch_files_to_check = [
            patch_file_path,
            patch_file_path.lower(),
            patch_file_path.upper(),
            patch_file_path.replace("_", ""),
            patch_file_path.replace("_", "-"),
        ]
        
        # 查找补丁文件
        for patch_path in patch_files_to_check:
            if os.path.exists(patch_path):
                if debug_mode:
                    print(f"DEBUG: 找到补丁文件: {patch_path}")
                return True
                
        # 检查是否有补丁文件夹
        patch_folders_to_check = [
            os.path.join(game_dir, "patch"),
            os.path.join(game_dir, "Patch"),
            os.path.join(game_dir, "PATCH"),
        ]
        
        for patch_folder in patch_folders_to_check:
            if os.path.exists(patch_folder):
                if debug_mode:
                    print(f"DEBUG: 找到补丁文件夹: {patch_folder}")
                return True
                
        # 检查game/patch文件夹
        game_folders = ["game", "Game", "GAME"]
        patch_folders = ["patch", "Patch", "PATCH"]
        
        for game_folder in game_folders:
            for patch_folder in patch_folders:
                game_patch_folder = os.path.join(game_dir, game_folder, patch_folder)
                if os.path.exists(game_patch_folder):
                    if debug_mode:
                        print(f"DEBUG: 找到game/patch文件夹: {game_patch_folder}")
                    return True
        
        # 检查配置文件
        config_files = ["config.json", "Config.json", "CONFIG.JSON"]
        script_files = ["scripts.json", "Scripts.json", "SCRIPTS.JSON"]
        
        for game_folder in game_folders:
            game_path = os.path.join(game_dir, game_folder)
            if os.path.exists(game_path):
                # 检查配置文件
                for config_file in config_files:
                    config_path = os.path.join(game_path, config_file)
                    if os.path.exists(config_path):
                        if debug_mode:
                            print(f"DEBUG: 找到配置文件: {config_path}")
                        return True
                
                # 检查脚本文件
                for script_file in script_files:
                    script_path = os.path.join(game_path, script_file)
                    if os.path.exists(script_path):
                        if debug_mode:
                            print(f"DEBUG: 找到脚本文件: {script_path}")
                        return True
        
        # 没有找到补丁文件或文件夹
        if debug_mode:
            print(f"DEBUG: {game_version} 在 {game_dir} 中没有安装补丁")
        return False 