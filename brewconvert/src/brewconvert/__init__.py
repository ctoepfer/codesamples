from __future__ import annotations

from pathlib import Path

from .detect import detect_format
from .model import Recipe


def read_recipes(path: str | Path, format: str | None = None) -> list[Recipe]:
    fmt = format or detect_format(path)
    if fmt == "beerxml":
        from .formats.beerxml import read
        return read(path)
    if fmt == "beersmith-bsmx":
        from .formats.beersmith import read
        return read(path)
    if fmt == "beerjson":
        from .formats.beerjson import read
        return read(path)
    if fmt == "brewfather-json":
        from .formats.brewfather import read
        return read(path)
    if fmt == "beertools-btp":
        from .formats.beertools import read
        return read(path)
    if fmt == "promash-text":
        from .formats.promash import read
        return read(path)
    raise ValueError(f"Unsupported input format: {fmt}")


def write_recipes(recipes: list[Recipe], path: str | Path, format: str | None = None, profile: str | None = None) -> None:
    fmt = format
    if fmt is None:
        suffix = Path(path).suffix.lower()
        if suffix == ".bsmx":
            fmt = "beersmith-bsmx"
        elif suffix == ".beerjson":
            fmt = "beerjson"
        elif suffix in {".json", ".brewfather"}:
            fmt = "brewfather-json"
        elif suffix in {".btp", ".btt"}:
            fmt = "beertools-btp"
        elif suffix in {".txt", ".promash"}:
            fmt = "promash-text"
        elif suffix == ".xml":
            fmt = "beerxml"
        else:
            fmt = None
    if fmt == "beerxml":
        from .formats.beerxml import write
        return write(recipes, path, profile=profile)
    if fmt == "beersmith-bsmx":
        from .formats.beersmith import write
        return write(recipes, path, profile=profile)
    if fmt == "beerjson":
        from .formats.beerjson import write
        return write(recipes, path, profile=profile)
    if fmt == "brewfather-json":
        from .formats.brewfather import write
        return write(recipes, path, profile=profile)
    if fmt == "beertools-btp":
        from .formats.beertools import write
        return write(recipes, path, profile=profile)
    if fmt == "promash-text":
        from .formats.promash import write
        return write(recipes, path, profile=profile)
    raise ValueError(f"Unsupported output format: {fmt}")

__all__ = ["Recipe", "detect_format", "read_recipes", "write_recipes"]
