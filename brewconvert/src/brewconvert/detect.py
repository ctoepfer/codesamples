from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET


def _local(tag: str) -> str:
    return tag.split('}', 1)[-1] if '}' in tag else tag


def _looks_like_promash(text: str) -> bool:
    lower = text.lower()
    return "promash" in lower or "recipe specifics" in lower or "grain/extract/sugar" in lower


def detect_format(path: str | Path) -> str:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in {".beerjson"}:
        return "beerjson"
    if suffix in {".btp", ".btt"}:
        return "beertools-btp"
    if suffix in {".txt", ".promash"}:
        sample = p.read_text(encoding="utf-8", errors="ignore")[:8192]
        if _looks_like_promash(sample):
            return "promash-text"
    if suffix in {".json", ".brewfather"}:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse JSON file: {p}") from exc
        obj = data.get("beerjson", data) if isinstance(data, dict) else data
        if isinstance(obj, dict) and ("version" in obj and "recipes" in obj or "ingredients" in obj and any(k in obj.get("ingredients", {}) for k in ("fermentable_additions", "hop_additions"))):
            return "beerjson"
        if isinstance(obj, dict) and any(k in obj for k in ("batchSize", "fermentables", "hops", "yeasts", "miscs")):
            return "brewfather-json"
        if isinstance(obj, list):
            return "brewfather-json"
        return "beerjson" if suffix == ".beerjson" else "brewfather-json"
    try:
        root = ET.parse(p).getroot()
    except ET.ParseError as exc:
        if suffix in {".txt", ".promash"}:
            return "promash-text"
        raise ValueError(f"Could not parse XML file: {p}") from exc
    local = _local(root.tag)
    if root.tag == "RECIPES" or local == "RECIPES":
        return "beerxml"
    if root.tag == "Selections" or local == "Selections":
        return "beersmith-bsmx"
    if local == "Recipe" and ("beertools" in root.tag.lower() or root.attrib.get("version")):
        return "beertools-btp"
    raise ValueError(f"Unsupported XML root tag: {root.tag}")
