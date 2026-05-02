"""
QR Code Module UI
PySide6 interface for QR code generation
"""
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QFileDialog,
    QMessageBox,
)
from PIL import Image

from shared import (
    Colors,
    GlowButton,
    OutlineButton,
    ModernInput,
    ModernTextBox,
    ModernCard,
    create_separator,
    create_spacer,
)

from .logic import (
    split_pasted_text,
    build_plaintext_payload,
    make_qr_image,
    create_labels_pdf,
    save_payload_txt,
)


# ============================================================================
# QR CODE UI WIDGET
# ============================================================================

class QrCodeWidget(QWidget):
    """
    Main QR Code generation widget

    Features:
    - Location/parts list input
    - Live QR preview
    - PDF/PNG export
    - Modern gradient UI
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.current_img: Optional[Image.Image] = None
        self.current_payload: str = ""

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Setup main UI layout"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Left panel: Input controls
        left_panel = self._create_left_panel()
        layout.addWidget(left_panel, 2)

        # Right panel: Preview
        right_panel = self._create_right_panel()
        layout.addWidget(right_panel, 1)

    def _create_left_panel(self) -> QWidget:
        """Create left input panel"""
        panel = ModernCard()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("🎨 QR Kod Oluşturucu")
        title.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 20px;
            font-weight: 700;
            background: transparent;
        """)
        layout.addWidget(title)

        subtitle = QLabel("Parça listelerini QR koda dönüştür")
        subtitle.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 12px;
            background: transparent;
        """)
        layout.addWidget(subtitle)

        layout.addWidget(create_separator())

        # Location input
        loc_label = QLabel("Lokasyon / Raf:")
        loc_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600; background: transparent;")
        layout.addWidget(loc_label)

        self.location_input = ModernInput(
            placeholder="Örn: PALET 2 MALZEMELER VE ADETLERİ",
            accent=Colors.ACCENT_BLUE
        )
        layout.addWidget(self.location_input)

        layout.addWidget(create_spacer(12))

        # Parts list input
        parts_label = QLabel("Parça Listesi (her satırda bir parça):")
        parts_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600; background: transparent;")
        layout.addWidget(parts_label)

        self.parts_input = ModernTextBox(
            placeholder="Motor\nVites\nKampana\nAmortisor\n..."
        )
        self.parts_input.setMinimumHeight(200)
        layout.addWidget(self.parts_input, 1)

        # Options row 1: QR settings
        opts1 = QHBoxLayout()
        opts1.setSpacing(12)

        # Error level
        err_label = QLabel("Hata Düzeyi:")
        err_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
        opts1.addWidget(err_label)

        self.err_combo = QComboBox()
        self.err_combo.addItems(["L (düşük)", "M (orta)", "Q (yüksek)", "H (çok yüksek)"])
        self.err_combo.setCurrentIndex(2)  # Q (yüksek)
        self.err_combo.setStyleSheet(f"""
            QComboBox {{
                background: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid rgba(71, 85, 105, 0.5);
                border-radius: 10px;
                padding: 8px 12px;
                font-weight: 600;
            }}
            QComboBox:hover {{
                border-color: {Colors.ACCENT_BLUE};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.ACCENT_BLUE};
            }}
        """)
        opts1.addWidget(self.err_combo)

        # Scale
        scale_label = QLabel("Ölçek:")
        scale_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
        opts1.addWidget(scale_label)

        self.scale_input = ModernInput(accent=Colors.ACCENT_BLUE)
        self.scale_input.setText("14")
        self.scale_input.setFixedWidth(60)
        opts1.addWidget(self.scale_input)

        # Border
        border_label = QLabel("Border:")
        border_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
        opts1.addWidget(border_label)

        self.border_input = ModernInput(accent=Colors.ACCENT_BLUE)
        self.border_input.setText("6")
        self.border_input.setFixedWidth(60)
        opts1.addWidget(self.border_input)

        opts1.addStretch()
        layout.addLayout(opts1)

        # Options row 2: Checkboxes
        opts2 = QHBoxLayout()
        opts2.setSpacing(16)

        self.numbering_check = QCheckBox("Numaralandır")
        self.numbering_check.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_PRIMARY};
                font-weight: 600;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid rgba(71, 85, 105, 0.5);
                background: {Colors.BG_SECONDARY};
            }}
            QCheckBox::indicator:checked {{
                background: {Colors.ACCENT_BLUE};
                border-color: {Colors.ACCENT_BLUE};
            }}
        """)
        opts2.addWidget(self.numbering_check)

        self.split_commas_check = QCheckBox("Virgül Ayır")
        self.split_commas_check.setStyleSheet(self.numbering_check.styleSheet())
        opts2.addWidget(self.split_commas_check)

        self.include_location_check = QCheckBox("Lokasyonu Dahil Et")
        self.include_location_check.setChecked(True)
        self.include_location_check.setStyleSheet(self.numbering_check.styleSheet())
        opts2.addWidget(self.include_location_check)

        opts2.addStretch()
        layout.addLayout(opts2)

        layout.addWidget(create_separator())

        # Action buttons
        actions = QHBoxLayout()
        actions.setSpacing(12)

        self.generate_btn = GlowButton("QR Oluştur", accent=Colors.ACCENT_BLUE)
        self.generate_btn.setFixedHeight(44)
        actions.addWidget(self.generate_btn)

        self.clear_btn = OutlineButton("Temizle")
        self.clear_btn.setFixedHeight(44)
        actions.addWidget(self.clear_btn)

        actions.addStretch()
        layout.addLayout(actions)

        return panel

    def _create_right_panel(self) -> QWidget:
        """Create right preview panel"""
        panel = ModernCard()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("Önizleme")
        title.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 16px;
            font-weight: 700;
            background: transparent;
        """)
        layout.addWidget(title)

        layout.addWidget(create_separator())

        # QR Preview
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(300, 300)
        self.preview_label.setStyleSheet(f"""
            background: {Colors.BG_SECONDARY};
            border-radius: 16px;
            padding: 20px;
        """)
        self.preview_label.setText("QR kod burada görünecek")
        layout.addWidget(self.preview_label, 1)

        # PDF Settings
        pdf_settings = QVBoxLayout()
        pdf_settings.setSpacing(12)

        # Layout combo
        layout_row = QHBoxLayout()
        layout_label = QLabel("PDF Düzeni:")
        layout_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600; background: transparent;")
        layout_row.addWidget(layout_label)

        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["4 (2x2)", "6 (3x2)", "8 (4x2)"])
        self.layout_combo.setStyleSheet(self.err_combo.styleSheet())
        layout_row.addWidget(self.layout_combo, 1)
        pdf_settings.addLayout(layout_row)

        # Title input
        title_row = QHBoxLayout()
        title_label = QLabel("PDF Başlık:")
        title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600; background: transparent;")
        title_row.addWidget(title_label)

        self.pdf_title_input = ModernInput(placeholder="Depo Malzemeleri", accent=Colors.ACCENT_BLUE)
        title_row.addWidget(self.pdf_title_input, 1)
        pdf_settings.addLayout(title_row)

        # Show text checkbox
        self.show_text_check = QCheckBox("QR altında metin göster")
        self.show_text_check.setChecked(True)
        self.show_text_check.setStyleSheet(self.numbering_check.styleSheet())
        pdf_settings.addWidget(self.show_text_check)

        layout.addLayout(pdf_settings)

        layout.addWidget(create_separator())

        # Export buttons
        export_btns = QVBoxLayout()
        export_btns.setSpacing(10)

        self.export_pdf_btn = GlowButton("📄 PDF Export", accent=Colors.ACCENT_PURPLE)
        self.export_pdf_btn.setEnabled(False)
        export_btns.addWidget(self.export_pdf_btn)

        self.export_png_btn = GlowButton("🖼️ PNG Export", accent=Colors.ACCENT_PINK)
        self.export_png_btn.setEnabled(False)
        export_btns.addWidget(self.export_png_btn)

        layout.addLayout(export_btns)

        return panel

    def _connect_signals(self):
        """Connect UI signals"""
        self.generate_btn.clicked.connect(self._on_generate)
        self.clear_btn.clicked.connect(self._on_clear)
        self.export_pdf_btn.clicked.connect(self._on_export_pdf)
        self.export_png_btn.clicked.connect(self._on_export_png)

    def _on_generate(self):
        """Generate QR code"""
        try:
            # Get location
            location = self.location_input.text().strip()

            # Parse parts list
            parts_text = self.parts_input.toPlainText().strip()
            if not parts_text:
                QMessageBox.warning(self, "Uyarı", "Parça listesi boş olamaz!")
                return

            items = split_pasted_text(parts_text, self.split_commas_check.isChecked())
            if not items:
                QMessageBox.warning(self, "Uyarı", "Parça listesi boş olamaz!")
                return

            # Build payload
            self.current_payload = build_plaintext_payload(
                location,
                items,
                self.numbering_check.isChecked(),
                self.include_location_check.isChecked()
            )

            # Generate QR code
            try:
                box_size = int(self.scale_input.text())
            except ValueError:
                box_size = 14

            try:
                border = int(self.border_input.text())
            except ValueError:
                border = 6

            self.current_img = make_qr_image(
                self.current_payload,
                box_size,
                border,
                self.err_combo.currentText()
            )

            # Update preview
            self._update_preview()

            # Enable export buttons
            self.export_pdf_btn.setEnabled(True)
            self.export_png_btn.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"QR kod oluşturulamadı:\n{e}")

    def _update_preview(self):
        """Update QR code preview"""
        if not self.current_img:
            return

        # Convert PIL Image to QPixmap
        img_copy = self.current_img.copy()
        img_copy.thumbnail((400, 400), Image.LANCZOS)

        # Convert to QImage
        img_bytes = img_copy.tobytes("raw", "RGB")
        qimage = QImage(
            img_bytes,
            img_copy.width,
            img_copy.height,
            img_copy.width * 3,
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(qimage)
        self.preview_label.setPixmap(pixmap)

    def _on_clear(self):
        """Clear all inputs"""
        self.location_input.clear()
        self.parts_input.clear()
        self.preview_label.clear()
        self.preview_label.setText("QR kod burada görünecek")
        self.current_img = None
        self.current_payload = ""
        self.export_pdf_btn.setEnabled(False)
        self.export_png_btn.setEnabled(False)

    def _on_export_pdf(self):
        """Export as PDF"""
        if not self.current_img or not self.current_payload:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "PDF Kaydet",
            "",
            "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        try:
            create_labels_pdf(
                file_path,
                self.current_img,
                self.current_payload,
                self.layout_combo.currentText(),
                self.show_text_check.isChecked(),
                self.pdf_title_input.text()
            )

            QMessageBox.information(self, "Başarılı", f"PDF kaydedildi:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"PDF kaydedilemedi:\n{e}")

    def _on_export_png(self):
        """Export as PNG"""
        if not self.current_img:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "PNG Kaydet",
            "",
            "PNG Files (*.png)"
        )

        if not file_path:
            return

        try:
            self.current_img.save(file_path, "PNG")

            # Also save .txt
            base_path = file_path.rsplit(".", 1)[0]
            txt_path = save_payload_txt(base_path, self.current_payload)

            QMessageBox.information(
                self,
                "Başarılı",
                f"PNG ve TXT kaydedildi:\n{file_path}\n{txt_path}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"PNG kaydedilemedi:\n{e}")
