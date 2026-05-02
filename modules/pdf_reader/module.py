"""PDF Reader Module"""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from module_system import BaseModule


class PDFReaderModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.module_id = "pdf-reader"
        self.name = "PDF Okuyucu"
        self.category = "utility"
        self.icon = "📄"
        self.theme_accent = "#14b8a6"
        self.requires_admin = False

    def create_widget(self, parent: QWidget) -> QWidget:
        try:
            from .ui import PDFReaderWidget
            return PDFReaderWidget(parent)
        except ImportError as e:
            w = QWidget(parent)
            layout = QVBoxLayout(w)
            lbl = QLabel(f"Eksik bağımlılık:\n{e}\n\npip install PySide6-Addons")
            lbl.setStyleSheet("color: #ef4444; font-size: 14px; padding: 40px;")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
            return w

    def on_activate(self) -> None:
        print(f"[{self.module_id}] Module activated")

    def on_deactivate(self) -> None:
        print(f"[{self.module_id}] Module deactivated")

    def cleanup(self) -> None:
        print(f"[{self.module_id}] Cleanup complete")
