"""
RAM Cleaner Module UI
System dashboard + RAM optimization + Disk temp cleaner
"""
import os
import platform
import ctypes
import shutil
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QScrollArea, QCheckBox,
)

import psutil

from shared import (
    Colors, GlowButton,
    ModernCard, ModernProgressBar,
    ModernTextBox, create_separator,
)

PROCESS_SET_QUOTA = 0x0100
PROCESS_QUERY_INFORMATION = 0x0400


class RAMCleanWorker(QThread):
    log = Signal(str)
    done = Signal(float)

    def run(self):
        cleaned_mb = 0.0
        self.log.emit("RAM temizleme başlatıldı...")
        for proc in psutil.process_iter(['pid']):
            try:
                pid = proc.info['pid']
                p = psutil.Process(pid)
                mem_before = p.memory_info().wset
                h = ctypes.windll.kernel32.OpenProcess(
                    PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION, False, pid)
                if h:
                    ctypes.windll.psapi.EmptyWorkingSet(h)
                    ctypes.windll.kernel32.CloseHandle(h)
                    mem_after = p.memory_info().wset
                    diff = mem_before - mem_after
                    if diff > 1024 * 1024:
                        cleaned_mb += diff / (1024 * 1024)
            except Exception:
                pass
        self.log.emit(f"Toplam kurtarılan: {cleaned_mb:.1f} MB")
        self.done.emit(cleaned_mb)


