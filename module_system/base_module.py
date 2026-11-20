"""
Base Module Interface for Saydut Launcher
All modules must inherit from BaseModule and implement the required methods
"""
from abc import ABC, abstractmethod
from typing import Optional
from PySide6.QtWidgets import QWidget


class BaseModule(ABC):
    """
    Abstract base class for all launcher modules

    Each module represents a self-contained application (QR Code, Encrypter, etc.)
    that can be loaded and displayed within the launcher's module container.

    Lifecycle:
    1. Module class is registered with ModuleRegistry
    2. User selects module from sidebar
    3. create_widget() is called to build the UI (lazy loading)
    4. on_activate() is called when module becomes visible
    5. on_deactivate() is called when user switches to another module
    6. cleanup() is called before module is destroyed (app exit)

    Example:
        class QrCodeModule(BaseModule):
            def __init__(self):
                super().__init__()
                self.module_id = "qr-code"
                self.name = "QR Kod Oluşturucu"
                self.icon = "🎨"
                self.theme_accent = "#38bdf8"

            def create_widget(self, parent):
                # Build and return the module's UI
                widget = QWidget(parent)
                # ... setup UI
                return widget

            def on_activate(self):
                # Called when module is shown
                print("QR module activated")

            def on_deactivate(self):
                # Called when module is hidden
                print("QR module deactivated")
    """

    def __init__(self):
        # Module identification
        self.module_id: str = ""  # Unique ID (e.g., "qr-code")
        self.name: str = ""  # Display name (e.g., "QR Kod Oluşturucu")
        self.category: str = ""  # Category (e.g., "utility", "security")
        self.description: str = ""  # Short description
        self.version: str = "1.0"  # Module version

        # UI properties
        self.icon: str = ""  # Emoji or icon path (e.g., "🎨")
        self.theme_accent: str = "#38bdf8"  # Accent color for UI

        # System requirements
        self.requires_admin: bool = False  # True for admin-only modules
        self.requires_internet: bool = False  # True if internet is needed

        # Internal state
        self.widget: Optional[QWidget] = None  # Cached widget instance
        self._is_active: bool = False  # Whether module is currently visible

    # ========================================================================
    # ABSTRACT METHODS - Must be implemented by subclasses
    # ========================================================================

    @abstractmethod
    def create_widget(self, parent: QWidget) -> QWidget:
        """
        Create and return the module's main widget

        This method is called once when the module is first accessed (lazy loading).
        The returned widget will be added to the launcher's QStackedWidget.

        Args:
            parent: Parent widget (the QStackedWidget container)

        Returns:
            QWidget: The module's main UI widget

        Example:
            def create_widget(self, parent):
                from shared import GlowButton, ModernCard, AnimatedHeader

                widget = QWidget(parent)
                layout = QVBoxLayout(widget)

                # Add header
                header = AnimatedHeader("🎨 QR Kod", "QR codes made easy")
                layout.addWidget(header)

                # Add content
                card = ModernCard(accent=self.theme_accent)
                # ... setup card content
                layout.addWidget(card)

                return widget
        """
        pass

    @abstractmethod
    def on_activate(self) -> None:
        """
        Called when the module becomes visible (user selects it)

        Use this to:
        - Start background tasks
        - Refresh data
        - Resume timers
        - Update UI state

        Example:
            def on_activate(self):
                self._is_active = True
                self.refresh_data()
                self.status_label.setText("Module active")
        """
        pass

    @abstractmethod
    def on_deactivate(self) -> None:
        """
        Called when the module is hidden (user switches to another module)

        Use this to:
        - Pause background tasks
        - Stop timers
        - Save state
        - Release resources

        Example:
            def on_deactivate(self):
                self._is_active = False
                self.pause_background_tasks()
                self.save_state()
        """
        pass

    # ========================================================================
    # OPTIONAL METHODS - Can be overridden by subclasses
    # ========================================================================

    def cleanup(self) -> None:
        """
        Called before the module is destroyed (application exit)

        Use this to:
        - Close file handles
        - Stop threads
        - Save persistent data
        - Release system resources

        Default implementation does nothing.

        Example:
            def cleanup(self):
                self.stop_worker_thread()
                self.save_config()
                self.close_database()
        """
        pass

    def on_first_load(self) -> None:
        """
        Called once after create_widget(), before first on_activate()

        Use this for one-time initialization that requires the widget to exist.

        Example:
            def on_first_load(self):
                self.load_saved_settings()
                self.populate_initial_data()
        """
        pass

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def is_active(self) -> bool:
        """Check if module is currently active (visible)"""
        return self._is_active

    def get_metadata(self) -> dict:
        """
        Get module metadata as dictionary

        Returns:
            dict: Module metadata for display in sidebar
        """
        return {
            'id': self.module_id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'version': self.version,
            'icon': self.icon,
            'accent': self.theme_accent,
            'requires_admin': self.requires_admin,
            'requires_internet': self.requires_internet,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.module_id} name={self.name}>"
