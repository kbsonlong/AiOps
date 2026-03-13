"""Dependency injection container for AIOps.

This module provides a simple dependency injection container to manage
component lifecycle and dependencies, improving testability and modularity.
"""

from dataclasses import dataclass, field
from typing import Dict, Type, Callable, Any, TypeVar, Optional
from threading import Lock
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class Container:
    """Simple dependency injection container.

    The container manages two types of registrations:
    - Factories: Functions that create new instances each time
    - Singletons: Instances that are created once and reused

    Example:
        ```python
        container = Container()

        # Register a factory
        container.register(Settings, lambda c: load_settings())

        # Register a singleton
        container.register_singleton(
            SkillRegistry,
            GlobalSkillRegistry()
        )

        # Get an instance
        settings = container.get(Settings)
        ```
    """

    _factories: Dict[Type, Callable[['Container'], Any]] = field(
        default_factory=dict,
        repr=False
    )
    _singletons: Dict[Type, Any] = field(
        default_factory=dict,
        repr=False
    )
    _factory_singletons: Dict[Type, Any] = field(
        default_factory=dict,
        repr=False
    )
    _lock: Lock = field(
        default_factory=Lock,
        repr=False
    )

    def register(
        self,
        interface: Type[T],
        factory: Callable[['Container'], T]
    ) -> None:
        """Register a factory function for an interface.

        The factory will be called each time the interface is requested.

        Args:
            interface: The type to register
            factory: A function that takes the container and returns an instance
        """
        with self._lock:
            self._factories[interface] = factory
            logger.debug(f"Registered factory for {interface.__name__}")

    def register_singleton(
        self,
        interface: Type[T],
        instance: T
    ) -> None:
        """Register a singleton instance.

        The same instance will be returned each time the interface is requested.

        Args:
            interface: The type to register
            instance: The instance to register
        """
        with self._lock:
            self._singletons[interface] = instance
            logger.debug(f"Registered singleton for {interface.__name__}")

    def register_factory_singleton(
        self,
        interface: Type[T],
        factory: Callable[['Container'], T]
    ) -> None:
        """Register a factory that creates a singleton on first access.

        The factory will be called once, and the result will be cached.

        Args:
            interface: The type to register
            factory: A function that takes the container and returns an instance
        """
        with self._lock:
            self._factories[interface] = factory
            logger.debug(
                f"Registered factory singleton for {interface.__name__}"
            )

    def get(self, interface: Type[T]) -> T:
        """Get an instance of the registered type.

        The lookup order is:
        1. Direct singletons
        2. Factory singletons (cached)
        3. Factories (creates new instance)

        Args:
            interface: The type to get

        Returns:
            An instance of the requested type

        Raises:
            ValueError: If the type is not registered
        """
        # Check direct singletons first
        if interface in self._singletons:
            return self._singletons[interface]

        # Check factory singletons (cached)
        if interface in self._factory_singletons:
            return self._factory_singletons[interface]

        # Check factories
        if interface in self._factories:
            instance = self._factories[interface](self)
            # Cache for future use
            self._factory_singletons[interface] = instance
            return instance

        raise ValueError(
            f"No registration for {interface.__name__}. "
            f"Did you forget to register it?"
        )

    def get_optional(self, interface: Type[T]) -> Optional[T]:
        """Get an instance of the registered type, or None if not registered.

        Args:
            interface: The type to get

        Returns:
            An instance of the requested type, or None
        """
        try:
            return self.get(interface)
        except ValueError:
            return None

    def has(self, interface: Type) -> bool:
        """Check if a type is registered.

        Args:
            interface: The type to check

        Returns:
            True if the type is registered, False otherwise
        """
        return (
            interface in self._singletons or
            interface in self._factory_singletons or
            interface in self._factories
        )

    def clear(self) -> None:
        """Clear all registrations.

        This is primarily useful for testing.
        """
        with self._lock:
            self._factories.clear()
            self._singletons.clear()
            self._factory_singletons.clear()
            logger.debug("Container cleared")


# Global container instance
_global_container: Optional[Container] = None
_container_lock = Lock()


def get_global_container() -> Container:
    """Get the global container instance.

    Returns:
        The global container instance
    """
    global _global_container
    if _global_container is None:
        with _container_lock:
            if _global_container is None:
                _global_container = Container()
    return _global_container


def reset_global_container() -> None:
    """Reset the global container.

    This is primarily useful for testing.
    """
    global _global_container
    with _container_lock:
        if _global_container is not None:
            _global_container.clear()
        _global_container = None
