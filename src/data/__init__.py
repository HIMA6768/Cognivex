"""Repository-owned biomedical data services."""

from .metabric import MetabricPaths, load_metabric

__all__ = ["MetabricPaths", "load_metabric"]
