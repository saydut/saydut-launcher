"""
Password Manager Module UI
PySide6 interface for password management
"""
import os
from typing import Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QScrollArea,
    QDialog,
    QMessageBox,
    QApplication,
)

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

from .database import PassDB


# ============================================================================
# MASTER PASSWORD DIALOG
# ============================================================================

class MasterPasswordDialog(QDialog):
    """Dialog for master password input"""

    def __init__(self, db: PassDB, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.master_password: Optional[str] = None

        self.setWindowTitle("Master Şifre")
        self.setFixedSize(400, 250)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("🔑 Master Şifre")
        title.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 20px;
            font-weight: 700;
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Description
        if self.db.has_master():
            desc_text = "Şifre kasanızı açmak için master şifrenizi girin:"
        else:
            desc_text = "Yeni bir master şifre oluşturun.\nBu şifre tüm şifrelerinizi koruyacak!"

        desc = QLabel(desc_text)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 12px;
        """)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        layout.addWidget(create_spacer(10))

        # Password input
        self.password_input = ModernInput(
            placeholder="Master şifre...",
            accent="#22c55e"
        )
        self.password_input.setEchoMode(ModernInput.Password)
        self.password_input.setFixedHeight(44)
        self.password_input.returnPressed.connect(self._on_ok)
        layout.addWidget(self.password_input)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.ok_btn = GlowButton("Devam", accent="#22c55e")
        self.ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(self.ok_btn)

        self.cancel_btn = OutlineButton("İptal")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def _on_ok(self):
        """Validate and accept"""
        password = self.password_input.text()
        if not password:
            QMessageBox.warning(self, "Uyarı", "Master şifre boş olamaz!")
            return

        # If master exists, verify it
        if self.db.has_master():
            if not self.db.verify_master(password):
                QMessageBox.critical(self, "Hata", "Master şifre yanlış!")
                return
        else:
            # Set new master password
            self.db.set_master(password)

        self.master_password = password
        self.accept()


# ============================================================================
# PASSWORD CARD
# ============================================================================

class PasswordCard(ModernCard):
    """Card widget for displaying password entry"""

    def __init__(
        self,
        entry_id: int,
        site: str,
        username: str,
        password: str,
        notes: str,
        on_copy_callback,
        on_delete_callback
    ):
        super().__init__()
        self.entry_id = entry_id
        self.site = site
        self.username = username
        self.password = password
        self.notes = notes

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Site name
        site_label = QLabel(f"🌐 {site}")
        site_label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 14px;
            font-weight: 700;
            background: transparent;
        """)
        layout.addWidget(site_label)

        # Username
        if username:
            username_label = QLabel(f"👤 {username}")
            username_label.setStyleSheet(f"""
                color: {Colors.TEXT_SECONDARY};
                font-size: 12px;
                background: transparent;
            """)
            layout.addWidget(username_label)

        # Password (masked)
        pass_label = QLabel(f"🔒 {'•' * 12}")
        pass_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 12px;
            background: transparent;
        """)
        layout.addWidget(pass_label)

        # Notes
        if notes:
            notes_label = QLabel(f"📝 {notes[:50]}{'...' if len(notes) > 50 else ''}")
            notes_label.setStyleSheet(f"""
                color: {Colors.TEXT_SECONDARY};
                font-size: 11px;
                font-style: italic;
                background: transparent;
            """)
            layout.addWidget(notes_label)

        layout.addWidget(create_separator())

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        copy_btn = OutlineButton("📋 Kopyala")
        copy_btn.clicked.connect(lambda: on_copy_callback(self.password))
        btn_layout.addWidget(copy_btn)

        delete_btn = OutlineButton("🗑️ Sil")
        delete_btn.clicked.connect(lambda: on_delete_callback(self.entry_id))
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)


# ============================================================================
# MAIN WIDGET
# ============================================================================

class PasswordManagerWidget(QWidget):
    """
    Main Password Manager Widget

    Features:
    - Master password protection
    - Encrypted password storage
    - Copy to clipboard with auto-clear
    - Add/delete entries
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Database
        db_path = os.path.join(
            os.path.expanduser("~"),
            ".saydut",
            "password_manager",
            "passwords.db"
        )
        self.db = PassDB(db_path)

        self.master_password: Optional[str] = None
        self.clipboard_timer: Optional[QTimer] = None

        self._setup_ui()
        self._unlock()

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

        title = QLabel("🔑 Saydut Pass")
        title.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 24px;
            font-weight: 800;
            background: transparent;
        """)
        header_layout.addWidget(title)

        subtitle = QLabel("Güvenli Şifre Yöneticisi - AES-256-GCM")
        subtitle.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 12px;
            background: transparent;
        """)
        header_layout.addWidget(subtitle)

        layout.addWidget(header_card)

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

        # List tab
        self.list_tab = self._create_list_tab()
        self.tabs.addTab(self.list_tab, "Şifreler")

        # Add tab
        self.add_tab = self._create_add_tab()
        self.tabs.addTab(self.add_tab, "Yeni Ekle")

        layout.addWidget(self.tabs, 1)

    def _create_list_tab(self) -> QWidget:
        """Create password list tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Refresh button
        refresh_btn = GlowButton("🔄 Yenile", accent=Colors.ACCENT_BLUE)
        refresh_btn.clicked.connect(self._refresh_list)
        layout.addWidget(refresh_btn)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 4px 0 4px 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(71, 85, 105, 0.5);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(71, 85, 105, 0.8);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
                background: transparent;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(12)
        self.list_layout.addStretch()

        scroll.setWidget(self.list_container)
        layout.addWidget(scroll, 1)

        return widget

    def _create_add_tab(self) -> QWidget:
        """Create add entry tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Site input
        site_label = QLabel("Site / Hizmet:")
        site_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600;")
        layout.addWidget(site_label)

        self.site_input = ModernInput(placeholder="Örn: github.com", accent="#22c55e")
        layout.addWidget(self.site_input)

        layout.addWidget(create_spacer(8))

        # Username input
        username_label = QLabel("Kullanıcı Adı / E-posta:")
        username_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600;")
        layout.addWidget(username_label)

        self.username_input = ModernInput(placeholder="Kullanıcı adı", accent="#22c55e")
        layout.addWidget(self.username_input)

        layout.addWidget(create_spacer(8))

        # Password input
        password_label = QLabel("Şifre:")
        password_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600;")
        layout.addWidget(password_label)

        self.new_pass_input = ModernInput(placeholder="Şifre", accent="#22c55e")
        self.new_pass_input.setEchoMode(ModernInput.Password)
        layout.addWidget(self.new_pass_input)

        layout.addWidget(create_spacer(8))

        # Notes input
        notes_label = QLabel("Notlar (Opsiyonel):")
        notes_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600;")
        layout.addWidget(notes_label)

        self.notes_input = ModernTextBox(placeholder="Ek bilgiler...")
        self.notes_input.setMaximumHeight(100)
        layout.addWidget(self.notes_input)

        layout.addWidget(create_spacer(12))

        # Add button
        add_btn = GlowButton("➕ Şifre Ekle", accent="#22c55e")
        add_btn.setFixedHeight(48)
        add_btn.clicked.connect(self._on_add_entry)
        layout.addWidget(add_btn)

        layout.addStretch()

        return widget

    # ========================================================================
    # LOGIC
    # ========================================================================

    def _unlock(self):
        """Show master password dialog"""
        dialog = MasterPasswordDialog(self.db, self)
        if dialog.exec() == QDialog.Accepted:
            self.master_password = dialog.master_password
            self._refresh_list()
        else:
            # User cancelled, close module
            QMessageBox.warning(
                self,
                "Uyarı",
                "Master şifre girilmeden devam edilemez."
            )

    def _refresh_list(self):
        """Refresh password list"""
        if not self.master_password:
            return

        # Clear existing cards
        for i in reversed(range(self.list_layout.count())):
            item = self.list_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        # Load entries
        try:
            entries = self.db.get_all_entries(self.master_password)

            if not entries:
                no_entries = QLabel("Henüz şifre eklenmedi.")
                no_entries.setAlignment(Qt.AlignCenter)
                no_entries.setStyleSheet(f"""
                    color: {Colors.TEXT_SECONDARY};
                    font-size: 14px;
                    padding: 40px;
                """)
                self.list_layout.insertWidget(0, no_entries)
            else:
                for entry_id, site, username, password, notes in entries:
                    card = PasswordCard(
                        entry_id,
                        site,
                        username,
                        password,
                        notes,
                        self._copy_to_clipboard,
                        self._delete_entry
                    )
                    self.list_layout.insertWidget(self.list_layout.count() - 1, card)

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Şifreler yüklenemedi:\n{e}")

    def _on_add_entry(self):
        """Add new password entry"""
        if not self.master_password:
            return

        site = self.site_input.text().strip()
        username = self.username_input.text().strip()
        password = self.new_pass_input.text()
        notes = self.notes_input.toPlainText().strip()

        if not site:
            QMessageBox.warning(self, "Uyarı", "Site adı boş olamaz!")
            return

        if not password:
            QMessageBox.warning(self, "Uyarı", "Şifre boş olamaz!")
            return

        try:
            self.db.add_entry(self.master_password, site, username, password, notes)

            # Clear inputs
            self.site_input.clear()
            self.username_input.clear()
            self.new_pass_input.clear()
            self.notes_input.clear()

            # Refresh list
            self._refresh_list()

            # Switch to list tab
            self.tabs.setCurrentIndex(0)

            QMessageBox.information(self, "Başarılı", "Şifre başarıyla eklendi!")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Şifre eklenemedi:\n{e}")

    def _delete_entry(self, entry_id: int):
        """Delete password entry"""
        confirm = QMessageBox.question(
            self,
            "Onay",
            "Bu şifreyi silmek istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        try:
            self.db.delete_entry(entry_id)
            self._refresh_list()
            QMessageBox.information(self, "Başarılı", "Şifre silindi!")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Şifre silinemedi:\n{e}")

    def _copy_to_clipboard(self, password: str):
        """Copy password to clipboard with auto-clear"""
        clipboard = QApplication.clipboard()
        clipboard.setText(password)

        # Clear clipboard after 20 seconds
        if self.clipboard_timer:
            self.clipboard_timer.stop()

        self.clipboard_timer = QTimer(self)
        self.clipboard_timer.setSingleShot(True)
        self.clipboard_timer.timeout.connect(lambda: clipboard.clear())
        self.clipboard_timer.start(20000)  # 20 seconds

        QMessageBox.information(
            self,
            "Kopyalandı",
            "Şifre panoya kopyalandı!\n20 saniye sonra otomatik temizlenecek."
        )
