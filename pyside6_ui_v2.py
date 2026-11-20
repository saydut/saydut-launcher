"""
Saydut Launcher - Modular Application Platform
Each module opens in its own separate window
"""
import sys
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QGridLayout,
)
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtGui import QColor

from shared import (
    GlowBackground,
    AnimatedHeader,
    Colors,
)

from module_system import (
    ModuleRegistry,
    ModuleWindow,
    get_global_registry,
)


# ============================================================================
# MODULE CARD  (clickable card in main grid)
# ============================================================================

class ModuleCard(QFrame):
    """Clickable card that opens a module in a separate window"""

    def __init__(self, icon: str, name: str, description: str, module_id: str, accent: str):
        super().__init__()
        self.module_id = module_id
        self.accent = accent
        self.setCursor(Qt.PointingHandCursor)

        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(24, 32, 52, 0.85);
                border: 1px solid rgba(71, 85, 105, 0.3);
                border-radius: 20px;
            }}
            QFrame:hover {{
                border-color: {accent};
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(accent))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Accent bar
        bar = QFrame()
        bar.setFixedHeight(4)
        bar.setStyleSheet(f"background: {accent}; border-radius: 2px; border: none;")
        layout.addWidget(bar)

        # Icon + Name
        title_label = QLabel(f"{icon}  {name}")
        title_label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 16px;
            font-weight: 700;
            background: transparent;
            border: none;
        """)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            color: {Colors.TEXT_TERTIARY};
            font-size: 11px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(desc_label)

        layout.addStretch()

        # Open button
        open_btn = QPushButton("Aç")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setStyleSheet(f"""
            QPushButton {{
                background: {accent};
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {accent},
                    stop:1 {Colors.ACCENT_PURPLE}
                );
            }}
        """)
        layout.addWidget(open_btn)

        # Store reference so launcher can connect to it
        self.open_btn = open_btn

    def mousePressEvent(self, event):
        """Clicking anywhere on the card triggers the open button"""
        self.open_btn.click()
        super().mousePressEvent(event)


# ============================================================================
# MAIN LAUNCHER WINDOW
# ============================================================================

class LauncherWindow(QMainWindow):
    """
    Main launcher dashboard

    Shows module cards in a grid.
    Clicking a card opens that module in a new window.
    """

    MODULE_META = [
        {"id": "qr-code",          "icon": "🎨", "name": "QR Kod",             "desc": "Parça listesi QR kod oluşturucu",       "accent": Colors.ACCENT_BLUE},
        {"id": "encrypter",         "icon": "🔐", "name": "Şifreleyici",        "desc": "AES-256 dosya/klasör şifreleme",        "accent": "#ef4444"},
        {"id": "password-manager",  "icon": "🔑", "name": "Şifre Yöneticisi",   "desc": "Güvenli şifre kasası",                  "accent": "#22c55e"},
        {"id": "media-hub",         "icon": "📺", "name": "Media Hub",          "desc": "YouTube, radyo ve medya oynatıcı",      "accent": "#f97316"},
        {"id": "ram-cleaner",       "icon": "🧹", "name": "RAM Temizleyici",    "desc": "Sistem belleğini temizle",              "accent": "#8b5cf6"},
        {"id": "pdf-reader",        "icon": "📄", "name": "PDF Okuyucu",        "desc": "Modern PDF görüntüleyici",              "accent": "#14b8a6"},
        {"id": "file-splitter",     "icon": "📁", "name": "Dosya Ayırıcı",      "desc": "Dosya karşılaştırma ve düzenleme",      "accent": "#f59e0b"},
        {"id": "program-manager",   "icon": "📦", "name": "Program Yöneticisi", "desc": "Winget/Chocolatey yönetimi",            "accent": "#06b6d4"},
        {"id": "pc-performance",    "icon": "⚡", "name": "PC Performans",      "desc": "Güç planları ve performans ayarları",   "accent": "#ec4899"},
    ]

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Saydut Launcher")
        self.resize(1100, 720)
        self.setFont(QFont("Segoe UI Variable", 10))
        self.setStyleSheet("QLabel { background: transparent; border: none; }")

        # Module system
        self.registry = get_global_registry()

        # Track open module windows  (module_id -> ModuleWindow)
        self._open_windows: dict[str, ModuleWindow] = {}

        self._register_modules()
        self._setup_ui()

    # ------------------------------------------------------------------
    # MODULE REGISTRATION
    # ------------------------------------------------------------------

    def _register_modules(self):
        """Import and register every module class"""
        from modules.qr_code import QrCodeModule
        from modules.encrypter import EncrypterModule
        from modules.password_manager import PasswordManagerModule
        from modules.media_hub import MediaHubModule
        from modules.ram_cleaner import RAMCleanerModule
        from modules.pdf_reader import PDFReaderModule
        from modules.file_splitter import FileSplitterModule
        from modules.program_manager import ProgramManagerModule
        from modules.pc_performance import PCPerformanceModule

        for cls in (
            QrCodeModule,
            EncrypterModule,
            PasswordManagerModule,
            MediaHubModule,
            RAMCleanerModule,
            PDFReaderModule,
            FileSplitterModule,
            ProgramManagerModule,
            PCPerformanceModule,
        ):
            self.registry.register(cls)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        root = GlowBackground()
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # --- Animated header ---
        header = AnimatedHeader()
        header.setFixedHeight(140)
        header.setStyleSheet("border-radius: 26px;")
        h_shadow = QGraphicsDropShadowEffect(header)
        h_shadow.setBlurRadius(36)
        h_shadow.setColor(QColor(0, 0, 0, 130))
        h_shadow.setOffset(0, 12)
        header.setGraphicsEffect(h_shadow)

        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(24, 20, 24, 20)
        h_layout.setSpacing(8)

        title = QLabel("Saydut Launcher")
        title.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:32px;font-weight:800;")
        subtitle = QLabel("Modern, modüler uygulama platformu  -  Bir modüle tıklayarak aç")
        subtitle.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:13px;")
        h_layout.addWidget(title)
        h_layout.addWidget(subtitle)
        h_layout.addStretch()

        main_layout.addWidget(header)

        # --- Card grid ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea{border:none;background:transparent;}
            QScrollBar:vertical{background:transparent;width:10px;margin:6px 0;}
            QScrollBar::handle:vertical{background:#334155;border-radius:5px;min-height:30px;}
            QScrollBar::handle:vertical:hover{background:#475569;}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;background:transparent;}
            QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{background:transparent;}
        """)

        grid_widget = QWidget()
        self.grid = QGridLayout(grid_widget)
        self.grid.setSpacing(18)
        self.grid.setContentsMargins(4, 4, 4, 4)

        for idx, meta in enumerate(self.MODULE_META):
            card = ModuleCard(
                meta["icon"], meta["name"], meta["desc"],
                meta["id"], meta["accent"],
            )
            card.open_btn.clicked.connect(
                lambda _checked=False, mid=meta["id"]: self._open_module(mid)
            )
            row, col = divmod(idx, 3)
            self.grid.addWidget(card, row, col)

        scroll.setWidget(grid_widget)
        main_layout.addWidget(scroll, 1)

        self.setCentralWidget(root)

    # ------------------------------------------------------------------
    # OPEN / CLOSE MODULE WINDOWS
    # ------------------------------------------------------------------

    def _open_module(self, module_id: str):
        """Open a module in a separate window (or bring existing to front)"""

        # If already open, just bring to front
        if module_id in self._open_windows:
            win = self._open_windows[module_id]
            win.raise_()
            win.activateWindow()
            return

        # Get the module instance from registry
        module = self.registry.get_module(module_id)

        # Create a new window for this module
        win = ModuleWindow(module, self.registry, parent=None)
        win.window_closed.connect(self._on_module_window_closed)
        self._open_windows[module_id] = win
        win.show()

    def _on_module_window_closed(self, module_id: str):
        """Remove window reference when it's closed"""
        self._open_windows.pop(module_id, None)

    # ------------------------------------------------------------------
    # CLEANUP
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        """Close all module windows when launcher closes"""
        for win in list(self._open_windows.values()):
            win.close()
        self.registry.cleanup_all()
        super().closeEvent(event)


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    app = QApplication(sys.argv)
    window = LauncherWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
