"""
File Splitter Module UI
Compare two folders and find differences
"""
import os
from typing import Optional

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
)

from shared import (
    Colors, GlowButton, OutlineButton, ModernInput,
    ModernCard, create_separator, create_spacer,
)


class CompareWorker(QThread):
    result = Signal(list, list, list)  # only_a, only_b, common
    error = Signal(str)

    def __init__(self, path_a, path_b):
        super().__init__()
        self.path_a = path_a
        self.path_b = path_b

    def run(self):
        try:
            files_a = set()
            files_b = set()
            for root, dirs, files in os.walk(self.path_a):
                rel = os.path.relpath(root, self.path_a)
                for f in files:
                    files_a.add(os.path.join(rel, f))
            for root, dirs, files in os.walk(self.path_b):
                rel = os.path.relpath(root, self.path_b)
                for f in files:
                    files_b.add(os.path.join(rel, f))

            only_a = sorted(files_a - files_b)
            only_b = sorted(files_b - files_a)
            common = sorted(files_a & files_b)
            self.result.emit(only_a, only_b, common)
        except Exception as e:
            self.error.emit(str(e))


TABLE_STYLE = f"""
    QTableWidget {{
        background: {Colors.BG_SECONDARY};
        color: {Colors.TEXT_PRIMARY};
        border: none;
        border-radius: 12px;
        gridline-color: rgba(71,85,105,0.3);
    }}
    QTableWidget::item {{
        padding: 6px 12px;
    }}
    QTableWidget::item:selected {{
        background: rgba(245,158,11,0.3);
    }}
    QHeaderView::section {{
        background: {Colors.BG_PRIMARY};
        color: {Colors.TEXT_PRIMARY};
        border: none;
        padding: 8px 12px;
        font-weight: 700;
    }}
"""


class FileSplitterWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._worker = None
        self._path_a = ""
        self._path_b = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header
        header = ModernCard()
        hl = QVBoxLayout(header)
        hl.setContentsMargins(20, 16, 20, 16)
        title = QLabel("📁 Dosya Karşılaştırıcı")
        title.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-size:24px;font-weight:800;background:transparent;")
        hl.addWidget(title)
        sub = QLabel("İki klasörü karşılaştır, farklılıkları bul")
        sub.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:12px;background:transparent;")
        hl.addWidget(sub)
        layout.addWidget(header)

        # Folder selection
        folders_card = ModernCard()
        fl = QVBoxLayout(folders_card)
        fl.setContentsMargins(20, 16, 20, 16)
        fl.setSpacing(12)

        # Folder A
        row_a = QHBoxLayout()
        lbl_a = QLabel("Klasör A:")
        lbl_a.setFixedWidth(70)
        lbl_a.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-weight:600;background:transparent;")
        row_a.addWidget(lbl_a)
        self.input_a = ModernInput(placeholder="Birinci klasör...", accent="#f59e0b")
        self.input_a.setReadOnly(True)
        row_a.addWidget(self.input_a)
        btn_a = OutlineButton("Seç")
        btn_a.clicked.connect(lambda: self._pick_folder("a"))
        row_a.addWidget(btn_a)
        fl.addLayout(row_a)

        # Folder B
        row_b = QHBoxLayout()
        lbl_b = QLabel("Klasör B:")
        lbl_b.setFixedWidth(70)
        lbl_b.setStyleSheet(f"color:{Colors.TEXT_PRIMARY};font-weight:600;background:transparent;")
        row_b.addWidget(lbl_b)
        self.input_b = ModernInput(placeholder="İkinci klasör...", accent="#f59e0b")
        self.input_b.setReadOnly(True)
        row_b.addWidget(self.input_b)
        btn_b = OutlineButton("Seç")
        btn_b.clicked.connect(lambda: self._pick_folder("b"))
        row_b.addWidget(btn_b)
        fl.addLayout(row_b)

        # Compare button
        self.btn_compare = GlowButton("🔍 Karşılaştır", accent="#f59e0b")
        self.btn_compare.setFixedHeight(44)
        self.btn_compare.clicked.connect(self._on_compare)
        fl.addWidget(self.btn_compare)

        layout.addWidget(folders_card)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Dosya", "Durum", "Konum"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet(TABLE_STYLE)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        # Status
        self.status_lbl = QLabel("Klasörleri seçip karşılaştır butonuna basın.")
        self.status_lbl.setStyleSheet(f"color:{Colors.TEXT_SECONDARY};font-size:11px;background:transparent;")
        layout.addWidget(self.status_lbl)

    def _pick_folder(self, which):
        path = QFileDialog.getExistingDirectory(self, "Klasör Seç")
        if not path:
            return
        if which == "a":
            self._path_a = path
            self.input_a.setText(path)
        else:
            self._path_b = path
            self.input_b.setText(path)

    def _on_compare(self):
        if not self._path_a or not self._path_b:
            QMessageBox.warning(self, "Uyarı", "Lütfen iki klasör de seçin.")
            return
        self.btn_compare.setEnabled(False)
        self.btn_compare.setText("Karşılaştırılıyor...")
        self.table.setRowCount(0)

        self._worker = CompareWorker(self._path_a, self._path_b)
        self._worker.result.connect(self._show_results)
        self._worker.error.connect(lambda e: (
            self.status_lbl.setText(f"Hata: {e}"),
            self.btn_compare.setEnabled(True),
            self.btn_compare.setText("🔍 Karşılaştır"),
        ))
        self._worker.start()

    def _show_results(self, only_a, only_b, common):
        self.btn_compare.setEnabled(True)
        self.btn_compare.setText("🔍 Karşılaştır")

        total = len(only_a) + len(only_b) + len(common)
        self.table.setRowCount(total)

        row = 0
        for f in only_a:
            self.table.setItem(row, 0, QTableWidgetItem(f))
            item = QTableWidgetItem("Sadece A'da")
            item.setForeground(Qt.red)
            self.table.setItem(row, 1, item)
            self.table.setItem(row, 2, QTableWidgetItem("A"))
            row += 1

        for f in only_b:
            self.table.setItem(row, 0, QTableWidgetItem(f))
            item = QTableWidgetItem("Sadece B'de")
            item.setForeground(Qt.cyan)
            self.table.setItem(row, 1, item)
            self.table.setItem(row, 2, QTableWidgetItem("B"))
            row += 1

        for f in common:
            self.table.setItem(row, 0, QTableWidgetItem(f))
            item = QTableWidgetItem("Her ikisinde")
            item.setForeground(Qt.green)
            self.table.setItem(row, 1, item)
            self.table.setItem(row, 2, QTableWidgetItem("A & B"))
            row += 1

        self.status_lbl.setText(
            f"Sonuç: {len(only_a)} sadece A | {len(only_b)} sadece B | {len(common)} ortak"
        )
