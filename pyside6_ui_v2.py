import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests
from PySide6.QtCore import QThread, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QLinearGradient, QPainter, QRadialGradient
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWidgets import QGraphicsDropShadowEffect


PROGRAMS_URL = "https://www.saydut.com/static/programs.json"
INSTALL_ROOT = r"C:\\Saydut"
LAUNCHER_DIR = os.path.join(INSTALL_ROOT, "launcher")
DOWNLOAD_DIR = os.path.join(LAUNCHER_DIR, "downloads")
TEMP_DIR = os.path.join(LAUNCHER_DIR, "temp")
INSTALLED_PATH = os.path.join(LAUNCHER_DIR, "installed.json")
PROGRAMS_CACHE_PATH = os.path.join(LAUNCHER_DIR, "programs_cache.json")


@dataclass
class Program:
    id: str
    name: str
    slug: str
    version: str
    category: str
    description: str
    exe_name: str
    download_url: str
    github_url: str
    theme_accent: str
    theme_text: str


class GlowBackground(QWidget):
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0b1324"))

        glow1 = QRadialGradient(120, 80, 320)
        glow1.setColorAt(0.0, QColor(56, 189, 248, 110))
        glow1.setColorAt(0.6, QColor(56, 189, 248, 35))
        glow1.setColorAt(1.0, QColor(11, 19, 36, 0))
        painter.fillRect(self.rect(), glow1)

        glow2 = QRadialGradient(self.width() - 120, 140, 380)
        glow2.setColorAt(0.0, QColor(99, 102, 241, 100))
        glow2.setColorAt(0.6, QColor(99, 102, 241, 30))
        glow2.setColorAt(1.0, QColor(11, 19, 36, 0))
        painter.fillRect(self.rect(), glow2)

        glow3 = QRadialGradient(self.width() * 0.5, self.height() - 80, 420)
        glow3.setColorAt(0.0, QColor(236, 72, 153, 80))
        glow3.setColorAt(0.6, QColor(236, 72, 153, 24))
        glow3.setColorAt(1.0, QColor(11, 19, 36, 0))
        painter.fillRect(self.rect(), glow3)

        painter.setPen(QColor(30, 41, 59, 60))
        step = 48
        for x in range(0, self.width(), step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), step):
            painter.drawLine(0, y, self.width(), y)

        super().paintEvent(event)


