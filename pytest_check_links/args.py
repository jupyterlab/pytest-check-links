"""Argparse handlers."""
from __future__ import annotations

import argparse
import json
from typing import Any


class StoreExtensionsAction(argparse.Action):
    """Store extensions action."""

    def __init__(
        self, option_strings: list[str], dest: str, nargs: int | None = None, **kwargs: Any
    ) -> None:
        """Initialize the action."""
        if nargs is not None:
            msg = "nargs not allowed"
            raise ValueError(msg)
        super().__init__(option_strings, dest, **kwargs)

    def __call__(  # type:ignore[override]
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str,
        option_string: str | None = None,
    ) -> None:
        """Evaluate the action."""
        parsed = self.parse_extensions(values)
        setattr(namespace, self.dest, parsed)

    def parse_extensions(self, csv: str) -> set[str]:
        """Parse extensions."""
        return {".%s" % ext.lstrip(".") for ext in csv.split(",")}


class StoreCacheAction(argparse.Action):
    """Build the cache session kwargs"""

    def __call__(  # type:ignore[override]
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str,
        option_string: str | None = None,
    ) -> None:
        """Evaluate the action."""
        ns_name = "check_links_cache_kwargs"
        if not hasattr(namespace, ns_name):
            setattr(namespace, ns_name, {})
        dest = self.dest.replace("check_links_cache_", "")
        kwargs = namespace.check_links_cache_kwargs
        if dest == "name":
            kwargs["cache_name"] = values
        elif dest == "expire_after":
            kwargs["expire_after"] = float(values)
        elif dest == "backend_opt":
            key, value = str(values).split(":", 1)
            try:
                kwargs[key] = json.loads(value)
            except Exception:
                kwargs[key] = value
        else:
            kwargs[dest] = values
