"""Adapter layer that unifies multiple internet search providers."""

from abc import ABC, abstractmethod
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .schema import SearchResult


class SearchProvider(ABC):
    """Abstract base class for an internet search provider adapter."""

    name: str = "unknown"

    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int,
        **kwargs: Any,
    ) -> List[SearchResult]:
        """Run a search and return results normalized to the common schema.

        Args:
            query: The search query string.
            max_results: Maximum number of results to return.
            **kwargs: Provider-specific options.

        Returns:
            A list of normalized search results.
        """
        raise NotImplementedError


class SearchAdapter:
    """Registry and dispatcher for search provider adapters."""

    def __init__(self) -> None:
        self._providers: Dict[str, SearchProvider] = {}

    def register(self, provider: SearchProvider) -> None:
        """Register a provider instance by its declared name."""
        self._providers[provider.name] = provider

    def get(self, name: str) -> SearchProvider:
        """Retrieve a registered provider by name."""
        name = name.lower()
        if name not in self._providers:
            raise ValueError(
                f"Unsupported search provider: {name}. "
                f"Available: {', '.join(sorted(self._providers))}"
            )
        return self._providers[name]

    def list_providers(self) -> List[str]:
        """Return the names of all registered providers."""
        return sorted(self._providers)

    def search(
        self,
        provider_name: str,
        query: str,
        max_results: int,
        **kwargs: Any,
    ) -> List[SearchResult]:
        """Dispatch a search to the named provider."""
        provider = self.get(provider_name)
        return provider.search(query=query, max_results=max_results, **kwargs)


def _discover_provider_classes(package_dir: Path) -> List[Type[SearchProvider]]:
    """Auto-discover concrete SearchProvider classes in a package directory."""
    classes: List[Type[SearchProvider]] = []
    for path in package_dir.glob("*.py"):
        if path.name.startswith("_"):
            continue
        module_name = f"{__package__}.providers.{path.stem}"
        try:
            module = import_module(module_name)
        except Exception:
            # A broken provider module should not prevent the rest from loading.
            continue
        for obj in vars(module).values():
            if (
                isinstance(obj, type)
                and issubclass(obj, SearchProvider)
                and obj is not SearchProvider
                and getattr(obj, "name", None)
            ):
                classes.append(obj)
    return classes


def build_adapter(
    package_dir: Optional[Path] = None,
    extra_providers: Optional[Dict[str, SearchProvider]] = None,
) -> SearchAdapter:
    """Create an adapter populated with auto-discovered providers.

    Args:
        package_dir: Directory containing provider modules. Defaults to the
            sibling `providers/` directory.
        extra_providers: Optional mapping of additional provider instances to
            register after discovery.

    Returns:
        A configured SearchAdapter instance.
    """
    if package_dir is None:
        package_dir = Path(__file__).resolve().parent / "providers"

    adapter = SearchAdapter()
    for provider_class in _discover_provider_classes(package_dir):
        adapter.register(provider_class())

    for provider in (extra_providers or {}).values():
        adapter.register(provider)

    return adapter
