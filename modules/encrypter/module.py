"""
Encrypter Module
Module wrapper for file/folder encryption
"""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout

from module_system import BaseModule


class EncrypterModule(BaseModule):
    """
    File/Folder Encryption Module

    Features:
    - AES-256-GCM encryption
    - Single file encrypt/decrypt
    - Bulk folder operations
    - Progress tracking
    - Async threading
    """

    def __init__(self):
        super().__init__()

        self.module_id = "encrypter"
        self.name = "Saydut Kripto"
        self.category = "security"
        self.icon = "🔐"
        self.theme_accent = "#ef4444"  # Red
        self.requires_admin = False

    def create_widget(self, parent: QWidget) -> QWidget:
        """Create the encrypter widget (lazy import)"""
        try:
            from .ui import EncrypterWidget
            return EncrypterWidget(parent)
        except ImportError as e:
            w = QWidget(parent)
            layout = QVBoxLayout(w)
            lbl = QLabel(f"Eksik bagimlilk:\n{e}\n\npip install cryptography")
            lbl.setStyleSheet("color: #ef4444; font-size: 14px; padding: 40px;")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
            return w

    def on_activate(self) -> None:
        """Called when module becomes active"""
        print(f"[{self.module_id}] Module activated")

    def on_deactivate(self) -> None:
        """Called when module becomes inactive"""
        print(f"[{self.module_id}] Module deactivated")

    def cleanup(self) -> None:
        """Cleanup resources"""
        # Stop any running workers
        if self.widget:
            widget = self.widget
            if hasattr(widget, 'worker') and widget.worker:
                if widget.worker.isRunning():
                    widget.worker.quit()
                    widget.worker.wait()

        print(f"[{self.module_id}] Cleanup complete")