class AnimatedHeader(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def _tick(self) -> None:
        self._phase = (self._phase + 1) % 3
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        if self._phase == 0:
            gradient.setColorAt(0.0, QColor("#0ea5e9"))
            gradient.setColorAt(0.5, QColor("#6366f1"))
            gradient.setColorAt(1.0, QColor("#ec4899"))
        elif self._phase == 1:
            gradient.setColorAt(0.0, QColor("#22d3ee"))
            gradient.setColorAt(0.5, QColor("#8b5cf6"))
            gradient.setColorAt(1.0, QColor("#f97316"))
        else:
            gradient.setColorAt(0.0, QColor("#38bdf8"))
            gradient.setColorAt(0.5, QColor("#14b8a6"))
            gradient.setColorAt(1.0, QColor("#f43f5e"))
        painter.fillRect(self.rect(), gradient)
        super().paintEvent(event)


class StatPill(QLabel):
    def __init__(self, title: str, value: str) -> None:
        super().__init__(f"{title}  {value}")
        self.setStyleSheet(
            "background:rgba(15,23,42,0.5); color:#e2e8f0; border:none;"
            "border-radius:12px; padding:6px 10px; font-weight:700;"
        )


class StatusPill(QLabel):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setStyleSheet(
            "background:#0f172a; color:#e2e8f0; border:none; "
            "border-radius:12px; padding:4px 10px; font-weight:700;"
        )


class ShimmerBadge(QLabel):
    def __init__(self, text: str, accent: str) -> None:
        super().__init__(text)
        self._accent = accent
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(450)
        self._tick()

    def _tick(self) -> None:
        self._phase = (self._phase + 1) % 3
        color = self._accent if self._phase == 0 else "#1f2937"
        text = "#f8fafc" if self._phase == 0 else "#e2e8f0"
        self.setStyleSheet(
            f"background:{color}; color:{text}; border-radius:12px; padding:4px 10px; font-weight:700;"
        )


def button_style(
    bg: str,
    hover: str,
    text: str = "#e2e8f0",
    border: str = "none",
    radius: int = 14,
    padding: str = "8px 12px",
    weight: int = 700,
) -> str:
    return (
        f"QPushButton{{background:{bg};color:{text};border:{border};border-radius:{radius}px;"
        f"padding:{padding};font-weight:{weight};}}"
        f"\nQPushButton:hover{{background:{hover};}}"
    )


class ProgramCard(QFrame):
    clicked = Signal(str)

    def __init__(self, program: Program) -> None:
        super().__init__()
        self.program = program
        self._badge: Optional[QLabel] = None
        self._selected = False

        self.setObjectName("ProgramCard")
        self.setStyleSheet(
            "QFrame#ProgramCard{background:rgba(24, 32, 52, 0.85); border:none; border-radius:20px;}"
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(program.theme_accent))
        shadow.setOffset(0, 10)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        accent = QFrame()
        accent.setFixedHeight(6)
        accent.setStyleSheet(f"background:{program.theme_accent}; border-radius:6px;")
        layout.addWidget(accent)

        title = QLabel(program.name)
        title.setStyleSheet("color:#f8fafc; font-size:16px; font-weight:700; background:transparent;")
        layout.addWidget(title)

        desc = QLabel(program.description)
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#94a3b8; font-size:12px; background:transparent;")
        layout.addWidget(desc)

        footer = QHBoxLayout()
        footer.addWidget(StatusPill(program.version))
        self._badge = StatusPill("NEW")
        footer.addWidget(self._badge)
        footer.addStretch()
        layout.addLayout(footer)

        btn = QPushButton("Detaylar")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            button_style(program.theme_accent, "#0ea5e9", text="#ffffff", radius=14, padding="8px 12px")
        )
        btn.clicked.connect(lambda: self.clicked.emit(program.id))
        layout.addWidget(btn)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.clicked.emit(self.program.id)
        super().mousePressEvent(event)

    def set_status(self, status: str) -> None:
        if status == "GUNCELLE":
            badge = ShimmerBadge("GUNCELLE", self.program.theme_accent)
            self._replace_badge(badge)
        elif status == "KURULU":
            self._badge.setText("KURULU")
            self._badge.setStyleSheet(
                "background:#0f766e; color:#d1fae5; border-radius:12px; padding:4px 10px; font-weight:700;"
            )
        else:
            self._badge.setText("YENI")
            self._badge.setStyleSheet(
                "background:#1f2937; color:#e2e8f0; border-radius:12px; padding:4px 10px; font-weight:700;"
            )

    def _replace_badge(self, badge: QLabel) -> None:
        layout = self.layout()
        if not layout:
            return
        footer = layout.itemAt(3)
        if not footer or not footer.layout():
            return
        footer.layout().replaceWidget(self._badge, badge)
        self._badge.deleteLater()
        self._badge = badge

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        shadow = self.graphicsEffect()
        if isinstance(shadow, QGraphicsDropShadowEffect):
            shadow.setBlurRadius(36 if selected else 24)


