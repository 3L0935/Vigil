"""Qt Quick presentation package for Vigil.

This package stays independent from the voice runtime so its views can be
loaded by visual fixtures and platform UI tests.
"""

from .app import create_engine

__all__ = ["create_engine"]
