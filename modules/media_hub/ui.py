"""
Media Hub Module UI
YouTube search (yt-dlp) + Radio streaming + Local file player (MPV)
"""
import os
import subprocess
import shutil
import threading
from typing import Optional

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QScrollArea, QFileDialog, QMessageBox, QComboBox, QFrame,
)

from shared import (
    Colors, GlowButton, OutlineButton, ModernInput,
    ModernCard, create_separator, create_spacer,
)

IPC_PIPE = r'\\.\pipe\saydut_mpv_socket'

try:
    import yt_dlp
    _YT_DLP = True
except ImportError:
    _YT_DLP = False

_MPV = bool(shutil.which("mpv"))

TAB_STYLE = f"""
    QTabWidget::pane {{ border:none; background:rgba(17,24,39,0.92); border-radius:16px; }}
    QTabBar::tab {{ background:{Colors.BG_SECONDARY}; color:{Colors.TEXT_SECONDARY};
        padding:12px 24px; border:none; border-top-left-radius:12px;
        border-top-right-radius:12px; margin-right:4px; font-weight:600; }}
    QTabBar::tab:selected {{ background:rgba(17,24,39,0.92); color:{Colors.TEXT_PRIMARY}; }}
    QTabBar::tab:hover {{ background:rgba(30,41,59,0.8); }}
"""

RADIOS = {
    "KRAL Pop": "http://46.20.3.201:80/;",
    "Power Türk": "https://live.powerapp.com.tr/powerturk/abr/playlist.m3u8",
    "Alem FM": "https://turkmedya.radyotvonline.com/turkmedya/alemfm.stream/playlist.m3u8",
    "Joy FM": "http://provisioning.streamtheworld.com/pls/JOY_FMAAC.pls",
    "Power FM": "http://icast.powergroup.com.tr/PowerTurk/mpeg/128/home",
    "Slow Türk": "https://radyo.duhnet.tv/slowturk",
    "Pal FM": "http://shoutcast.radyogrup.com:1030/;",
}


class YTSearchWorker(QThread):
    results = Signal(list)
    error = Signal(str)

    def __init__(self, term):
        super().__init__()
        self.term = term

    def run(self):
        if not _YT_DLP:
            self.error.emit("yt-dlp yüklü değil")
            return
        try:
            opts = {
                'quiet': True,
                'extract_flat': 'in_playlist',
                'ignoreerrors': True,
                'extractor_args': {'youtube': {'player_client': ['android', 'ios']}},
            }
            if "youtube.com" in self.term or "youtu.be" in self.term:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(self.term, download=False)
                    self.results.emit([info])
            else:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(f"ytsearch15:{self.term}", download=False)
                    entries = list(info.get('entries', []))
                    self.results.emit(entries)
        except Exception as e:
            self.error.emit(str(e)[:100])


class MediaHubWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_process = None
        self._search_worker = None
        self._current_video = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header = ModernCard()
        hl = QVBoxLayout(header)
        hl.setContentsMargins(20, 16, 20, 16)
        title = QLabel("📺 Saydut Media Hub")
        title.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:24px;font-weight:800;background:transparent;")
        hl.addWidget(title)
        dep_parts = []
        if not _YT_DLP:
            dep_parts.append("yt-dlp: ❌")
        else:
            dep_parts.append("yt-dlp: ✅")
        dep_parts.append(f"MPV: {'✅' if _MPV else '❌'}")
        dep_lbl = QLabel(" | ".join(dep_parts))
        dep_lbl.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:11px;background:transparent;")
        hl.addWidget(dep_lbl)
        layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_STYLE)
        self.tabs.addTab(self._create_youtube_tab(), "YouTube")
        self.tabs.addTab(self._create_radio_tab(), "Radyo")
        self.tabs.addTab(self._create_player_tab(), "Oynatıcı")
        layout.addWidget(self.tabs, 1)

    # ── YouTube Tab ──────────────────────────────────────────────────
    def _create_youtube_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # Search bar
        search_row = QHBoxLayout()
        self.yt_input = ModernInput(placeholder="YouTube'da ara veya link yapıştır...", accent="#f97316")
        self.yt_input.returnPressed.connect(self._yt_search)
        search_row.addWidget(self.yt_input)
        btn_search = GlowButton("🔍 Ara", accent="#f97316")
        btn_search.clicked.connect(self._yt_search)
        search_row.addWidget(btn_search)
        lay.addLayout(search_row)

        # Content: results + controls
        content = QHBoxLayout()

        # Results list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self._results_container = QWidget()
        self._results_layout = QVBoxLayout(self._results_container)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.addStretch()
        scroll.setWidget(self._results_container)
        content.addWidget(scroll, 2)

        # Controls panel
        ctrl = ModernCard()
        ctrl_lay = QVBoxLayout(ctrl)
        ctrl_lay.setContentsMargins(16, 16, 16, 16)
        ctrl_lay.setSpacing(12)

        ctrl_title = QLabel("Oynatıcı")
        ctrl_title.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:16px;font-weight:700;background:transparent;")
        ctrl_lay.addWidget(ctrl_title)

        self.lbl_selected = QLabel("Bir video seçin...")
        self.lbl_selected.setWordWrap(True)
        self.lbl_selected.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:12px;background:transparent;")
        ctrl_lay.addWidget(self.lbl_selected)

        ctrl_lay.addWidget(create_separator())

        self.btn_play_video = GlowButton("▶ Video Oynat", accent="#22c55e")
        self.btn_play_video.setEnabled(False)
        self.btn_play_video.clicked.connect(lambda: self._yt_play("video"))
        ctrl_lay.addWidget(self.btn_play_video)

        self.btn_play_audio = GlowButton("🎵 Sadece Ses", accent="#3b82f6")
        self.btn_play_audio.setEnabled(False)
        self.btn_play_audio.clicked.connect(lambda: self._yt_play("audio"))
        ctrl_lay.addWidget(self.btn_play_audio)

        ctrl_lay.addWidget(create_separator())

        btn_pause = OutlineButton("⏸ Duraklat / Devam")
        btn_pause.clicked.connect(self._toggle_pause)
        ctrl_lay.addWidget(btn_pause)

        btn_stop = GlowButton("⏹ Durdur", accent="#ef4444")
        btn_stop.clicked.connect(self._stop_media)
        ctrl_lay.addWidget(btn_stop)

        ctrl_lay.addStretch()
        content.addWidget(ctrl, 1)

        lay.addLayout(content, 1)

        self.yt_status = QLabel("Hazır")
        self.yt_status.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:11px;background:transparent;")
        lay.addWidget(self.yt_status)

        return w

    # ── Radio Tab ────────────────────────────────────────────────────
    def _create_radio_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        info = QLabel("📻 Canlı Radyo İstasyonları")
        info.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:16px;font-weight:700;background:transparent;")
        lay.addWidget(info)
        lay.addWidget(create_separator())

        self.radio_combo = QComboBox()
        self.radio_combo.addItems(list(RADIOS.keys()))
        self.radio_combo.setStyleSheet(f"""
            QComboBox {{ background:{Colors.BG_SECONDARY}; color:{Colors.TEXT_PRIMARY};
                border:1px solid rgba(71,85,105,0.5); border-radius:10px; padding:10px 14px; font-weight:600; }}
            QComboBox:hover {{ border-color:#f97316; }}
            QComboBox::drop-down {{ border:none; }}
            QComboBox QAbstractItemView {{ background:{Colors.BG_SECONDARY}; color:{Colors.TEXT_PRIMARY};
                selection-background-color:#f97316; }}
        """)
        lay.addWidget(self.radio_combo)

        btn_row = QHBoxLayout()
        btn_play = GlowButton("▶ Oynat", accent="#22c55e")
        btn_play.clicked.connect(self._play_radio)
        btn_row.addWidget(btn_play)
        btn_pause = OutlineButton("⏸ Duraklat")
        btn_pause.clicked.connect(self._toggle_pause)
        btn_row.addWidget(btn_pause)
        btn_stop = GlowButton("⏹ Durdur", accent="#ef4444")
        btn_stop.clicked.connect(self._stop_media)
        btn_row.addWidget(btn_stop)
        lay.addLayout(btn_row)

        self.radio_status = QLabel("Radyo bekleniyor...")
        self.radio_status.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:12px;background:transparent;")
        lay.addWidget(self.radio_status)

        lay.addStretch()
        return w

    # ── Player Tab ───────────────────────────────────────────────────
    def _create_player_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        info = QLabel("🎥 Yerel Medya Oynatıcı")
        info.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:16px;font-weight:700;background:transparent;")
        lay.addWidget(info)
        lay.addWidget(create_separator())

        btn_open = GlowButton("📂 Dosya Seç (Video / Ses)", accent="#f97316")
        btn_open.setFixedHeight(48)
        btn_open.clicked.connect(self._open_local)
        lay.addWidget(btn_open)

        self.local_status = QLabel("Dosya seçilmedi")
        self.local_status.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:12px;background:transparent;")
        lay.addWidget(self.local_status)

        btn_row = QHBoxLayout()
        btn_pause = OutlineButton("⏸ Duraklat / Devam")
        btn_pause.clicked.connect(self._toggle_pause)
        btn_row.addWidget(btn_pause)
        btn_stop = GlowButton("⏹ Durdur", accent="#ef4444")
        btn_stop.clicked.connect(self._stop_media)
        btn_row.addWidget(btn_stop)
        lay.addLayout(btn_row)

        lay.addStretch()
        return w

    # ── MPV Engine ───────────────────────────────────────────────────
    def _play_mpv(self, url_or_file, is_video=True, title="Medya"):
        self._stop_media()
        cmd = ["mpv", url_or_file,
               f"--input-ipc-server={IPC_PIPE}",
               "--ytdl-raw-options=extractor-args=youtube:player_client=android"]
        if not is_video:
            cmd += ["--no-video", "--force-window=no"]
        else:
            cmd += ["--force-window=immediate", f"--title={title}"]
            if "youtube.com" in url_or_file or "youtu.be" in url_or_file:
                cmd.append("--ytdl-format=bestvideo+bestaudio/best")
        try:
            self.current_process = subprocess.Popen(cmd, creationflags=0x08000000)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"MPV başlatılamadı:\n{e}\n\nMPV kurulu mu?")
            return False

    def _toggle_pause(self):
        if not self.current_process:
            return
        try:
            with open(IPC_PIPE, 'w') as f:
                f.write("cycle pause\n")
        except Exception:
            pass

    def _stop_media(self):
        try:
            with open(IPC_PIPE, 'w') as f:
                f.write("quit\n")
        except Exception:
            pass
        if self.current_process:
            try:
                self.current_process.terminate()
                try:
                    self.current_process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.current_process.kill()
            except Exception:
                pass
            self.current_process = None

    # ── YouTube Actions ──────────────────────────────────────────────
    def _yt_search(self):
        term = self.yt_input.text().strip()
        if not term:
            return
        if not _YT_DLP:
            QMessageBox.warning(self, "Eksik", "yt-dlp yüklü değil.\npip install yt-dlp")
            return
        self.yt_status.setText("Aranıyor...")
        # Clear old results
        for i in reversed(range(self._results_layout.count())):
            item = self._results_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        self._search_worker = YTSearchWorker(term)
        self._search_worker.results.connect(self._yt_show_results)
        self._search_worker.error.connect(lambda e: self.yt_status.setText(f"Hata: {e}"))
        self._search_worker.start()

    def _yt_show_results(self, results):
        self.yt_status.setText(f"{len(results)} sonuç bulundu.")
        for vid in results:
            title = vid.get('title', 'Başlık yok')
            dur = vid.get('duration')
            dur_str = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else "??:??"

            btn = OutlineButton(f"{dur_str} | {title[:50]}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _c=False, v=vid: self._select_video(v))
            self._results_layout.insertWidget(self._results_layout.count() - 1, btn)

    def _select_video(self, vid):
        self._current_video = vid
        self.lbl_selected.setText(vid.get('title', 'Video'))
        self.lbl_selected.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:12px;background:transparent;")
        self.btn_play_video.setEnabled(True)
        self.btn_play_audio.setEnabled(True)

    def _yt_play(self, mode):
        if not self._current_video:
            return
        if not _MPV:
            QMessageBox.warning(self, "Eksik", "MPV yüklü değil.\nwinget install mpv")
            return
        vid = self._current_video
        if 'id' in vid:
            url = f"https://www.youtube.com/watch?v={vid['id']}"
        else:
            url = vid.get('url', '')
        title = vid.get('title', 'YouTube')
        is_video = mode == "video"
        self.yt_status.setText(f"Oynatılıyor: {title}")
        self._play_mpv(url, is_video, title)

    # ── Radio ────────────────────────────────────────────────────────
    def _play_radio(self):
        if not _MPV:
            QMessageBox.warning(self, "Eksik", "MPV yüklü değil.\nwinget install mpv")
            return
        name = self.radio_combo.currentText()
        url = RADIOS.get(name)
        if url:
            self.radio_status.setText(f"Bağlanıyor: {name}...")
            if self._play_mpv(url, is_video=False):
                self.radio_status.setText(f"🎵 Çalıyor: {name}")

    # ── Local Player ─────────────────────────────────────────────────
    def _open_local(self):
        if not _MPV:
            QMessageBox.warning(self, "Eksik", "MPV yüklü değil.\nwinget install mpv")
            return
        fp, _ = QFileDialog.getOpenFileName(
            self, "Dosya Seç", "",
            "Medya (*.mp4 *.mkv *.avi *.mp3 *.wav *.flac *.webm *.mov)")
        if not fp:
            return
        fname = os.path.basename(fp)
        is_vid = fname.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm'))
        self.local_status.setText(f"Oynatılıyor: {fname}")
        self._play_mpv(fp, is_vid, fname)
