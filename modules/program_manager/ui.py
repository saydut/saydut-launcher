"""
Program Manager Module UI
Faithful port of interface.py + logic.py - ALL 7 pages preserved
Winget programs, Chocolatey, Tweaks, Updates, Uninstall, System Info, About
"""
import os
import sys
import json
import subprocess
import threading
import platform
import socket
from typing import Optional, List

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QCheckBox, QFrame, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QStackedWidget,
)

import psutil

from shared import (
    Colors, GlowButton, OutlineButton, ModernInput,
    ModernCard, ModernTextBox, create_separator, create_spacer,
)

try:
    import winreg
    _WINREG = True
except ImportError:
    _WINREG = False


# ── Helpers ──────────────────────────────────────────────────────
def _get_module_dir():
    return os.path.dirname(os.path.abspath(__file__))


def load_json_data(filename):
    """Load JSON from data/ folder"""
    try:
        path = os.path.join(_get_module_dir(), 'data', filename)
        if not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


# ── Styles ───────────────────────────────────────────────────────
SIDEBAR_BTN_STYLE = f"""
    QPushButton {{
        background: transparent;
        color: {Colors.TEXT_SECONDARY};
        text-align: left;
        padding: 12px 18px;
        border: none;
        border-radius: 10px;
        font-size: 14px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background: rgba(30, 41, 59, 0.8);
        color: {Colors.TEXT_PRIMARY};
    }}
"""

SIDEBAR_BTN_ACTIVE = f"""
    QPushButton {{
        background: rgba(6, 182, 212, 0.15);
        color: {Colors.ACCENT_BLUE};
        text-align: left;
        padding: 12px 18px;
        border: none;
        border-radius: 10px;
        border-left: 3px solid {Colors.ACCENT_BLUE};
        font-size: 14px;
        font-weight: 600;
    }}
"""

TABLE_STYLE = f"""
    QTableWidget {{ background:{Colors.BG_SECONDARY}; color:{Colors.TEXT_PRIMARY};
        border:none; border-radius:12px; gridline-color:rgba(71,85,105,0.3); }}
    QTableWidget::item {{ padding:6px 12px; }}
    QTableWidget::item:selected {{ background:rgba(6,182,212,0.3); }}
    QHeaderView::section {{ background:{Colors.BG_PRIMARY}; color:{Colors.TEXT_PRIMARY};
        border:none; padding:8px 12px; font-weight:700; }}
"""

