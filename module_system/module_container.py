"""
Module Container for Saydut Launcher
Manages the QStackedWidget that displays module UIs
"""
from typing import Optional
from PySide6.QtWidgets import QStackedWidget, QWidget
from PySide6.QtCore import Signal, QPropertyAnimation, QEasingCurve, QPoint
from .module_registry import ModuleRegistry
from .base_module import BaseModule


class ModuleContainer(QStackedWidget):
    """
    Container widget for module UIs

    This is a QStackedWidget that:
    - Holds all module widgets
    - Switches between modules
    - Manages activation/deactivation
    - Provides smooth transitions (optional)

    Usage:
        container = ModuleContainer(registry)
        container.load_module("qr-code")  # Load and show QR module
        container.switch_to("encrypter")  # Switch to encrypter
    """

    # Signals
    module_changed = Signal(str)  # Emits module_id when switched
    module_loaded = Signal(str)  # Emits module_id when first loaded

    def __init__(self, registry: ModuleRegistry, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.registry = registry
        self._current_module_id: Optional[str] = None

        # Map module_id to widget index in stack
        self._module_indices: dict[str, int] = {}

        # Styling
        self.setStyleSheet(
            "QStackedWidget {"
            "background: transparent; "
            "border: none;"
            "}"
        )

    # ========================================================================
    # MODULE LOADING
    # ========================================================================

    def load_module(self, module_id: str) -> QWidget:
        """
        Load a module's widget into the container

        If the module is already loaded, returns the existing widget.
        Otherwise, creates the widget and adds it to the stack.

        Args:
            module_id: Module to load

        Returns:
            QWidget: The module's widget

        Raises:
            KeyError: If module_id is not registered

        Example:
            widget = container.load_module("qr-code")
        """
        # Check if already loaded
        if module_id in self._module_indices:
            index = self._module_indices[module_id]
            return self.widget(index)

        # Get module from registry
        module = self.registry.get_module(module_id)

        # Create widget
        widget = module.create_widget(self)
        module.widget = widget  # Cache reference

        # Add to stack
        index = self.addWidget(widget)
        self._module_indices[module_id] = index

        print(f"[Container] Loaded module widget: {module_id} (index {index})")

        # Emit signal
        self.module_loaded.emit(module_id)

        return widget

    def is_module_loaded(self, module_id: str) -> bool:
        """Check if a module's widget is loaded"""
        return module_id in self._module_indices

    # ========================================================================
    # MODULE SWITCHING
    # ========================================================================

    def switch_to(self, module_id: str, animate: bool = False) -> None:
        """
        Switch to a different module

        Handles:
        - Deactivating current module
        - Loading new module (if not loaded)
        - Switching QStackedWidget
        - Activating new module

        Args:
            module_id: Module to switch to
            animate: Whether to animate the transition (experimental)

        Example:
            container.switch_to("encrypter")
        """
        # Deactivate current module
        if self._current_module_id:
            self.registry.deactivate_module(self._current_module_id)

        # Load module if needed
        if not self.is_module_loaded(module_id):
            self.load_module(module_id)

        # Switch to module
        index = self._module_indices[module_id]
        self.setCurrentIndex(index)

        # Activate new module
        self.registry.activate_module(module_id)
        self._current_module_id = module_id

        print(f"[Container] Switched to module: {module_id}")

        # Emit signal
        self.module_changed.emit(module_id)

    def get_current_module_id(self) -> Optional[str]:
        """Get the currently active module ID"""
        return self._current_module_id

    def get_current_module(self) -> Optional[BaseModule]:
        """Get the currently active module instance"""
        if not self._current_module_id:
            return None
        return self.registry.get_module(self._current_module_id)

    # ========================================================================
    # PRELOADING (PERFORMANCE OPTIMIZATION)
    # ========================================================================

    def preload_modules(self, module_ids: list[str]) -> None:
        """
        Preload modules in the background (performance optimization)

        Loads module widgets without activating them.
        Useful for frequently used modules.

        Args:
            module_ids: List of module IDs to preload

        Example:
            # Preload top 3 modules
            container.preload_modules(["qr-code", "encrypter", "password-manager"])
        """
        for module_id in module_ids:
            if not self.is_module_loaded(module_id):
                print(f"[Container] Preloading: {module_id}")
                self.load_module(module_id)

    def preload_all(self) -> None:
        """
        Preload all registered modules (not recommended for many modules)

        Only use this if you have few modules and want instant switching.
        """
        for module_id in self.registry._module_classes.keys():
            if not self.is_module_loaded(module_id):
                self.load_module(module_id)

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_loaded_modules(self) -> list[str]:
        """Get list of loaded module IDs"""
        return list(self._module_indices.keys())

    def get_stats(self) -> dict:
        """Get container statistics"""
        return {
            'total_widgets': self.count(),
            'loaded_modules': len(self._module_indices),
            'current_module': self._current_module_id,
            'module_ids': list(self._module_indices.keys()),
        }

    def __repr__(self) -> str:
        return (
            f"<ModuleContainer "
            f"widgets={self.count()} "
            f"current={self._current_module_id}>"
        )
