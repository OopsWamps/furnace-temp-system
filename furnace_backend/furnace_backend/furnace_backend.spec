# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

# 项目根目录
project_root = Path.cwd()

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / 'config'), 'config'),
        (str(project_root / 'heating_bilstm.pth'), '.'),
        (str(project_root / 'heating_feat_scaler.pkl'), '.'),
        (str(project_root / 'heating_target_scaler.pkl'), '.'),
        (str(project_root / 'cooling_bilstm.pth'), '.'),
        (str(project_root / 'cooling_feat_scaler.pkl'), '.'),
        (str(project_root / 'cooling_target_scaler.pkl'), '.'),
        (str(project_root / 'holding_bilstm.pth'), '.'),
        (str(project_root / 'holding_feat_scaler.pkl'), '.'),
        (str(project_root / 'holding_target_scaler.pkl'), '.'),
    ],
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'fastapi.middleware',
        'sqlalchemy',
        'sqlalchemy.dialects',
        'sqlalchemy.dialects.postgresql',
        'asyncpg',
        'psycopg2',
        'yaml',
        'loguru',
        'pydantic',
        'pydantic_settings',
        'pandas',
        'numpy',
        'torch',
        'sklearn',
        'joblib',
        'alembic',
        'httpx',
        'passlib',
        'jose',
    ],
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
    name='furnace_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