class InstallerWorker(QThread):
    status = Signal(str)
    progress = Signal(float, int, int)
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, program: Program, auto_run: bool) -> None:
        super().__init__()
        self.program = program
        self.auto_run = auto_run

    def run(self) -> None:  # noqa: N802
        ensure_dirs()
        download_path = os.path.join(DOWNLOAD_DIR, f"{self.program.id}.zip")
        temp_dir = os.path.join(TEMP_DIR, self.program.id)
        install_dir = os.path.join(INSTALL_ROOT, self.program.id)
        backup_dir = install_dir + ".backup"
        stage = "download"

        try:
            self.status.emit("Downloading...")
            with requests.get(self.program.download_url, stream=True, timeout=30) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                downloaded = 0
                chunk_size = 1024 * 256
                with open(download_path, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if not chunk:
                            continue
                        handle.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            self.progress.emit(downloaded / total, downloaded, total)

            stage = "extract"
            self.status.emit("Extracting...")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            os.makedirs(temp_dir, exist_ok=True)
            with zipfile.ZipFile(download_path, "r") as archive:
                archive.extractall(temp_dir)

            stage = "backup"
            self.status.emit("Preparing install...")
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir, ignore_errors=True)
            if os.path.exists(install_dir):
                shutil.move(install_dir, backup_dir)

            stage = "install"
            self.status.emit("Installing...")
            shutil.move(temp_dir, install_dir)

            stage = "validate"
            exe_path = os.path.join(install_dir, self.program.exe_name)
            if not os.path.exists(exe_path):
                exe_path = find_executable(install_dir, self.program.exe_name)
            if not exe_path:
                raise RuntimeError("Executable not found after install.")

            stage = "shortcut"
            create_shortcut(exe_path, self.program.name)

            stage = "cleanup"
            if os.path.exists(download_path):
                os.remove(download_path)
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir, ignore_errors=True)

            if self.auto_run:
                subprocess.Popen(exe_path, cwd=os.path.dirname(exe_path))

            self.finished.emit({"version": self.program.version, "exe_path": exe_path})
        except Exception as exc:  # noqa: BLE001
            message = f"{str(exc)} (stage: {stage})"
            if os.path.exists(install_dir):
                shutil.rmtree(install_dir, ignore_errors=True)
            if os.path.exists(backup_dir):
                shutil.move(backup_dir, install_dir)
            self.failed.emit(message)


class LauncherWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Saydut Programlar")
        self.resize(1320, 780)
        self.setStyleSheet("QLabel{background:transparent; border:none;}")

        self.programs: List[Program] = []
        self.cards: Dict[str, ProgramCard] = {}
        self.selected_program: Optional[Program] = None
        self.installed: Dict[str, Dict[str, str]] = load_installed()
        self.worker: Optional[InstallerWorker] = None
        self.last_download_stats = {"time": None, "bytes": 0}
        self.view_mode = "grid"

        root = GlowBackground()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = AnimatedHeader()
        header.setFixedHeight(160)
        header.setStyleSheet("border-radius:26px;")
        header_shadow = QGraphicsDropShadowEffect(header)
        header_shadow.setBlurRadius(36)
        header_shadow.setColor(QColor(0, 0, 0, 130))
        header_shadow.setOffset(0, 12)
        header.setGraphicsEffect(header_shadow)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 20, 24, 20)
        header_layout.setSpacing(10)

        title = QLabel("Saydut Programlar")
        title.setStyleSheet("color:#f8fafc; font-size:32px; font-weight:800;")
        title.setContentsMargins(0, 0, 0, 6)
        subtitle = QLabel("Modern, hizli ve guvenli yazilimlarin merkezi")
        subtitle.setStyleSheet("color:#e2e8f0; font-size:12px;")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        stats = QHBoxLayout()
        stats.addWidget(StatPill("Uygulama", "7"))
        stats.addWidget(StatPill("Kurulu", str(len(self.installed))))
        stats.addWidget(StatPill("Guncelleme", "1"))
        stats.addStretch()
        header_layout.addLayout(stats)
        layout.addWidget(header)

        hero = QFrame()
        hero.setStyleSheet(
            "background:rgba(15,23,42,0.35); border:none; border-radius:20px;"
        )
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 16, 20, 16)
        hero_layout.setSpacing(16)

        hero_text = QVBoxLayout()
        hero_title = QLabel("Arac setin her zaman guncel.")
        hero_title.setStyleSheet("color:#f8fafc; font-size:20px; font-weight:800;")
        hero_desc = QLabel("Saydut uygulamalarini tek yerden kur, guncelle ve ac.")
        hero_desc.setStyleSheet("color:#94a3b8; font-size:12px;")
        hero_desc.setWordWrap(True)
        hero_text.addWidget(hero_title)
        hero_text.addWidget(hero_desc)
        hero_layout.addLayout(hero_text)
        hero_layout.addStretch()

        hero_cta = QPushButton("Tumunu Guncelle")
        hero_cta.setCursor(Qt.PointingHandCursor)
        hero_cta.setStyleSheet(
            button_style("#38bdf8", "#0ea5e9", text="#0b1120", radius=14, padding="10px 16px", weight=800)
        )
        hero_layout.addWidget(hero_cta)
        layout.addWidget(hero)

        body = QHBoxLayout()

        left_panel = QFrame()
        left_panel.setStyleSheet(
            "background:rgba(17, 24, 39, 0.9); border:none; border-radius:24px;"
        )
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(14)

        top = QHBoxLayout()
        apps_title = QLabel("Uygulamalar")
        apps_title.setStyleSheet("color:#e2e8f0; font-size:16px; font-weight:700;")
        top.addWidget(apps_title)
        top.addStretch()
        left_layout.addLayout(top)

        segment = QHBoxLayout()
        self.grid_button = QPushButton("Grid")
        self.grid_button.setCursor(Qt.PointingHandCursor)
        self.grid_button.setStyleSheet(
            button_style("#38bdf8", "#0ea5e9", text="#0b1120", radius=12, padding="6px 12px", weight=700)
        )
        self.grid_button.clicked.connect(lambda: self.set_view_mode("grid"))
        segment.addWidget(self.grid_button)

        self.list_button = QPushButton("Liste")
        self.list_button.setCursor(Qt.PointingHandCursor)
        self.list_button.setStyleSheet(
            button_style("#1f2937", "#334155", text="#e2e8f0", radius=12, padding="6px 12px", weight=600)
        )
        self.list_button.clicked.connect(lambda: self.set_view_mode("list"))
        segment.addWidget(self.list_button)
        segment.addStretch()
        left_layout.addLayout(segment)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            "QScrollArea{border:none; background:transparent;}"
            "QScrollBar:vertical{background:transparent;width:10px;margin:6px 0 6px 0;}"
            "QScrollBar::handle:vertical{background:#334155;border-radius:5px;min-height:30px;}"
            "QScrollBar::handle:vertical:hover{background:#475569;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;background:transparent;}"
            "QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{background:transparent;}"
        )
        self.scroll_content = QWidget()
        self.grid = QGridLayout(self.scroll_content)
        self.grid.setSpacing(14)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.scroll_content)
        left_layout.addWidget(self.scroll)

        right_panel = QFrame()
        right_panel.setFixedWidth(340)
        right_panel.setStyleSheet(
            "background:rgba(17, 24, 39, 0.92); border:none; border-radius:24px;"
        )
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(14)

        self.detail_title = QLabel("Secili Uygulama")
        self.detail_title.setStyleSheet("color:#f8fafc; font-size:18px; font-weight:700;")
        right_layout.addWidget(self.detail_title)

        self.detail_pill = QLabel("HAZIR")
        self.detail_pill.setStyleSheet(
            "background:#0f172a; color:#e2e8f0; border:none; border-radius:12px;"
            "padding:6px 10px; font-weight:700;"
        )
        right_layout.addWidget(self.detail_pill)

        self.preview = QFrame()
        self.preview.setFixedHeight(140)
        self.preview.setStyleSheet(
            "background:rgba(15,23,42,0.4); border:none; border-radius:16px;"
        )
        right_layout.addWidget(self.preview)

        self.detail_desc = QLabel("Uygulama detaylari ve surum notlari burada gorunur.")
        self.detail_desc.setWordWrap(True)
        self.detail_desc.setStyleSheet("color:#94a3b8; font-size:12px;")
        right_layout.addWidget(self.detail_desc)

        actions = QHBoxLayout()
        self.install_button = QPushButton("Yukle")
        self.install_button.setStyleSheet(
            button_style("#38bdf8", "#0ea5e9", text="#0b1120", radius=14, padding="10px 14px", weight=700)
        )
        self.install_button.clicked.connect(self.handle_install)
        actions.addWidget(self.install_button)

        self.launch_button = QPushButton("Ac")
        self.launch_button.setStyleSheet(
            button_style("#0f172a", "#111827", text="#e2e8f0", border="1px solid #334155", radius=14, padding="10px 14px", weight=600)
        )
        self.launch_button.clicked.connect(self.launch_selected)
        actions.addWidget(self.launch_button)
        right_layout.addLayout(actions)

        quick = QHBoxLayout()
        for label in ["Tumunu Guncelle", "Tumunu Kur", "Temizle"]:
            btn = QPushButton(label)
            btn.setStyleSheet(
                button_style("#1f2937", "#334155", text="#e2e8f0", radius=12, padding="6px 10px", weight=600)
            )
            quick.addWidget(btn)
        right_layout.addLayout(quick)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(
            "QProgressBar{background:#0f172a;border:none;border-radius:12px;height:10px;}"
            "QProgressBar::chunk{background:#38bdf8;border-radius:12px;}"
        )
        right_layout.addWidget(self.progress)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color:#94a3b8; font-size:11px; background:transparent;")
        right_layout.addWidget(self.progress_label)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet(
            "background:#0f172a; color:#e2e8f0; border:none; border-radius:12px;"
        )
        right_layout.addWidget(self.log_box, 1)

        self.github_button = QPushButton("GitHub")
        self.github_button.setStyleSheet(
            button_style("#111827", "#1f2937", text="#e2e8f0", radius=14, padding="10px 14px", weight=600)
        )
        self.github_button.clicked.connect(self.open_github)
        right_layout.addWidget(self.github_button)

        body.addWidget(left_panel, 1)
        body.addSpacing(18)
        body.addWidget(right_panel)
        layout.addLayout(body)

        self.setCentralWidget(root)
        self.setFont(QFont("Segoe UI Variable", 10))

        self.load_programs()

    def log(self, text: str) -> None:
        self.log_box.append(text)

    def load_programs(self) -> None:
        try:
            programs = fetch_programs()
            self.programs = programs
            self.render_programs()
        except Exception as exc:  # noqa: BLE001
            cached = load_programs_from_cache()
            if cached:
                self.programs = cached
                self.render_programs()
            else:
                self.log(f"Programs list could not be loaded: {exc}")

    def render_programs(self) -> None:
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.cards = {}

        columns = 2 if self.view_mode == "grid" else 1
        for index, program in enumerate(self.programs):
            card = ProgramCard(program)
            card.clicked.connect(self.select_program)
            card.set_status(self.get_status(program))
            self.cards[program.id] = card
            self.grid.addWidget(card, index // columns, index % columns)

        if self.programs and not self.selected_program:
            self.select_program(self.programs[0].id)

    def select_program(self, program_id: str) -> None:
        program = next((item for item in self.programs if item.id == program_id), None)
        if not program:
            return
        self.selected_program = program
        for pid, card in self.cards.items():
            card.set_selected(pid == program_id)
        self.detail_title.setText(program.name)
        self.detail_desc.setText(program.description)
        self.detail_pill.setText(program.category.upper())
        self.launch_button.setEnabled(program.id in self.installed)
        self.detail_status_update()

    def set_view_mode(self, mode: str) -> None:
        self.view_mode = mode
        if mode == "grid":
            self.grid_button.setStyleSheet(
                button_style("#38bdf8", "#0ea5e9", text="#0b1120", radius=12, padding="6px 12px", weight=700)
            )
            self.list_button.setStyleSheet(
                button_style("#1f2937", "#334155", text="#e2e8f0", radius=12, padding="6px 12px", weight=600)
            )
        else:
            self.grid_button.setStyleSheet(
                button_style("#1f2937", "#334155", text="#e2e8f0", radius=12, padding="6px 12px", weight=600)
            )
            self.list_button.setStyleSheet(
                button_style("#38bdf8", "#0ea5e9", text="#0b1120", radius=12, padding="6px 12px", weight=700)
            )
        self.render_programs()

    def detail_status_update(self) -> None:
        if not self.selected_program:
            self.progress_label.setText("")
            return
        self.progress_label.setText(self.get_detail_status(self.selected_program))

    def handle_install(self) -> None:
        if not self.selected_program:
            return
        if self.worker and self.worker.isRunning():
            return
        program = self.selected_program
        self.last_download_stats = {"time": time.time(), "bytes": 0}
        kill_process(program.exe_name)
        self.worker = InstallerWorker(program, auto_run=True)
        self.worker.status.connect(self.on_status)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.install_button.setEnabled(False)
        self.worker.start()

    def on_status(self, text: str) -> None:
        self.progress_label.setText(text)
        self.log(text)

    def on_progress(self, value: float, downloaded: int, total: int) -> None:
        self.progress.setValue(int(value * 100))
        now = time.time()
        last_time = self.last_download_stats["time"]
        last_bytes = self.last_download_stats["bytes"]
        speed = None
        eta = None
        if last_time:
            elapsed = max(now - last_time, 0.001)
            delta = max(downloaded - last_bytes, 0)
            speed = delta / elapsed
            remaining = max(total - downloaded, 0)
            eta = remaining / speed if speed else None
        self.last_download_stats = {"time": now, "bytes": downloaded}
        speed_text = f"{format_bytes(speed)}/s" if speed else "--/s"
        eta_text = format_eta(eta)
        percent = int((downloaded / total) * 100) if total else 0
        self.progress_label.setText(
            f"Downloading... {percent}% - {speed_text} - ETA {eta_text}"
        )

    def on_finished(self, installed: dict) -> None:
        if self.selected_program:
            self.installed[self.selected_program.id] = installed
            save_installed(self.installed)
            card = self.cards.get(self.selected_program.id)
            if card:
                card.set_status(self.get_status(self.selected_program))
            self.detail_status_update()
        self.progress_label.setText("Install completed.")
        self.install_button.setEnabled(True)

    def on_failed(self, message: str) -> None:
        self.progress_label.setText("Install failed.")
        self.log(f"Error: {message}")
        self.install_button.setEnabled(True)

    def get_status(self, program: Program) -> str:
        installed = self.installed.get(program.id)
        if not installed:
            return "YENI"
        if version_tuple(program.version) > version_tuple(installed.get("version", "")):
            return "GUNCELLE"
        return "KURULU"

    def get_detail_status(self, program: Program) -> str:
        installed = self.installed.get(program.id)
        if not installed:
            return "Yuklu degil"
        installed_version = installed.get("version", "")
        if version_tuple(program.version) > version_tuple(installed_version):
            return f"Guncelleme var: {installed_version} -> {program.version}"
        return f"Kurulu: {installed_version}"

    def launch_selected(self) -> None:
        if not self.selected_program:
            return
        installed = self.installed.get(self.selected_program.id)
        if not installed:
            return
        exe_path = installed.get("exe_path")
        if exe_path and os.path.exists(exe_path):
            subprocess.Popen(exe_path, cwd=os.path.dirname(exe_path))

    def open_github(self) -> None:
        if not self.selected_program:
            return
        QDesktopServices.openUrl(QUrl(self.selected_program.github_url))


def ensure_dirs() -> None:
    os.makedirs(INSTALL_ROOT, exist_ok=True)
    os.makedirs(LAUNCHER_DIR, exist_ok=True)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)