class DiskScanWorker(QThread):
    log = Signal(str)
    result = Signal(list)

    def run(self):
        self.log.emit("Disk taranıyor...")
        targets = [
            ("Kullanıcı Temp", os.environ.get("TEMP")),
            ("Windows Temp", os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Temp")),
            ("Prefetch", os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Prefetch")),
        ]
        results = []
        for name, path in targets:
            if not path or not os.path.exists(path):
                continue
            size = count = 0
            try:
                for root, dirs, files in os.walk(path):
                    for f in files:
                        try:
                            fp = os.path.join(root, f)
                            size += os.path.getsize(fp)
                            count += 1
                        except Exception:
                            pass
            except Exception:
                pass
            if size > 0:
                results.append((name, path, size, count))
        self.result.emit(results)


class DiskCleanWorker(QThread):
    log = Signal(str)
    done = Signal(int, float)

    def __init__(self, paths):
        super().__init__()
        self.paths = paths

    def run(self):
        freed = deleted = 0
        for path in self.paths:
            self.log.emit(f"Temizleniyor: {path}")
            try:
                for root, dirs, files in os.walk(path):
                    for f in files:
                        try:
                            fp = os.path.join(root, f)
                            s = os.path.getsize(fp)
                            os.remove(fp)
                            freed += s
                            deleted += 1
                        except Exception:
                            pass
                    for d in dirs:
                        try:
                            shutil.rmtree(os.path.join(root, d))
                        except Exception:
                            pass
            except Exception:
                pass
        self.done.emit(deleted, freed / (1024 * 1024))


TAB_STYLE = f"""
    QTabWidget::pane {{ border:none; background:rgba(17,24,39,0.92); border-radius:16px; }}
    QTabBar::tab {{ background:{Colors.BG_SECONDARY}; color:{Colors.TEXT_SECONDARY};
        padding:12px 24px; border:none; border-top-left-radius:12px;
        border-top-right-radius:12px; margin-right:4px; font-weight:600; }}
    QTabBar::tab:selected {{ background:rgba(17,24,39,0.92); color:{Colors.TEXT_PRIMARY}; }}
    QTabBar::tab:hover {{ background:rgba(30,41,59,0.8); }}
"""

CHK_STYLE = f"""
    QCheckBox {{ color:{Colors.TEXT_PRIMARY}; font-weight:600; spacing:8px; }}
    QCheckBox::indicator {{ width:18px; height:18px; border-radius:4px;
        border:2px solid rgba(71,85,105,0.5); background:{Colors.BG_SECONDARY}; }}
    QCheckBox::indicator:checked {{ background:#f59e0b; border-color:#f59e0b; }}
"""


class RAMCleanerWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._worker = None
        self._disk_scan_worker = None
        self._disk_clean_worker = None
        self._scan_results = []
        self._check_boxes = []
        self._setup_ui()
        self._start_refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header = ModernCard()
        hl = QVBoxLayout(header)
        hl.setContentsMargins(20, 16, 20, 16)
        title = QLabel("🧹 Saydut System Care")
        title.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:24px;font-weight:800;background:transparent;")
        hl.addWidget(title)
        uname = platform.uname()
        info = QLabel(f"{uname.node} | {uname.system} {uname.release} | CPU: {psutil.cpu_count(logical=False)} çekirdek")
        info.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:11px;background:transparent;")
        hl.addWidget(info)
        layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_STYLE)
        self.tabs.addTab(self._create_dashboard(), "Sistem Özeti")
        self.tabs.addTab(self._create_ram_tab(), "RAM Optimize")
        self.tabs.addTab(self._create_disk_tab(), "Disk Temizle")
        layout.addWidget(self.tabs, 1)

    def _make_bar_card(self, label_text):
        card = ModernCard()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(8)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:14px;font-weight:600;background:transparent;")
        cl.addWidget(lbl)
        bar = ModernProgressBar()
        bar.setFixedHeight(14)
        cl.addWidget(bar)
        return card, lbl, bar

    # ── Dashboard ────────────────────────────────────────────────────
    def _create_dashboard(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(20)

        c1, self.lbl_cpu, self.bar_cpu = self._make_bar_card("İşlemci (CPU): %0")
        lay.addWidget(c1)
        c2, self.lbl_ram, self.bar_ram = self._make_bar_card("Bellek (RAM): %0")
        lay.addWidget(c2)
        c3, self.lbl_disk, self.bar_disk = self._make_bar_card("Disk (C:): %0")
        lay.addWidget(c3)
        lay.addStretch()
        return w

    # ── RAM Tab ──────────────────────────────────────────────────────
    def _create_ram_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        info = QLabel("Kullanılmayan bellek alanlarını geri kazanır (EmptyWorkingSet API)")
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:12px;background:transparent;")
        lay.addWidget(info)

        self.ram_bar2 = ModernProgressBar()
        self.ram_bar2.setFixedHeight(18)
        lay.addWidget(self.ram_bar2)

        self.ram_status = QLabel("Hazır")
        self.ram_status.setAlignment(Qt.AlignCenter)
        self.ram_status.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:14px;font-weight:600;background:transparent;")
        lay.addWidget(self.ram_status)

        self.btn_clean_ram = GlowButton("🧹 RAM'i Şimdi Temizle", accent="#8b5cf6")
        self.btn_clean_ram.setFixedHeight(48)
        self.btn_clean_ram.clicked.connect(self._on_clean_ram)
        lay.addWidget(self.btn_clean_ram)

        self.ram_log = ModernTextBox()
        self.ram_log.setReadOnly(True)
        lay.addWidget(self.ram_log, 1)
        return w

    # ── Disk Tab ─────────────────────────────────────────────────────
    def _create_disk_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        btn_row = QHBoxLayout()
        self.btn_scan = GlowButton("🔍 Sistemi Tara", accent="#f59e0b")
        self.btn_scan.clicked.connect(self._on_scan_disk)
        btn_row.addWidget(self.btn_scan)
        self.btn_clean_disk = GlowButton("🗑️ Seçilenleri Temizle", accent="#ef4444")
        self.btn_clean_disk.setEnabled(False)
        self.btn_clean_disk.clicked.connect(self._on_clean_disk)
        btn_row.addWidget(self.btn_clean_disk)
        lay.addLayout(btn_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self._disk_container = QWidget()
        self._disk_layout = QVBoxLayout(self._disk_container)
        self._disk_layout.setContentsMargins(0, 0, 0, 0)
        self._disk_layout.addStretch()
        scroll.setWidget(self._disk_container)
        lay.addWidget(scroll, 1)

        self.disk_log = ModernTextBox()
        self.disk_log.setReadOnly(True)
        self.disk_log.setMaximumHeight(120)
        lay.addWidget(self.disk_log)
        return w

    # ── Timer ────────────────────────────────────────────────────────
    def _start_refresh(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(2000)
        self._refresh()

    def _refresh(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            self.lbl_cpu.setText(f"İşlemci (CPU): %{cpu:.0f}")
            self.bar_cpu.setValue(int(cpu))
            ram = psutil.virtual_memory().percent
            self.lbl_ram.setText(f"Bellek (RAM): %{ram:.0f}")
            self.bar_ram.setValue(int(ram))
            self.ram_bar2.setValue(int(ram))
            self.ram_status.setText(f"Mevcut Yük: %{ram:.0f}")
            disk = psutil.disk_usage("C:\\").percent
            self.lbl_disk.setText(f"Disk (C:): %{disk:.0f}")
            self.bar_disk.setValue(int(disk))
        except Exception:
            pass

    # ── Actions ──────────────────────────────────────────────────────
    def _on_clean_ram(self):
        self.btn_clean_ram.setEnabled(False)
        self.btn_clean_ram.setText("Temizleniyor...")
        self._worker = RAMCleanWorker()
        self._worker.log.connect(lambda m: self.ram_log.append(m))
        self._worker.done.connect(self._ram_done)
        self._worker.start()

    def _ram_done(self, cleaned: float):
        self.btn_clean_ram.setEnabled(True)
        self.btn_clean_ram.setText("🧹 RAM'i Şimdi Temizle")
        self.ram_log.append(f"✅ Tamamlandı! {cleaned:.1f} MB kurtarıldı.")
        self._refresh()

    def _on_scan_disk(self):
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("Taranıyor...")
        self.btn_clean_disk.setEnabled(False)
        self._check_boxes.clear()
        for i in reversed(range(self._disk_layout.count())):
            item = self._disk_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self._disk_scan_worker = DiskScanWorker()
        self._disk_scan_worker.log.connect(lambda m: self.disk_log.append(m))
        self._disk_scan_worker.result.connect(self._scan_done)
        self._disk_scan_worker.start()

    def _scan_done(self, results):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("🔍 Sistemi Tara")
        self._scan_results = results
        if not results:
            self.disk_log.append("Temiz! Gereksiz dosya bulunamadı.")
            return
        self.disk_log.append(f"{len(results)} kategori bulundu.")
        for name, path, size, count in results:
            chk = QCheckBox(f"{name} ({count} dosya) - {size/(1024*1024):.1f} MB")
            chk.setChecked(True)
            chk.setStyleSheet(CHK_STYLE)
            self._disk_layout.insertWidget(self._disk_layout.count() - 1, chk)
            self._check_boxes.append((chk, path))
        self.btn_clean_disk.setEnabled(True)

    def _on_clean_disk(self):
        paths = [p for chk, p in self._check_boxes if chk.isChecked()]
        if not paths:
            return
        self.btn_clean_disk.setEnabled(False)
        self.btn_clean_disk.setText("Siliniyor...")
        self._disk_clean_worker = DiskCleanWorker(paths)
        self._disk_clean_worker.log.connect(lambda m: self.disk_log.append(m))
        self._disk_clean_worker.done.connect(self._disk_done)
        self._disk_clean_worker.start()

    def _disk_done(self, deleted, freed_mb):
        self.btn_clean_disk.setText("🗑️ Seçilenleri Temizle")
        self.disk_log.append(f"✅ {deleted} dosya silindi, {freed_mb:.1f} MB kazanıldı.")
        for i in reversed(range(self._disk_layout.count())):
            item = self._disk_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self._check_boxes.clear()