SCROLL_STYLE = """
    QScrollArea { border: none; background: transparent; }
    QScrollBar:vertical { background: transparent; width: 8px; }
    QScrollBar::handle:vertical { background: rgba(71,85,105,0.5); border-radius: 4px; min-height: 20px; }
    QScrollBar::handle:vertical:hover { background: rgba(71,85,105,0.8); }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""

CHECKBOX_STYLE = f"""
    QCheckBox {{ color: {Colors.TEXT_PRIMARY}; font-weight: 600; spacing: 8px; background: transparent; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px;
        border: 2px solid rgba(71,85,105,0.6); background: transparent; }}
    QCheckBox::indicator:checked {{ background: #06b6d4; border-color: #06b6d4; }}
    QCheckBox::indicator:hover {{ border-color: #06b6d4; }}
"""

SWITCH_STYLE = f"""
    QCheckBox {{ color: {Colors.TEXT_PRIMARY}; font-weight: 600; spacing: 8px; background: transparent; }}
    QCheckBox::indicator {{ width: 40px; height: 20px; border-radius: 10px;
        border: 2px solid rgba(71,85,105,0.6); background: rgba(30,41,59,0.8); }}
    QCheckBox::indicator:checked {{ background: #ef4444; border-color: #ef4444; }}
"""


# ── Workers ──────────────────────────────────────────────────────
class WingetInstallWorker(QThread):
    log = Signal(str)
    done = Signal()

    def __init__(self, app_ids: list):
        super().__init__()
        self.app_ids = app_ids

    def run(self):
        total = len(self.app_ids)
        for i, app_id in enumerate(self.app_ids):
            self.log.emit(f"[{i+1}/{total}] Kuruluyor: {app_id}...")
            try:
                cmd = f'start /wait cmd /c "winget install --id {app_id} -e --accept-package-agreements --accept-source-agreements"'
                subprocess.run(cmd, shell=True, creationflags=0x08000000)
                self.log.emit(f"✅ {app_id} tamamlandı")
            except Exception as e:
                self.log.emit(f"❌ Hata ({app_id}): {e}")
        self.log.emit("Tüm işlemler tamamlandı.")
        self.done.emit()


class ChocoInstallWorker(QThread):
    log = Signal(str)
    done = Signal()

    def __init__(self, packages: list):
        super().__init__()
        self.packages = packages

    def run(self):
        pkgs = " ".join(self.packages)
        self.log.emit(f"Kuruluyor: {pkgs}...")
        try:
            cmd = f'start /wait cmd /c "choco install {pkgs} -y & pause"'
            subprocess.run(cmd, shell=True, creationflags=0x08000000)
            self.log.emit("İşlem tamamlandı.")
        except Exception as e:
            self.log.emit(f"❌ Hata: {e}")
        self.done.emit()


class UpdateScanWorker(QThread):
    result = Signal(list)
    status = Signal(str)

    def run(self):
        self.status.emit("Taranıyor... Lütfen bekleyin.")
        try:
            cmd = "winget upgrade --include-unknown"
            p = subprocess.run(cmd, capture_output=True, text=True, shell=True,
                               encoding='utf-8', errors='ignore', creationflags=0x08000000)
            lines = p.stdout.splitlines()
            updates = []
            start = False
            for line in lines:
                if "Name" in line and "Id" in line:
                    start = True
                    continue
                if start and "-----" in line:
                    continue
                if start and len(line) > 10:
                    parts = line.split()
                    if len(parts) >= 3:
                        updates.append(line)
            self.result.emit(updates)
        except Exception as e:
            self.result.emit([f"Hata: {e}"])


class InstalledProgramsWorker(QThread):
    result = Signal(list)

    def run(self):
        programs = set()
        if not _WINREG:
            self.result.emit([])
            return
        paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ]
        hives = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
        for hive in hives:
            for path in paths:
                try:
                    with winreg.OpenKey(hive, path) as key:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            try:
                                sub_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, sub_name) as sub:
                                    try:
                                        name = winreg.QueryValueEx(sub, "DisplayName")[0]
                                        if name:
                                            programs.add(name)
                                    except OSError:
                                        pass
                            except OSError:
                                continue
                except OSError:
                    continue
        self.result.emit(sorted(programs))


class TweakApplyWorker(QThread):
    log = Signal(str)
    done = Signal()

    def __init__(self, tweaks: list):
        super().__init__()
        self.tweaks = tweaks

    def run(self):
        for tweak in self.tweaks:
            name = tweak.get("name", "?")
            t_type = tweak.get("type", "")
            self.log.emit(f"İşlem başlatılıyor: {name}...")
            try:
                if t_type == "script":
                    cmd = tweak.get("command", "")
                    subprocess.run(["powershell", "-Command", cmd], shell=True, creationflags=0x08000000)
                elif t_type == "winget":
                    wid = tweak.get("id", "")
                    subprocess.run(f"winget install --id {wid} -e --silent", shell=True, creationflags=0x08000000)
                elif t_type in ("external_exe", "external_zip"):
                    self.log.emit(f"  {name}: Harici araç (manuel indirme gerekli)")
                elif t_type == "local_exe":
                    self.log.emit(f"  {name}: Yerel araç (assets klasöründen)")
                self.log.emit(f"✅ {name} tamamlandı.")
            except Exception as e:
                self.log.emit(f"❌ Hata ({name}): {e}")
        self.log.emit("İşlemler tamamlandı.")
        self.done.emit()


# ── Main Widget ──────────────────────────────────────────────────
class ProgramManagerWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._workers = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Sidebar ──
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"QFrame {{ background:{Colors.BG_SECONDARY}; border-right:1px solid rgba(71,85,105,0.3); }}")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(12, 20, 12, 20)
        sb_layout.setSpacing(4)

        logo = QLabel("SAYDUT\nYAZILIM")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:20px;font-weight:800;background:transparent;")
        sb_layout.addWidget(logo)

        ver = QLabel("Program Yöneticisi")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:11px;background:transparent;")
        sb_layout.addWidget(ver)
        sb_layout.addSpacing(20)

        self.sidebar_buttons = []
        pages = [
            ("🚀  Programlar", 0),
            ("🍫  Chocolatey", 1),
            ("🛠️  Tweakler", 2),
            ("🔄  Uygulama Güncelle", 3),
            ("🗑️  Kaldır", 4),
            ("💻  Sistem", 5),
            ("ℹ️  Hakkında", 6),
        ]

        for text, idx in pages:
            btn = QPushButton(text)
            btn.setStyleSheet(SIDEBAR_BTN_STYLE)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _c=False, i=idx: self._show_page(i))
            sb_layout.addWidget(btn)
            self.sidebar_buttons.append(btn)

        sb_layout.addStretch()
        layout.addWidget(sidebar)

        # ── Content Area ──
        content = QFrame()
        content.setStyleSheet("QFrame { background:transparent; }")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(20, 20, 20, 20)
        cl.setSpacing(0)

        self.stack = QStackedWidget()

        self.stack.addWidget(self._create_programs_page())
        self.stack.addWidget(self._create_choco_page())
        self.stack.addWidget(self._create_tweaks_page())
        self.stack.addWidget(self._create_updates_page())
        self.stack.addWidget(self._create_uninstall_page())
        self.stack.addWidget(self._create_system_page())
        self.stack.addWidget(self._create_about_page())

        cl.addWidget(self.stack)

        self.log_label = QLabel("Hazır")
        self.log_label.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:11px;background:transparent;padding:8px 4px;")
        cl.addWidget(self.log_label)

        layout.addWidget(content, 1)
        self._show_page(0)

    def _show_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.sidebar_buttons):
            btn.setStyleSheet(SIDEBAR_BTN_ACTIVE if i == index else SIDEBAR_BTN_STYLE)
        if index == 5:
            self._refresh_system()

    def _log(self, text):
        self.log_label.setText(text)

    # ═══════════════════════════════════════════════════════════════
    # 1. PROGRAMLAR (Winget)
    # ═══════════════════════════════════════════════════════════════
    def _create_programs_page(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        title = QLabel("Popüler Programlar (Winget)")
        title.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:22px;font-weight:800;background:transparent;")
        lay.addWidget(title)

        desc = QLabel("Winget (Microsoft Resmi Kaynağı) üzerinden güvenli, reklamsız ve hızlı kurulum.")
        desc.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:12px;background:transparent;")
        lay.addWidget(desc)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLL_STYLE)
        container = QWidget()
        container.setStyleSheet("background:transparent;")
        self._prog_grid = QVBoxLayout(container)
        self._prog_grid.setContentsMargins(0, 0, 0, 0)
        self._prog_grid.setSpacing(0)

        self._prog_checkboxes = []
        self._load_programs()

        self._prog_grid.addStretch()
        scroll.setWidget(container)
        lay.addWidget(scroll, 1)

        btn_frame = QHBoxLayout()
        self._prog_select_all = False

        btn_sel = OutlineButton("Tümünü Seç")
        btn_sel.clicked.connect(self._toggle_select_all_progs)
        self._btn_select_progs = btn_sel
        btn_frame.addWidget(btn_sel)

        btn_frame.addStretch()

        self._prog_status = QLabel("Hazır")
        self._prog_status.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:12px;background:transparent;")
        btn_frame.addWidget(self._prog_status)

        btn_install = GlowButton("Seçilenleri Kur", accent="#22c55e")
        btn_install.setFixedHeight(44)
        btn_install.clicked.connect(self._install_selected_progs)
        self._btn_install_progs = btn_install
        btn_frame.addWidget(btn_install)

        lay.addLayout(btn_frame)
        return w

    def _load_programs(self):
        data = load_json_data("programs.json")
        if not data:
            data = [
                {"name": "Google Chrome", "id": "Google.Chrome", "description": "Web tarayıcısı."},
                {"name": "Discord", "id": "Discord.Discord", "description": "Sohbet uygulaması."},
                {"name": "WinRAR", "id": "RARLab.WinRAR", "description": "Arşiv yöneticisi."},
                {"name": "VLC", "id": "VideoLAN.VLC", "description": "Medya oynatıcı."},
                {"name": "Steam", "id": "Valve.Steam", "description": "Oyun platformu."},
            ]

        row_layout = None
        col = 0
        for item in data:
            if col == 0:
                row_layout = QHBoxLayout()
                row_layout.setSpacing(12)

            card = ModernCard()
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 10, 12, 10)
            cl.setSpacing(4)

            cb = QCheckBox(item['name'])
            cb.setStyleSheet(CHECKBOX_STYLE)
            cb.setProperty("app_id", item['id'])
            cl.addWidget(cb)
            self._prog_checkboxes.append(cb)

            if item.get('description'):
                d = QLabel(item['description'])
                d.setWordWrap(True)
                d.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:11px;background:transparent;")
                cl.addWidget(d)

            row_layout.addWidget(card)
            col += 1

            if col >= 3:
                self._prog_grid.addLayout(row_layout)
                col = 0

        if col > 0 and row_layout:
            while col < 3:
                row_layout.addStretch()
                col += 1
            self._prog_grid.addLayout(row_layout)

    def _toggle_select_all_progs(self):
        self._prog_select_all = not self._prog_select_all
        for cb in self._prog_checkboxes:
            cb.setChecked(self._prog_select_all)
        self._btn_select_progs.setText("Seçimi Kaldır" if self._prog_select_all else "Tümünü Seç")

    def _install_selected_progs(self):
        selected = [cb.property("app_id") for cb in self._prog_checkboxes if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir program seçin.")
            return
        self._btn_install_progs.setEnabled(False)
        self._btn_install_progs.setText("Kuruluyor...")
        worker = WingetInstallWorker(selected)
        worker.log.connect(lambda m: (self._prog_status.setText(m), self._log(m)))
        worker.done.connect(lambda: (self._btn_install_progs.setEnabled(True), self._btn_install_progs.setText("Seçilenleri Kur")))
        self._workers.append(worker)
        worker.start()

    # ═══════════════════════════════════════════════════════════════
    # 2. CHOCOLATEY
    # ═══════════════════════════════════════════════════════════════
    def _create_choco_page(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        title = QLabel("Chocolatey Paketleri")
        title.setStyleSheet(f"color:#d2691e;font-size:22px;font-weight:800;background:transparent;")
        lay.addWidget(title)

        self._choco_installed = self._check_choco()
        status_text = "Yüklü ✅" if self._choco_installed else "Yüklü Değil ❌"
        status_color = "#10b981" if self._choco_installed else "#ef4444"
        self._choco_status = QLabel(f"Durum: {status_text}")
        self._choco_status.setStyleSheet(f"color:{status_color};font-size:13px;font-weight:700;background:transparent;")
        lay.addWidget(self._choco_status)

        self._btn_install_choco = None
        if not self._choco_installed:
            btn = GlowButton("Chocolatey'i Şimdi Yükle", accent="#d2691e")
            btn.clicked.connect(self._install_chocolatey)
            lay.addWidget(btn)
            self._btn_install_choco = btn

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLL_STYLE)
        container = QWidget()
        container.setStyleSheet("background:transparent;")
        grid = QVBoxLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        self._choco_checkboxes = []
        data = load_json_data("chocolatey.json")
        if not data:
            data = [{"name": "NodeJS", "package": "nodejs"}, {"name": "Python", "package": "python"}, {"name": "Git", "package": "git"}]

        row_layout = None
        col = 0
        for item in data:
            if col == 0:
                row_layout = QHBoxLayout()
                row_layout.setSpacing(10)

            cb = QCheckBox(item['name'])
            cb.setStyleSheet(CHECKBOX_STYLE)
            cb.setProperty("pkg_name", item['package'])
            if not self._choco_installed:
                cb.setEnabled(False)
            row_layout.addWidget(cb)
            self._choco_checkboxes.append(cb)
            col += 1

            if col >= 4:
                grid.addLayout(row_layout)
                col = 0

        if col > 0 and row_layout:
            grid.addLayout(row_layout)

        grid.addStretch()
        scroll.setWidget(container)
        lay.addWidget(scroll, 1)

        btn_frame = QHBoxLayout()
        self._choco_select_all = False
        btn_sel = OutlineButton("Tümünü Seç")
        btn_sel.clicked.connect(self._toggle_select_all_choco)
        if not self._choco_installed:
            btn_sel.setEnabled(False)
        self._btn_select_choco = btn_sel
        btn_frame.addWidget(btn_sel)

        btn_run = GlowButton("Seçilenleri Kur", accent="#d2691e")
        btn_run.setFixedHeight(44)
        btn_run.clicked.connect(self._run_choco_install)
        if not self._choco_installed:
            btn_run.setEnabled(False)
        self._btn_choco_run = btn_run
        btn_frame.addWidget(btn_run, 1)

        lay.addLayout(btn_frame)

        self._choco_log = QLabel("")
        self._choco_log.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:11px;background:transparent;")
        lay.addWidget(self._choco_log)
        return w

    def _check_choco(self):
        try:
            subprocess.run(["choco", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x08000000)
            return True
        except FileNotFoundError:
            return False

    def _install_chocolatey(self):
        if self._btn_install_choco:
            self._btn_install_choco.setEnabled(False)
            self._btn_install_choco.setText("Yükleniyor...")

        def run():
            try:
                cmd = 'Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString(\'https://community.chocolatey.org/install.ps1\'))'
                subprocess.run(['powershell', '-Command', cmd], shell=True, creationflags=0x08000000)
            except Exception:
                pass

        threading.Thread(target=run, daemon=True).start()
        self._choco_log.setText("Chocolatey kurulumu başlatıldı. Tamamlandıktan sonra programı yeniden başlatın.")

    def _toggle_select_all_choco(self):
        self._choco_select_all = not self._choco_select_all
        for cb in self._choco_checkboxes:
            cb.setChecked(self._choco_select_all)
        self._btn_select_choco.setText("Seçimi Kaldır" if self._choco_select_all else "Tümünü Seç")

    def _run_choco_install(self):
        selected = [cb.property("pkg_name") for cb in self._choco_checkboxes if cb.isChecked()]
        if not selected:
            return
        self._btn_choco_run.setEnabled(False)
        worker = ChocoInstallWorker(selected)
        worker.log.connect(lambda m: (self._choco_log.setText(m), self._log(m)))
        worker.done.connect(lambda: self._btn_choco_run.setEnabled(True))
        self._workers.append(worker)
        worker.start()

    # ═══════════════════════════════════════════════════════════════
    # 3. TWEAKLER
    # ═══════════════════════════════════════════════════════════════
    def _create_tweaks_page(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        title = QLabel("Sistem İyileştirmeleri (Tweaks)")
        title.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:22px;font-weight:800;background:transparent;")
        lay.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLL_STYLE)
        container = QWidget()
        container.setStyleSheet("background:transparent;")
        grid = QVBoxLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)

        self._tweak_switches = []
        data = load_json_data("tweaks.json")
        for item in data:
            row = ModernCard()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(14, 12, 14, 12)

            cb = QCheckBox(item['name'])
            cb.setStyleSheet(SWITCH_STYLE)
            cb.setProperty("tweak_data", item)
            rl.addWidget(cb)

            if item.get('description'):
                d = QLabel(item['description'])
                d.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:11px;background:transparent;")
                d.setWordWrap(True)
                rl.addWidget(d, 1)

            self._tweak_switches.append(cb)
            grid.addWidget(row)

        grid.addStretch()
        scroll.setWidget(container)
        lay.addWidget(scroll, 1)

        btn_frame = QHBoxLayout()
        self._tweak_select_all = False
        btn_sel = OutlineButton("Tümünü Seç")
        btn_sel.clicked.connect(self._toggle_select_all_tweaks)
        self._btn_select_tweaks = btn_sel
        btn_frame.addWidget(btn_sel)

        btn_apply = GlowButton("Seçilenleri Uygula", accent="#ef4444")
        btn_apply.setFixedHeight(44)
        btn_apply.clicked.connect(self._apply_tweaks)
        self._btn_apply_tweaks = btn_apply
        btn_frame.addWidget(btn_apply, 1)

        lay.addLayout(btn_frame)

        self._tweak_status = QLabel("Hazır")
        self._tweak_status.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:11px;background:transparent;")
        lay.addWidget(self._tweak_status)
        return w

    def _toggle_select_all_tweaks(self):
        self._tweak_select_all = not self._tweak_select_all
        for cb in self._tweak_switches:
            cb.setChecked(self._tweak_select_all)
        self._btn_select_tweaks.setText("Seçimi Kaldır" if self._tweak_select_all else "Tümünü Seç")

    def _apply_tweaks(self):
        selected = [cb.property("tweak_data") for cb in self._tweak_switches if cb.isChecked()]
        if not selected:
            return
        confirm = QMessageBox.question(
            self, "Dikkat",
            "Seçilen ayarlar sisteme uygulanacak.\nSistem Geri Yükleme noktası oluşturulması önerilir.",
            QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return
        self._btn_apply_tweaks.setEnabled(False)
        worker = TweakApplyWorker(selected)
        worker.log.connect(lambda m: (self._tweak_status.setText(m), self._log(m)))
        worker.done.connect(lambda: self._btn_apply_tweaks.setEnabled(True))
        self._workers.append(worker)
        worker.start()

    # ═══════════════════════════════════════════════════════════════
    # 4. GÜNCELLEMELER
    # ═══════════════════════════════════════════════════════════════
    def _create_updates_page(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        title = QLabel("Yazılım Güncellemeleri")
        title.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:22px;font-weight:800;background:transparent;")
        lay.addWidget(title)

        desc = QLabel("Yüklü programları tarar ve güncellenecekleri listeler.")
        desc.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:12px;background:transparent;")
        lay.addWidget(desc)

        top = QHBoxLayout()
        self._btn_scan = GlowButton("Taramayı Başlat", accent=Colors.ACCENT_BLUE)
        self._btn_scan.clicked.connect(self._scan_updates)
        top.addWidget(self._btn_scan)

        self._update_loading = QLabel("")
        self._update_loading.setStyleSheet(f"color:#3b82f6;font-size:12px;background:transparent;")
        top.addWidget(self._update_loading, 1)
        lay.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLL_STYLE)
        self._update_container = QWidget()
        self._update_container.setStyleSheet("background:transparent;")
        self._update_layout = QVBoxLayout(self._update_container)
        self._update_layout.setContentsMargins(0, 0, 0, 0)
        self._update_layout.setSpacing(4)
        self._update_layout.addStretch()
        scroll.setWidget(self._update_container)
        lay.addWidget(scroll, 1)

        bottom = QHBoxLayout()
        self._update_select_all = False
        btn_sel = OutlineButton("Tümünü Seç")
        btn_sel.clicked.connect(self._toggle_select_all_updates)
        self._btn_select_updates = btn_sel
        bottom.addWidget(btn_sel)

        self._btn_run_updates = GlowButton("Seçilenleri Güncelle", accent="#22c55e")
        self._btn_run_updates.setEnabled(False)
        self._btn_run_updates.clicked.connect(self._run_updates)
        bottom.addWidget(self._btn_run_updates)
        lay.addLayout(bottom)

        self._update_checkboxes = []
        return w

    def _scan_updates(self):
        self._btn_scan.setEnabled(False)
        self._btn_run_updates.setEnabled(False)

        for i in reversed(range(self._update_layout.count())):
            item = self._update_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self._update_checkboxes.clear()

        worker = UpdateScanWorker()
        worker.status.connect(lambda m: self._update_loading.setText(m))
        worker.result.connect(self._on_scan_done)
        self._workers.append(worker)
        worker.start()

    def _on_scan_done(self, updates):
        self._btn_scan.setEnabled(True)
        self._update_loading.setText("")

        if not updates:
            lbl = QLabel("Sisteminiz güncel! Güncelleme bulunamadı.")
            lbl.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:13px;padding:20px;background:transparent;")
            self._update_layout.insertWidget(0, lbl)
            return

        for line in updates:
            full_line = line.strip()
            parts = full_line.split()
            app_id = None
            version_index = -1
            for i, part in enumerate(parts):
                if i > 0 and len(part) > 3 and part[0].isdigit() and '.' in part:
                    version_index = i
                    break
            if version_index > 0:
                app_id = parts[version_index - 1]
            else:
                possible = [p for p in parts if '.' in p and not p[0].isdigit()]
                app_id = possible[0] if possible else (parts[-2] if len(parts) >= 2 else full_line)

            row = ModernCard()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(10, 6, 10, 6)
            cb = QCheckBox(full_line)
            cb.setStyleSheet(f"QCheckBox {{ color:{Colors.TEXT_PRIMARY}; font-family:Consolas; font-size:11px; background:transparent; }}")
            cb.setProperty("app_id", app_id)
            cb.setChecked(True)
            rl.addWidget(cb)
            self._update_checkboxes.append(cb)
            self._update_layout.insertWidget(self._update_layout.count() - 1, row)

        self._btn_run_updates.setEnabled(True)

    def _toggle_select_all_updates(self):
        self._update_select_all = not self._update_select_all
        for cb in self._update_checkboxes:
            cb.setChecked(self._update_select_all)
        self._btn_select_updates.setText("Seçimi Kaldır" if self._update_select_all else "Tümünü Seç")

    def _run_updates(self):
        selected = [cb.property("app_id") for cb in self._update_checkboxes if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, "Uyarı", "Lütfen güncellenecek programları seçin.")
            return
        confirm = QMessageBox.question(
            self, "Onay",
            f"{len(selected)} program güncellenecek. Bu işlem zaman alabilir.\nDevam edilsin mi?",
            QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return
        self._btn_run_updates.setEnabled(False)
        self._btn_run_updates.setText("Güncelleniyor...")

        def update_thread():
            total = len(selected)
            for i, app_id in enumerate(selected):
                self._update_loading.setText(f"Güncelleniyor ({i+1}/{total}): {app_id}...")
                try:
                    cmd = f"winget upgrade --id {app_id} --accept-source-agreements --accept-package-agreements"
                    subprocess.run(f'start /wait cmd /c "{cmd} & echo. & echo Islem Tamamlandi... & timeout /t 3"', shell=True)
                except Exception:
                    pass
            self._update_loading.setText("Tüm güncellemeler tamamlandı.")
            self._btn_run_updates.setEnabled(True)
            self._btn_run_updates.setText("Seçilenleri Güncelle")

        threading.Thread(target=update_thread, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════
    # 5. KALDIRMA
    # ═══════════════════════════════════════════════════════════════
    def _create_uninstall_page(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        title = QLabel("Program Kaldırma Aracı")
        title.setStyleSheet(f"color:#ef4444;font-size:22px;font-weight:800;background:transparent;")
        lay.addWidget(title)

        ctrl = QHBoxLayout()
        self._uninstall_search = ModernInput(placeholder="Program ara...")
        self._uninstall_search.setFixedWidth(300)
        self._uninstall_search.textChanged.connect(self._filter_uninstall_list)
        ctrl.addWidget(self._uninstall_search)

        btn_refresh = OutlineButton("Yenile")
        btn_refresh.clicked.connect(self._refresh_uninstall_list)
        ctrl.addWidget(btn_refresh)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        self._uninstall_table = QTableWidget()
        self._uninstall_table.setColumnCount(1)
        self._uninstall_table.setHorizontalHeaderLabels(["Program Adı"])
        self._uninstall_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._uninstall_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._uninstall_table.setStyleSheet(TABLE_STYLE)
        self._uninstall_table.verticalHeader().setVisible(False)
        lay.addWidget(self._uninstall_table, 1)

        btn_uninstall = GlowButton("🗑️ Seçili Programı Kaldır", accent="#ef4444")
        btn_uninstall.setFixedHeight(44)
        btn_uninstall.clicked.connect(self._uninstall_selected)
        lay.addWidget(btn_uninstall)

        self._uninstall_status = QLabel("")
        self._uninstall_status.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:11px;background:transparent;")
        lay.addWidget(self._uninstall_status)

        self._all_programs = []
        self._refresh_uninstall_list()
        return w

    def _refresh_uninstall_list(self):
        self._uninstall_status.setText("Liste yükleniyor...")
        self._uninstall_table.setRowCount(0)
        worker = InstalledProgramsWorker()
        worker.result.connect(self._on_installed_loaded)
        self._workers.append(worker)
        worker.start()

    def _on_installed_loaded(self, programs):
        self._all_programs = programs
        self._populate_uninstall(programs)
        self._uninstall_status.setText(f"{len(programs)} program bulundu.")

    def _populate_uninstall(self, programs):
        self._uninstall_table.setRowCount(len(programs))
        for i, name in enumerate(programs):
            self._uninstall_table.setItem(i, 0, QTableWidgetItem(name))

    def _filter_uninstall_list(self):
        query = self._uninstall_search.text().lower()
        filtered = [p for p in self._all_programs if query in p.lower()]
        self._populate_uninstall(filtered)

    def _uninstall_selected(self):
        items = self._uninstall_table.selectedItems()
        if not items:
            QMessageBox.warning(self, "Seçim Yok", "Lütfen kaldırılacak bir program seçin.")
            return
        name = items[0].text()
        confirm = QMessageBox.question(
            self, "Onay", f"'{name}' programını kaldırmak istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return

        def run_uninstall():
            self._uninstall_status.setText(f"Kaldırılıyor: {name}...")
            try:
                cmd = f'winget uninstall --name "{name}"'
                subprocess.run(f'start /wait cmd /c "{cmd} & pause"', shell=True)
                self._uninstall_status.setText("İşlem tamamlandı.")
                self._refresh_uninstall_list()
            except Exception as e:
                self._uninstall_status.setText(f"Hata: {e}")

        threading.Thread(target=run_uninstall, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════
    # 6. SİSTEM BİLGİSİ
    # ═══════════════════════════════════════════════════════════════
    def _create_system_page(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        title = QLabel("Sistem Raporu")
        title.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:22px;font-weight:800;background:transparent;")
        lay.addWidget(title)

        self._sys_textbox = ModernTextBox()
        self._sys_textbox.setReadOnly(True)
        lay.addWidget(self._sys_textbox, 1)

        btn_refresh = GlowButton("Bilgileri Yenile", accent=Colors.ACCENT_BLUE)
        btn_refresh.clicked.connect(self._refresh_system)
        lay.addWidget(btn_refresh)
        return w

    def _refresh_system(self):
        lines = ["── SİSTEM RAPORU ──"]
        lines.append(f"PC Adı: {socket.gethostname()}")
        lines.append(f"OS: {platform.system()} {platform.release()} ({platform.version()})")
        lines.append(f"İşlemci: {platform.processor()}")
        lines.append(f"Çekirdek: {psutil.cpu_count(logical=False)} Fiziksel / {psutil.cpu_count(logical=True)} Mantıksal")
        mem = psutil.virtual_memory()
        lines.append(f"RAM: {round(mem.total / (1024**3), 2)} GB (Kullanılan: {mem.percent}%)")
        lines.append("")
        lines.append("── DİSKLER ──")
        for part in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(part.mountpoint)
                lines.append(f"{part.device} ({part.fstype}): {round(u.total / (1024**3), 1)} GB Toplam")
            except Exception:
                pass
        self._sys_textbox.setText("\n".join(lines))

    # ═══════════════════════════════════════════════════════════════
    # 7. HAKKINDA
    # ═══════════════════════════════════════════════════════════════
    def _create_about_page(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch()

        card = ModernCard()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(50, 40, 50, 40)
        cl.setSpacing(12)

        title = QLabel("Saydut Program Yöneticisi")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:26px;font-weight:800;background:transparent;")
        cl.addWidget(title)

        ver = QLabel("v2.0.0 Pro Edition")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:14px;background:transparent;")
        cl.addWidget(ver)

        cl.addSpacing(16)

        desc = QLabel(
            "Bu araç, sistem yönetimini kolaylaştırmak, programları güncellemek,\n"
            "gereksiz dosyaları temizlemek ve Windows ayarlarını optimize etmek\n"
            "için tasarlanmıştır.\n\n"
            "Geliştirici: Kemal Saydut\n"
            "Lisans: MIT Open Source"
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:13px;background:transparent;")
        cl.addWidget(desc)

        lay.addWidget(card)
        lay.addStretch()
        return w
