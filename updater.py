import argparse
import os
import shutil
import sys
import tempfile
import time
import zipfile


def _safe_rmtree(path: str) -> None:
    try:
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install-dir", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--app-exe", required=True)
    args = parser.parse_args()

    install_dir = os.path.abspath(args.install_dir)
    package = os.path.abspath(args.package)
    app_exe = args.app_exe

    time.sleep(1.5)

    if not os.path.exists(package):
        return 1

    backup_dir = install_dir + ".backup"
    temp_dir = tempfile.mkdtemp(prefix="saydut_launcher_update_")

    try:
        with zipfile.ZipFile(package, "r") as archive:
            archive.extractall(temp_dir)

        if os.path.exists(backup_dir):
            _safe_rmtree(backup_dir)
        if os.path.exists(install_dir):
            shutil.move(install_dir, backup_dir)

        shutil.move(temp_dir, install_dir)
        _safe_rmtree(package)
        _safe_rmtree(backup_dir)

        exe_path = os.path.join(install_dir, app_exe)
        if os.path.exists(exe_path):
            os.startfile(exe_path)
        return 0
    except Exception:
        if os.path.exists(install_dir):
            _safe_rmtree(install_dir)
        if os.path.exists(backup_dir):
            shutil.move(backup_dir, install_dir)
        return 2
    finally:
        _safe_rmtree(temp_dir)


if __name__ == "__main__":
    raise SystemExit(main())
