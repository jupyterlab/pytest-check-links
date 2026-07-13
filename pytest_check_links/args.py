"""Argparse handlers."""
from __future__ import annotations

import argparse
import json
import re
from typing import Any


def parse_status_codes(spec: str) -> list[int]:
    """Parse HTTP status codes and ranges."""
    codes: set[int] = set()
    for token in re.split(r"[\s,]+", spec.strip()):
        if not token:
            continue

        if ".." in token:
            parts = token.split("..", 1)
        elif "-" in token:
            parts = token.split("-", 1)
        else:
            parts = [token]

        try:
            if len(parts) == 1:
                start = end = int(parts[0])
            else:
                start, end = int(parts[0]), int(parts[1])
        except ValueError as err:
            msg = f"Invalid HTTP status code: {token}"
            raise argparse.ArgumentTypeError(msg) from err

        if start > end:
            msg = f"Invalid HTTP status range: {token}"
            raise argparse.ArgumentTypeError(msg)
        if start < 100 or end > 599:
            msg = f"Invalid HTTP status code: {token}"
            raise argparse.ArgumentTypeError(msg)
        codes.update(range(start, end + 1))

    return sorted(codes)


def parse_timeout(spec: str) -> float:
    """Parse a positive request timeout."""
    try:
        timeout = float(spec)
    except ValueError as err:
        msg = f"Invalid request timeout: {spec}"
        raise argparse.ArgumentTypeError(msg) from err
    if timeout <= 0:
        msg = "Request timeout must be greater than 0"
        raise argparse.ArgumentTypeError(msg)
    return timeout


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
        elif dest == "allowable_codes":
            kwargs["allowable_codes"] = parse_status_codes(values)
        elif dest == "backend_opt":
            key, value = str(values).split(":", 1)
            try:
                kwargs[key] = json.loads(value)
            except Exception:
                kwargs[key] = value
        else:
            kwargs[dest] = values
