"""
Module Registry for Saydut Launcher
Handles module registration, discovery, and lazy loading
"""
from typing import Dict, List, Type, Optional
from .base_module import BaseModule


class ModuleRegistry:
    """
    Central registry for all launcher modules

    Responsibilities:
    - Register module classes
    - Lazy load module instances (create only when needed)
    - Provide module metadata
    - Manage module lifecycle

    Usage:
        # Create registry
        registry = ModuleRegistry()

        # Register modules
        registry.register(QrCodeModule)
        registry.register(EncrypterModule)

        # Get module metadata (without loading)
        modules = registry.list_modules()

        # Load and get module instance (lazy)
        qr_module = registry.get_module("qr-code")
        widget = qr_module.create_widget(parent)
    """

    def __init__(self):
        # Store module classes (not instances) for lazy loading
        self._module_classes: Dict[str, Type[BaseModule]] = {}

        # Store module instances (created on first access)
        self._module_instances: Dict[str, BaseModule] = {}

        # Track loaded state
        self._first_load_done: set[str] = set()

    # ========================================================================
    # REGISTRATION
    # ========================================================================

    def register(self, module_class: Type[BaseModule]) -> None:
        """
        Register a module class

        The module is not instantiated yet (lazy loading).
        A temporary instance is created just to get metadata.

        Args:
            module_class: A class that inherits from BaseModule

        Raises:
            ValueError: If module_id is empty or already registered
            TypeError: If module_class doesn't inherit from BaseModule

        Example:
            registry.register(QrCodeModule)
            registry.register(EncrypterModule)
        """
        # Validate
        if not issubclass(module_class, BaseModule):
            raise TypeError(
                f"{module_class.__name__} must inherit from BaseModule"
            )

        # Create temporary instance to get module_id
        temp_instance = module_class()

        if not temp_instance.module_id:
            raise ValueError(
                f"{module_class.__name__} must set module_id in __init__()"
            )

        if temp_instance.module_id in self._module_classes:
            raise ValueError(
                f"Module ID '{temp_instance.module_id}' is already registered"
            )

        # Store the class (not the instance)
        self._module_classes[temp_instance.module_id] = module_class

        print(f"[Registry] Registered module: {temp_instance.module_id} "
              f"({temp_instance.name})")

    def register_all(self, module_classes: List[Type[BaseModule]]) -> None:
        """
        Register multiple modules at once

        Args:
            module_classes: List of module classes

        Example:
            registry.register_all([
                QrCodeModule,
                EncrypterModule,
                PasswordManagerModule,
            ])
        """
        for module_class in module_classes:
            self.register(module_class)

    # ========================================================================
    # MODULE ACCESS
    # ========================================================================

    def get_module(self, module_id: str) -> BaseModule:
        """
        Get module instance by ID (lazy loading)

        If the module hasn't been loaded yet, it will be instantiated.
        Otherwise, the cached instance is returned.

        Args:
            module_id: Unique module identifier

        Returns:
            BaseModule: The module instance

        Raises:
            KeyError: If module_id is not registered

        Example:
            qr_module = registry.get_module("qr-code")
            widget = qr_module.create_widget(parent)
        """
        # Check if registered
        if module_id not in self._module_classes:
            raise KeyError(f"Module '{module_id}' is not registered")

        # Return cached instance if already loaded
        if module_id in self._module_instances:
            return self._module_instances[module_id]

        # Lazy load: Create instance now
        module_class = self._module_classes[module_id]
        instance = module_class()

        # Cache the instance
        self._module_instances[module_id] = instance

        print(f"[Registry] Lazy loaded module: {module_id}")

        return instance

    def has_module(self, module_id: str) -> bool:
        """Check if a module is registered"""
        return module_id in self._module_classes

    def is_loaded(self, module_id: str) -> bool:
        """Check if a module has been instantiated"""
        return module_id in self._module_instances

    # ========================================================================
    # METADATA
    # ========================================================================

    def list_modules(self) -> List[dict]:
        """
        Get metadata for all registered modules (without loading them)

        Returns:
            List[dict]: List of module metadata dictionaries

        Example:
            modules = registry.list_modules()
            for module in modules:
                print(module['name'], module['icon'])
        """
        metadata_list = []

        for module_id, module_class in self._module_classes.items():
            # Check if already loaded
            if module_id in self._module_instances:
                metadata = self._module_instances[module_id].get_metadata()
            else:
                # Create temporary instance just for metadata
                temp = module_class()
                metadata = temp.get_metadata()

            metadata_list.append(metadata)

        # Sort by name
        metadata_list.sort(key=lambda m: m['name'])

        return metadata_list

    def get_modules_by_category(self, category: str) -> List[dict]:
        """
        Get modules filtered by category

        Args:
            category: Category name (e.g., "utility", "security")

        Returns:
            List[dict]: Filtered module metadata

        Example:
            security_modules = registry.get_modules_by_category("security")
        """
        all_modules = self.list_modules()
        return [m for m in all_modules if m['category'] == category]

    # ========================================================================
    # LIFECYCLE MANAGEMENT
    # ========================================================================

    def activate_module(self, module_id: str) -> BaseModule:
        """
        Activate a module (call on_activate)

        This is typically called when a user selects a module from the sidebar.

        Args:
            module_id: Module to activate

        Returns:
            BaseModule: The activated module

        Example:
            module = registry.activate_module("qr-code")
        """
        module = self.get_module(module_id)

        # Call on_first_load if this is the first time
        if module_id not in self._first_load_done:
            module.on_first_load()
            self._first_load_done.add(module_id)

        # Activate
        module._is_active = True
        module.on_activate()

        print(f"[Registry] Activated module: {module_id}")

        return module

    def deactivate_module(self, module_id: str) -> None:
        """
        Deactivate a module (call on_deactivate)

        Args:
            module_id: Module to deactivate

        Example:
            registry.deactivate_module("qr-code")
        """
        if not self.is_loaded(module_id):
            return  # Module not loaded, nothing to deactivate

        module = self._module_instances[module_id]
        module._is_active = False
        module.on_deactivate()

        print(f"[Registry] Deactivated module: {module_id}")

    def cleanup_all(self) -> None:
        """
        Call cleanup() on all loaded modules (app shutdown)

        Example:
            # On application exit
            registry.cleanup_all()
        """
        for module_id, module in self._module_instances.items():
            print(f"[Registry] Cleaning up module: {module_id}")
            try:
                module.cleanup()
            except Exception as e:
                print(f"[Registry] Error cleaning up {module_id}: {e}")

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_stats(self) -> dict:
        """
        Get registry statistics

        Returns:
            dict: Stats (registered count, loaded count, etc.)

        Example:
            stats = registry.get_stats()
            print(f"Loaded: {stats['loaded']} / {stats['registered']}")
        """
        return {
            'registered': len(self._module_classes),
            'loaded': len(self._module_instances),
            'module_ids': list(self._module_classes.keys()),
            'loaded_ids': list(self._module_instances.keys()),
        }

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"<ModuleRegistry "
            f"registered={stats['registered']} "
            f"loaded={stats['loaded']}>"
        )


# ============================================================================
# GLOBAL REGISTRY INSTANCE
# ============================================================================

# Create a global registry instance that can be imported
_global_registry: Optional[ModuleRegistry] = None


def get_global_registry() -> ModuleRegistry:
    """
    Get the global module registry instance

    This is a singleton pattern - there's only one registry per application.

    Returns:
        ModuleRegistry: The global registry

    Example:
        from module_system import get_global_registry

        registry = get_global_registry()
        qr_module = registry.get_module("qr-code")
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ModuleRegistry()
    return _global_registry
