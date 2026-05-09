# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import importlib.util

_SPEC_PATH = Path(SPECPATH).resolve()
ROOT = _SPEC_PATH.parent if _SPEC_PATH.is_dir() else _SPEC_PATH.parent.parent


def data_pair(source: str, target: str):
    path = ROOT / source
    if path.exists():
        return [(str(path), target)]
    return []


datas = []
datas += data_pair("autoee_demo/web_static", "autoee_demo/web_static")
datas += data_pair("specs", "specs")
datas += data_pair("agents", "agents")
datas += data_pair("skills", "skills")
datas += data_pair("safety", "safety")
datas += data_pair("reports/templates", "reports/templates")

hiddenimports = [
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
]
if importlib.util.find_spec("webview") is not None:
    hiddenimports.append("webview")

a = Analysis(
    [str(ROOT / "autoee_demo" / "web_launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt5.QtWebEngineWidgets",
        "PyQt5.QtWebEngineCore",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AutoEE",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AutoEE",
)
