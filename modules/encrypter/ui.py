"""
Encrypter Module UI
PySide6 interface for file/folder encryption
"""
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QFileDialog,
    QMessageBox,
)

from shared import (
    Colors,
    GlowButton,
    ModernInput,
    ModernTextBox,
    ModernCard,
    ModernProgressBar,
    create_separator,
    create_spacer,
    WorkerThread,
    encrypt_file,
    decrypt_file,
    encrypt_folder,
    decrypt_folder,
)


# ============================================================================
# WORKER THREADS
# ============================================================================

class FileEncryptWorker(WorkerThread):
    """Worker for file encryption"""

    def __init__(self, input_path: str, output_path: str, password: str):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.password = password

    def do_work(self) -> dict:
        self.emit_status("Dosya şifreleniyor...")
        encrypt_file(self.input_path, self.output_path, self.password)
        return {"success": True, "file": self.output_path}


class FileDecryptWorker(WorkerThread):
    """Worker for file decryption"""

    def __init__(self, input_path: str, output_path: str, password: str):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.password = password

    def do_work(self) -> dict:
        self.emit_status("Dosya çözülüyor...")
        decrypt_file(self.input_path, self.output_path, self.password)
        return {"success": True, "file": self.output_path}


class FolderEncryptWorker(WorkerThread):
    """Worker for folder encryption"""

    def __init__(self, folder_path: str, password: str):
        super().__init__()
        self.folder_path = folder_path
        self.password = password

    def do_work(self) -> dict:
        self.emit_status("Klasör şifreleniyor...")

        def progress_callback(current: int, total: int, filename: str):
            self.emit_progress(current, total)
            self.emit_status(f"Şifreleniyor: {filename} ({current}/{total})")

        success, errors = encrypt_folder(
            self.folder_path,
            self.password,
            progress_callback
        )

        return {"success": success, "errors": errors}


class FolderDecryptWorker(WorkerThread):
    """Worker for folder decryption"""

    def __init__(self, folder_path: str, password: str):
        super().__init__()
        self.folder_path = folder_path
        self.password = password

    def do_work(self) -> dict:
        self.emit_status("Klasör çözülüyor...")

        def progress_callback(current: int, total: int, filename: str):
            self.emit_progress(current, total)
            self.emit_status(f"Çözülüyor: {filename} ({current}/{total})")

        success, errors = decrypt_folder(
            self.folder_path,
            self.password,
            progress_callback
        )

        return {"success": success, "errors": errors}


# ============================================================================
# MAIN WIDGET
# ============================================================================

