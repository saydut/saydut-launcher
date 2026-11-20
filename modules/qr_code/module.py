"""
QR Code Module
Module wrapper for QR code generator
"""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout

from module_system import BaseModule


class QrCodeModule(BaseModule):
    """
    QR Code Generator Module

    Features:
    - Parts list → QR code conversion
    - PDF label export (2x2, 3x2, 4x2 grids)
    - PNG + TXT export
    - Live preview
    """

    def __init__(self):
        super().__init__()

        self.module_id = "qr-code"
        self.name = "QR Kod Oluşturucu"
        self.category = "utility"
        self.icon = "🎨"
        self.theme_accent = "#38bdf8"  # Cyan
        self.requires_admin = False

    def create_widget(self, parent: QWidget) -> QWidget:
        """Create the QR code widget (lazy import)"""
        try:
            from .ui import QrCodeWidget
            return QrCodeWidget(parent)
        except ImportError as e:
            # Missing dependency (PIL, qrcode, reportlab)
            w = QWidget(parent)
            layout = QVBoxLayout(w)
            lbl = QLabel(f"Eksik bağımlılık:\n{e}\n\npip install Pillow qrcode reportlab")
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
        print(f"[{self.module_id}] Cleanup complete")
