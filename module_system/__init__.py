"""
Module System for Saydut Launcher
Plugin-based architecture with lazy loading
"""
from .base_module import BaseModule
from .module_registry import ModuleRegistry, get_global_registry
from .module_container import ModuleContainer
from .module_window import ModuleWindow

__all__ = [
    'BaseModule',
    'ModuleRegistry',
    'ModuleContainer',
    'ModuleWindow',
    'get_global_registry',
]
