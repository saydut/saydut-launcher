"""
Module Window for Saydut Launcher
Each module opens in its own separate window
"""
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCloseEvent
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from shared import GlowBackground
from .base_module import BaseModule
from .module_registry import ModuleRegistry


class ModuleWindow(QMainWindow):
    """
    Standalone window for a single module

    - Opens when user clicks a module in the launcher sidebar
    - Has its own GlowBackground
    - Handles module lifecycle (activate, deactivate, cleanup)
    """

    window_closed = Signal(str)  # Emits module_id when closed

    def __init__(
        self,
        module: BaseModule,
        registry: ModuleRegistry,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self.module = module
        self.registry = registry

        # Window setup
        self.setWindowTitle(f"{module.icon} {module.name}")
        self.resize(1100, 700)
        self.setFont(QFont("Segoe UI Variable", 10))
        self.setStyleSheet("QLabel { background: transparent; border: none; }")

        # Build UI
        self._setup_ui()

        # Activate module
        self.registry.activate_module(module.module_id)

    def _setup_ui(self):
        """Build window with GlowBackground + module widget"""
        root = GlowBackground()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(0)

        # Create the module's widget inside the glow background
        widget = self.module.create_widget(root)
        self.module.widget = widget
        layout.addWidget(widget, 1)

        self.setCentralWidget(root)

    def closeEvent(self, event: QCloseEvent):
        """Deactivate and cleanup when window closes"""
        mid = self.module.module_id
        try:
            self.registry.deactivate_module(mid)
        except Exception:
            pass

        # Clear cached widget so it can be recreated next time
        self.module.widget = None

        # Remove the module instance from registry cache
        # so a fresh one is created when opened again
        self.registry._module_instances.pop(mid, None)
        self.registry._first_load_done.discard(mid)

        self.window_closed.emit(mid)
        super().closeEvent(event)
