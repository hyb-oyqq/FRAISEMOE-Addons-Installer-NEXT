# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# 获取spec文件所在目录的绝对路径
SPEC_ROOT = os.path.dirname(os.path.abspath(SPEC))
ICON_PATH = os.path.join(SPEC_ROOT, 'assets', 'images', 'ICO', 'icon.ico')

# 收集所有子模块
hiddenimports = []
hiddenimports += collect_submodules('workers')
hiddenimports += collect_submodules('core')
hiddenimports += collect_submodules('core.managers')
hiddenimports += collect_submodules('core.handlers')
hiddenimports += collect_submodules('ui')
hiddenimports += collect_submodules('ui.components')
hiddenimports += collect_submodules('utils')
hiddenimports += collect_submodules('config')

# PySide6 相关隐藏导入
hiddenimports += ['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets']

a = Analysis(
    ['Main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('data', 'data'),
        ('config', 'config'),
        ('bin', 'bin'),
        ('ui', 'ui'),
        ('workers', 'workers'),
        ('core', 'core'),
        ('utils', 'utils'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FRAISEMOE_Addons_Installer_NEXT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH,
)