class EncrypterWidget(QWidget):
    """
    File/Folder Encryption Widget

    Features:
    - AES-256-GCM encryption
    - File/folder operations
    - Progress tracking
    - Async threading
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.worker: Optional[WorkerThread] = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup main UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header_card = ModernCard()
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(20, 20, 20, 20)
        header_layout.setSpacing(8)

        title = QLabel("🔐 Saydut Kripto | Pro")
        title.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 24px;
            font-weight: 800;
            background: transparent;
        """)
        header_layout.addWidget(title)

        subtitle = QLabel("AES-256-GCM Askeri Standart Şifreleme")
        subtitle.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 12px;
            background: transparent;
        """)
        header_layout.addWidget(subtitle)

        layout.addWidget(header_card)

        # Password input
        pass_card = ModernCard()
        pass_layout = QVBoxLayout(pass_card)
        pass_layout.setContentsMargins(20, 20, 20, 20)
        pass_layout.setSpacing(12)

        pass_label = QLabel("Güvenlik Anahtarı (Parola)")
        pass_label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-weight: 700;
            background: transparent;
        """)
        pass_layout.addWidget(pass_label)

        self.password_input = ModernInput(
            placeholder="Parolanızı buraya girin...",
            accent="#ef4444"
        )
        self.password_input.setEchoMode(ModernInput.Password)
        self.password_input.setFixedHeight(44)
        pass_layout.addWidget(self.password_input)

        layout.addWidget(pass_card)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: rgba(17, 24, 39, 0.92);
                border-radius: 16px;
            }}
            QTabBar::tab {{
                background: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_SECONDARY};
                padding: 12px 24px;
                border: none;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                margin-right: 4px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: rgba(17, 24, 39, 0.92);
                color: {Colors.TEXT_PRIMARY};
            }}
            QTabBar::tab:hover {{
                background: rgba(30, 41, 59, 0.8);
            }}
        """)

        # File operations tab
        file_tab = self._create_file_tab()
        self.tabs.addTab(file_tab, "Dosya İşlemleri")

        # Folder operations tab
        folder_tab = self._create_folder_tab()
        self.tabs.addTab(folder_tab, "Klasör İşlemleri")

        layout.addWidget(self.tabs, 1)

        # Progress & Log
        progress_card = ModernCard()
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(20, 20, 20, 20)
        progress_layout.setSpacing(12)

        # Progress bar
        self.progress_bar = ModernProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)
        progress_layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Sistem Hazır")
        self.status_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 11px;
            background: transparent;
        """)
        progress_layout.addWidget(self.status_label)

        # Log box
        self.log_box = ModernTextBox()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(120)
        progress_layout.addWidget(self.log_box)

        layout.addWidget(progress_card)

    def _create_file_tab(self) -> QWidget:
        """Create file operations tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        info = QLabel("Tek bir dosyayı şifrelemek veya çözmek için\naşağıdaki butonları kullanın.")
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 12px;
            background: transparent;
        """)
        layout.addWidget(info)

        layout.addWidget(create_spacer(10))

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.encrypt_file_btn = GlowButton("🔒 Dosya Şifrele", accent="#ef4444")
        self.encrypt_file_btn.setFixedHeight(48)
        self.encrypt_file_btn.clicked.connect(self._on_encrypt_file)
        btn_layout.addWidget(self.encrypt_file_btn)

        self.decrypt_file_btn = GlowButton("🔓 Dosya Çöz", accent="#22c55e")
        self.decrypt_file_btn.setFixedHeight(48)
        self.decrypt_file_btn.clicked.connect(self._on_decrypt_file)
        btn_layout.addWidget(self.decrypt_file_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        return widget

    def _create_folder_tab(self) -> QWidget:
        """Create folder operations tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        info = QLabel("Bir klasör içindeki TÜM dosyaları işler.\nDikkatli kullanın!")
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 12px;
            background: transparent;
        """)
        layout.addWidget(info)

        layout.addWidget(create_spacer(10))

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.encrypt_folder_btn = GlowButton("🔒 Klasör Şifrele", accent="#ef4444")
        self.encrypt_folder_btn.setFixedHeight(48)
        self.encrypt_folder_btn.clicked.connect(self._on_encrypt_folder)
        btn_layout.addWidget(self.encrypt_folder_btn)

        self.decrypt_folder_btn = GlowButton("🔓 Klasör Çöz", accent="#22c55e")
        self.decrypt_folder_btn.setFixedHeight(48)
        self.decrypt_folder_btn.clicked.connect(self._on_decrypt_folder)
        btn_layout.addWidget(self.decrypt_folder_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        return widget

    # ========================================================================
    # FILE OPERATIONS
    # ========================================================================

    def _on_encrypt_file(self):
        """Encrypt a single file"""
        password = self.password_input.text()
        if not password:
            QMessageBox.warning(self, "Uyarı", "Lütfen parola girin!")
            return

        input_path, _ = QFileDialog.getOpenFileName(self, "Şifrelenecek Dosya Seç")
        if not input_path:
            return

        output_path = input_path + ".enc"

        self._log("Dosya şifreleme başlatılıyor...")
        self._set_busy(True)

        self.worker = FileEncryptWorker(input_path, output_path, password)
        self.worker.status.connect(self._log)
        self.worker.finished.connect(self._on_file_encrypt_finished)
        self.worker.failed.connect(self._on_worker_failed)
        self.worker.start()

    def _on_decrypt_file(self):
        """Decrypt a single file"""
        password = self.password_input.text()
        if not password:
            QMessageBox.warning(self, "Uyarı", "Lütfen parola girin!")
            return

        input_path, _ = QFileDialog.getOpenFileName(
            self,
            "Çözülecek Dosya Seç",
            "",
            "Encrypted Files (*.enc)"
        )
        if not input_path:
            return

        output_path = input_path.rsplit(".enc", 1)[0]

        self._log("Dosya çözme başlatılıyor...")
        self._set_busy(True)

        self.worker = FileDecryptWorker(input_path, output_path, password)
        self.worker.status.connect(self._log)
        self.worker.finished.connect(self._on_file_decrypt_finished)
        self.worker.failed.connect(self._on_worker_failed)
        self.worker.start()

    # ========================================================================
    # FOLDER OPERATIONS
    # ========================================================================

    def _on_encrypt_folder(self):
        """Encrypt all files in folder"""
        password = self.password_input.text()
        if not password:
            QMessageBox.warning(self, "Uyarı", "Lütfen parola girin!")
            return

        folder_path = QFileDialog.getExistingDirectory(self, "Şifrelenecek Klasör Seç")
        if not folder_path:
            return

        confirm = QMessageBox.question(
            self,
            "Onay",
            f"Bu klasördeki TÜM dosyalar şifrelenecek!\n\n{folder_path}\n\nDevam edilsin mi?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        self._log("Klasör şifreleme başlatılıyor...")
        self._set_busy(True)

        self.worker = FolderEncryptWorker(folder_path, password)
        self.worker.status.connect(self._log)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_folder_finished)
        self.worker.failed.connect(self._on_worker_failed)
        self.worker.start()

    def _on_decrypt_folder(self):
        """Decrypt all .enc files in folder"""
        password = self.password_input.text()
        if not password:
            QMessageBox.warning(self, "Uyarı", "Lütfen parola girin!")
            return

        folder_path = QFileDialog.getExistingDirectory(self, "Çözülecek Klasör Seç")
        if not folder_path:
            return

        confirm = QMessageBox.question(
            self,
            "Onay",
            f"Bu klasördeki TÜM .enc dosyalar çözülecek!\n\n{folder_path}\n\nDevam edilsin mi?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        self._log("Klasör çözme başlatılıyor...")
        self._set_busy(True)

        self.worker = FolderDecryptWorker(folder_path, password)
        self.worker.status.connect(self._log)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_folder_finished)
        self.worker.failed.connect(self._on_worker_failed)
        self.worker.start()

    # ========================================================================
    # CALLBACKS
    # ========================================================================

    def _on_file_encrypt_finished(self, result: dict):
        """File encryption completed"""
        self._set_busy(False)
        self._log("✅ Dosya başarıyla şifrelendi!")
        QMessageBox.information(self, "Başarılı", f"Dosya şifrelendi:\n{result['file']}")

    def _on_file_decrypt_finished(self, result: dict):
        """File decryption completed"""
        self._set_busy(False)
        self._log("✅ Dosya başarıyla çözüldü!")
        QMessageBox.information(self, "Başarılı", f"Dosya çözüldü:\n{result['file']}")

    def _on_folder_finished(self, result: dict):
        """Folder operation completed"""
        self._set_busy(False)
        success = result['success']
        errors = result['errors']

        msg = f"✅ İşlem tamamlandı!\n\nBaşarılı: {success}\nHata: {errors}"
        self._log(msg)
        QMessageBox.information(self, "Tamamlandı", msg)

    def _on_worker_failed(self, error: str):
        """Worker failed"""
        self._set_busy(False)
        self._log(f"❌ Hata: {error}")
        QMessageBox.critical(self, "Hata", f"İşlem başarısız:\n{error}")

    def _on_progress(self, ratio: float, current: int, total: int):
        """Update progress bar"""
        self.progress_bar.setValue(int(ratio * 100))

    def _log(self, message: str):
        """Add log message"""
        self.log_box.append(message)
        self.status_label.setText(message)

    def _set_busy(self, busy: bool):
        """Disable/enable buttons"""
        self.encrypt_file_btn.setEnabled(not busy)
        self.decrypt_file_btn.setEnabled(not busy)
        self.encrypt_folder_btn.setEnabled(not busy)
        self.decrypt_folder_btn.setEnabled(not busy)

        if not busy:
            self.progress_bar.setValue(0)
