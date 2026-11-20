"""
PDF Reader Module UI
Embeds QPdfView for full PDF viewing with zoom, page nav, print
"""
from typing import Optional

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFileDialog, QSlider, QSpinBox, QToolButton, QMessageBox,
)

try:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView
    from PySide6.QtPrintSupport import QPrinter, QPrintDialog
    _PDF_AVAILABLE = True
except ImportError:
    _PDF_AVAILABLE = False

from shared import (
    Colors, GlowButton, OutlineButton, ModernCard, ModernInput,
)


class ZoomPdfView(QPdfView):
    """QPdfView with mouse wheel zoom"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPageMode(QPdfView.PageMode.MultiPage)
        self.setZoomMode(QPdfView.ZoomMode.Custom)
        self.setZoomFactor(1.0)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            return super().wheelEvent(event)
        factor = 1.1 if delta > 0 else 1 / 1.1
        new_zoom = max(0.2, min(self.zoomFactor() * factor, 5.0))
        self.setZoomFactor(new_zoom)
        event.accept()


class PDFReaderWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        if not _PDF_AVAILABLE:
            lay = QVBoxLayout(self)
            lay.setContentsMargins(40, 40, 40, 40)
            lbl = QLabel("QtPdf modülü bulunamadı.\n\npip install PySide6-Addons")
            lbl.setStyleSheet(f"color:#ef4444;font-size:14px;")
            lbl.setWordWrap(True)
            lay.addWidget(lbl)
            return

        self.doc = QPdfDocument(self)
        self.view = ZoomPdfView()
        self.view.setDocument(self.doc)
        self.navigator = self.view.pageNavigator()
        self.navigator.currentPageChanged.connect(self._on_page_changed)
        self.doc.statusChanged.connect(self._on_doc_status)
        self._pending = False

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = ModernCard()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 12, 16, 12)
        title = QLabel("📄 Saydut PDF Reader")
        title.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:20px;font-weight:800;background:transparent;")
        hl.addWidget(title)
        hl.addStretch()
        layout.addWidget(header)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        btn_open = GlowButton("📂 PDF Aç", accent="#14b8a6")
        btn_open.clicked.connect(self._open_file)
        toolbar.addWidget(btn_open)

        btn_print = OutlineButton("🖨️ Yazdır")
        btn_print.clicked.connect(self._print)
        toolbar.addWidget(btn_print)

        toolbar.addSpacing(12)

        # Zoom controls
        btn_out = QToolButton()
        btn_out.setText("−")
        btn_out.setFixedSize(32, 32)
        btn_out.setStyleSheet(f"background:{Colors.BG_SECONDARY};color:{Colors.TEXT_PRIMARY};border-radius:6px;font-size:16px;font-weight:bold;")
        btn_out.clicked.connect(lambda: self._adjust_zoom(-0.1))
        toolbar.addWidget(btn_out)

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(50)
        self.zoom_slider.setMaximum(400)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(160)
        self.zoom_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ background:{Colors.BG_SECONDARY}; height:6px; border-radius:3px; }}
            QSlider::handle:horizontal {{ background:#14b8a6; width:16px; margin:-5px 0; border-radius:8px; }}
        """)
        self.zoom_slider.valueChanged.connect(self._slider_zoom)
        toolbar.addWidget(self.zoom_slider)

        btn_in = QToolButton()
        btn_in.setText("+")
        btn_in.setFixedSize(32, 32)
        btn_in.setStyleSheet(btn_out.styleSheet())
        btn_in.clicked.connect(lambda: self._adjust_zoom(0.1))
        toolbar.addWidget(btn_in)

        btn_fw = OutlineButton("Genişliğe Sığdır")
        btn_fw.clicked.connect(lambda: self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth))
        toolbar.addWidget(btn_fw)

        btn_fp = OutlineButton("Sayfaya Sığdır")
        btn_fp.clicked.connect(lambda: self.view.setZoomMode(QPdfView.ZoomMode.FitInView))
        toolbar.addWidget(btn_fp)

        toolbar.addSpacing(12)

        # Page navigation
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setStyleSheet(f"""
            QSpinBox {{ background:{Colors.BG_SECONDARY}; color:{Colors.TEXT_PRIMARY};
                border:1px solid rgba(71,85,105,0.5); border-radius:8px; padding:4px 8px; }}
        """)
        self.page_spin.valueChanged.connect(self._go_to_page)
        toolbar.addWidget(self.page_spin)

        self.total_lbl = QLabel("/ 0")
        self.total_lbl.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};background:transparent;")
        toolbar.addWidget(self.total_lbl)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # PDF View
        self.view.setStyleSheet(f"background:{Colors.BG_SECONDARY}; border-radius:12px;")
        layout.addWidget(self.view, 1)

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "PDF Aç", "", "PDF Files (*.pdf)")
        if not path:
            return
        status = self.doc.load(path)
        self._pending = True
        if status == QPdfDocument.Status.Error:
            self._pending = False
            QMessageBox.warning(self, "Hata", "PDF açılamadı.")
            return
        if status == QPdfDocument.Status.Ready:
            self._pending = False
            self._update_page_count()
            self.navigator.jump(0, QPointF(0, 0), None)

    def _on_doc_status(self, status):
        if not self._pending:
            return
        if status == QPdfDocument.Status.Ready:
            self._pending = False
            self._update_page_count()
            self.navigator.jump(0, QPointF(0, 0), None)
        elif status == QPdfDocument.Status.Error:
            self._pending = False
            QMessageBox.warning(self, "Hata", "PDF açılamadı.")

    def _update_page_count(self):
        count = self.doc.pageCount()
        self.page_spin.blockSignals(True)
        self.page_spin.setMaximum(max(count, 1))
        self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)
        self.total_lbl.setText(f"/ {count}")

    def _on_page_changed(self, page):
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(page + 1)
        self.page_spin.blockSignals(False)

    def _go_to_page(self):
        page = self.page_spin.value() - 1
        if 0 <= page < self.doc.pageCount():
            self.navigator.jump(page, QPointF(0, 0), None)

    def _adjust_zoom(self, delta):
        zoom = max(0.2, min(self.view.zoomFactor() + delta, 5.0))
        self.view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.view.setZoomFactor(zoom)
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(int(zoom * 100))
        self.zoom_slider.blockSignals(False)

    def _slider_zoom(self, value):
        self.view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.view.setZoomFactor(value / 100.0)

    def _print(self):
        if self.doc.pageCount() == 0:
            return
        printer = QPrinter()
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.Accepted:
            self.view.print_(printer)