def write_launcher_hint() -> None:
    hint_path = os.path.join(INSTALL_ROOT, "launcher_path.txt")
    try:
        if getattr(sys, "frozen", False):
            launcher_path = os.path.abspath(sys.executable)
        else:
            launcher_path = os.path.abspath(sys.argv[0])
        if launcher_path:
            with open(hint_path, "w", encoding="utf-8") as handle:
                handle.write(launcher_path)
    except OSError:
        pass


def format_bytes(num_bytes: Optional[float]) -> str:
    if not num_bytes or num_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def format_eta(seconds: Optional[float]) -> str:
    if seconds is None or seconds <= 0:
        return "--:--"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def version_tuple(version: str) -> Tuple[int, ...]:
    raw = version.strip().lstrip("vV")
    if not raw:
        return (0,)
    parts = []
    for piece in raw.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def load_installed() -> Dict[str, Dict[str, str]]:
    if not os.path.exists(INSTALLED_PATH):
        return {}
    try:
        with open(INSTALLED_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_installed(data: Dict[str, Dict[str, str]]) -> None:
    with open(INSTALLED_PATH, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def parse_programs(payload: dict) -> List[Program]:
    programs = []
    for item in payload.get("programs", []):
        theme = item.get("theme", {})
        programs.append(
            Program(
                id=item["id"],
                name=item["name"],
                slug=item.get("slug", item["id"]),
                version=item["version"],
                category=item.get("category", "general"),
                description=item.get("description", ""),
                exe_name=item["exe_name"],
                download_url=item["download_url"],
                github_url=item["github_url"],
                theme_accent=theme.get("accent", "#38bdf8"),
                theme_text=theme.get("accent_text", "#e2e8f0"),
            )
        )
    return programs


def fetch_programs() -> List[Program]:
    response = requests.get(PROGRAMS_URL, timeout=20)
    response.raise_for_status()
    payload = response.json()
    cache_programs(payload)
    return parse_programs(payload)


def load_programs_from_cache() -> Optional[List[Program]]:
    if not os.path.exists(PROGRAMS_CACHE_PATH):
        return None
    try:
        with open(PROGRAMS_CACHE_PATH, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return parse_programs(payload)
    except (OSError, json.JSONDecodeError):
        return None


def cache_programs(payload: dict) -> None:
    try:
        with open(PROGRAMS_CACHE_PATH, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
    except OSError:
        pass


def find_executable(root_dir: str, exe_name: str) -> Optional[str]:
    target_lower = exe_name.lower()
    for root, _, files in os.walk(root_dir):
        for name in files:
            if name.lower() == target_lower:
                return os.path.join(root, name)
    return None


def kill_process(exe_name: str) -> None:
    subprocess.run(["taskkill", "/IM", exe_name, "/F"], capture_output=True)


def ps_escape(value: str) -> str:
    return value.replace("'", "''")


def create_shortcut(target_path: str, shortcut_name: str) -> None:
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.exists(desktop):
        return
    lnk_path = os.path.join(desktop, f"{shortcut_name}.lnk")
    target_path = os.path.abspath(target_path)
    working_dir = os.path.dirname(target_path)
    command = (
        "$WshShell = New-Object -ComObject WScript.Shell;"
        f"$Shortcut = $WshShell.CreateShortcut('{ps_escape(lnk_path)}');"
        f"$Shortcut.TargetPath = '{ps_escape(target_path)}';"
        f"$Shortcut.WorkingDirectory = '{ps_escape(working_dir)}';"
        "$Shortcut.Save();"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True)


def main() -> None:
    ensure_dirs()
    write_launcher_hint()
    app = QApplication(sys.argv)
    window = LauncherWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

