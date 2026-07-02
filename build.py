"""
Build script — packages Moltin TypeWriter into a Windows executable using PyInstaller.
Run: python build.py

Steps:
1. Runs PyInstaller to create a one-folder distribution in dist/MoltinTypeWriter/
2. Optionally invokes Inno Setup to create the installer .exe
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build_temp"
APP_NAME = "MoltinTypeWriter"
ENTRY_POINT = str(ROOT / "main.py")
ICON = str(ROOT / "assets" / "icon.ico")


def run(cmd: list[str], **kwargs):
    print(f"\n▶  {' '.join(cmd)}\n")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"✕  Command failed with code {result.returncode}")
        sys.exit(result.returncode)


def build_exe():
    print("=" * 60)
    print("  Moltin TypeWriter — Build Script")
    print("=" * 60)

    # Clean previous build
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    if (DIST_DIR / APP_NAME).exists():
        shutil.rmtree(DIST_DIR / APP_NAME)

    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",                    # No console window
        "--onedir",                      # Folder distribution (faster startup)
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(BUILD_DIR),
        "--icon", ICON,
        "--add-data", f"styles{os.pathsep}styles",          # Include QSS themes
        "--add-data", f"assets{os.pathsep}assets",          # Include icon
        "--add-data", f"example_vault{os.pathsep}example_vault",  # Example vault
        "--hidden-import", "PyQt6.sip",
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "rapidfuzz",
        "--hidden-import", "cryptography",
        "--hidden-import", "requests",
        "--collect-submodules", "services",
        "--collect-submodules", "config",
        "--collect-submodules", "ui",
        "--noconfirm",
        ENTRY_POINT,
    ]

    run(pyinstaller_args, cwd=str(ROOT))
    print(f"\n✓  Executable built: {DIST_DIR / APP_NAME}")


def build_installer():
    """Build installer using Inno Setup (must be installed)."""
    iss_path = ROOT / "installer" / "setup.iss"
    iscc_candidates = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]

    iscc = next((p for p in iscc_candidates if os.path.exists(p)), None)
    if not iscc:
        print("\n⚠  Inno Setup not found. Skipping installer creation.")
        print("   Download from: https://jrsoftware.org/isinfo.php")
        print(f"   Then run manually: ISCC.exe \"{iss_path}\"")
        return

    run([iscc, str(iss_path)])
    installer = list((ROOT / "dist").glob("MoltinTypeWriter-Setup-*.exe"))
    if installer:
        print(f"\n✓  Installer: {installer[0]}")


if __name__ == "__main__":
    build_exe()
    build_installer()
    print("\n🎉  Build complete!")
