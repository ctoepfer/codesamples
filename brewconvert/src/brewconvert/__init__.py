from __future__ import annotations

from pathlib import Path

from .detect import detect_format
from .model import Recipe


def read_recipes(
    path: str | Path, format: str | None = None, *, report=None, strict: bool = False
) -> list[Recipe]:
    fmt = format or detect_format(path)
    if fmt == "beerxml":
        from .formats.beerxml import read

        return read(path, report=report, strict=strict)
    if fmt == "beersmith-bsmx":
        from .formats.beersmith import read

        return read(path, report=report, strict=strict)
    if fmt == "beerjson":
        from .formats.beerjson import read

        return read(path, report=report, strict=strict)
    if fmt == "brewfather-json":
        from .formats.brewfather import read

        return read(path, report=report, strict=strict)
    if fmt == "beertools-btp":
        from .formats.beertools import read

        return read(path, report=report, strict=strict)
    if fmt == "promash-text":
        from .formats.promash import read

        return read(path, report=report, strict=strict)
    raise ValueError(f"Unsupported input format: {fmt}")


def write_recipes(
    recipes: list[Recipe],
    path: str | Path,
    format: str | None = None,
    profile: str | None = None,
    *,
    report=None,
    strict: bool = False,
):
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

        return write(recipes, path, profile=profile, report=report, strict=strict)
    if fmt == "beersmith-bsmx":
        from .formats.beersmith import write

        return write(recipes, path, profile=profile, report=report, strict=strict)
    if fmt == "beerjson":
        from .formats.beerjson import write

        return write(recipes, path, profile=profile, report=report, strict=strict)
    if fmt == "brewfather-json":
        from .formats.brewfather import write

        return write(recipes, path, profile=profile, report=report, strict=strict)
    if fmt == "beertools-btp":
        from .formats.beertools import write

        return write(recipes, path, profile=profile, report=report, strict=strict)
    if fmt == "promash-text":
        from .formats.promash import write

        return write(recipes, path, profile=profile, report=report, strict=strict)
    raise ValueError(f"Unsupported output format: {fmt}")


__all__ = [
    "ConversionReport",
    "Diagnostic",
    "Recipe",
    "ValidationError",
    "detect_format",
    "read_recipes",
    "validate_recipes",
    "write_recipes",
]

from .report import ConversionReport, Diagnostic, ValidationError, validate_recipes
