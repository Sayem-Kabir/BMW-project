"""Feature store package — Spec Section 19.3."""

from ml.feature_store.feast_stub import list_entities, read_features, write_features

__all__ = ["write_features", "read_features", "list_entities"]
