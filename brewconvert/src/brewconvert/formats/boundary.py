"""Common adapter validation, profiles, and transactional serialization."""

from __future__ import annotations

import warnings
from functools import wraps
from pathlib import Path
from tempfile import TemporaryDirectory

from brewconvert.report import (
    ConversionReport,
    additions,
    compare_recipes,
    quantity_of,
    validate_recipes,
)

PROFILES = {
    "beerxml": {None, "standard", "grainfather"},
    "beersmith-bsmx": {None, "beersmith-bsmx"},
    "beerjson": {None, "standard"},
    "brewfather-json": {None, "export"},
    "beertools-btp": {None},
    "promash-text": {None},
}


def _publish(report, supplied):
    if not supplied and report.warnings:
        warnings.warn(report.text(), UserWarning, stacklevel=3)


def reader(fmt):
    def decorate(fn):
        @wraps(fn)
        def read(path, *, report=None, strict=False):
            supplied = report is not None
            report = report if supplied else ConversionReport(fmt, "model")
            recipes = fn(path)
            validate_recipes(recipes, report)
            if strict:
                report.check()
            _publish(report, supplied)
            return recipes

        return read

    return decorate


def writer(fmt):
    def decorate(fn):
        @wraps(fn)
        def write(recipes, path, profile=None, *, report=None, strict=False):
            if profile not in PROFILES[fmt]:
                raise ValueError(
                    f"Unsupported profile {profile!r} for {fmt}; supported: {PROFILES[fmt]}"
                )
            supplied = report is not None
            report = report if supplied else ConversionReport("model", fmt)
            report.target_format = fmt
            validate_recipes(recipes, report)
            if fmt in {"beersmith-bsmx", "beertools-btp", "promash-text"}:
                report.add(
                    "provisional-writer",
                    "<collection>",
                    None,
                    None,
                    None,
                    fmt,
                    "Draft/pragmatic writer; validate in the target application before production use.",
                )
            for r in recipes:
                for item in additions(r):
                    q = quantity_of(item)
                    if q and q.kind == "count" and fmt == "beerxml":
                        report.add(
                            "count-unsupported",
                            r.name,
                            item.name,
                            q.display(),
                            q.display(),
                            "AMOUNT omitted",
                            "BeerXML cannot represent counts; mass/volume is not invented.",
                            True,
                        )
                    if fmt == "beerxml":
                        phase = getattr(item, "use", None)
                        allowed = (
                            {"boil", "mash", "primary", "secondary", "bottling"}
                            if item in r.miscs
                            else {"boil", "dry hop", "mash", "first wort", "aroma"}
                        )
                        if phase and (
                            item in r.yeasts
                            or item in r.fermentables
                            or phase.lower() not in allowed
                        ):
                            report.add(
                                "native-phase-unsupported",
                                r.name,
                                item.name,
                                phase,
                                phase,
                                phase
                                if profile == "grainfather"
                                and (item in r.miscs or item in r.hops)
                                else None,
                                "Phase is outside the BeerXML enum or ingredient timing fields; a target application may reject or ignore it.",
                                True,
                            )
                    if fmt == "beersmith-bsmx":
                        native = (
                            item in r.fermentables
                            or item in r.hops
                            or (item in r.miscs and q and q.kind == "mass")
                            or (
                                item in r.yeasts
                                and q
                                and q.kind == "volume"
                                and (item.form or "").lower() == "liquid"
                            )
                        )
                        if q and not native:
                            report.add(
                                "native-quantity-unsupported",
                                r.name,
                                item.name,
                                q.display(),
                                q.display(),
                                "BC_QUANTITY extension only",
                                "No verified native BSMX quantity mapping; BeerSmith may ignore the extension.",
                                True,
                            )
                        phase = getattr(item, "use", None)
                        native_phases = (
                            {"mash", "sparge", "boil"}
                            if item in r.miscs
                            else {"boil"}
                            if item in r.hops
                            else set()
                        )
                        if phase and phase.lower() not in native_phases:
                            report.add(
                                "native-phase-unsupported",
                                r.name,
                                item.name,
                                phase,
                                phase,
                                "BC_PHASE extension only",
                                "Native BSMX phase mapping unverified; BeerSmith may ignore this phase.",
                                True,
                            )
                if fmt == "beersmith-bsmx":
                    report.add(
                        "bsmx-extensions",
                        r.name,
                        None,
                        None,
                        None,
                        "BC_*",
                        "Final gravity, exact quantities and phases use brewconvert extensions; these do not establish BeerSmith compatibility.",
                    )
                if r.source_metadata.get("document"):
                    report.add(
                        "source-document",
                        r.name,
                        None,
                        "original document in source_metadata[document]",
                        "normalized fields",
                        fmt,
                        "Full source document is retained in memory only; unmodeled nested fields and application metadata are not copied.",
                    )
                if r.unknown_fields:
                    report.add(
                        "unsupported-source",
                        r.name,
                        None,
                        list(r.unknown_fields),
                        "source evidence",
                        fmt,
                        "Unmodeled source fields are retained in memory but are not emitted to this target.",
                    )
                for item in (
                    r.fermentables
                    + r.hops
                    + r.miscs
                    + r.yeasts
                    + r.mash_steps
                    + ([r.style] if r.style else [])
                ):
                    if item.source:
                        report.add(
                            "source-evidence",
                            r.name,
                            item.name,
                            list(item.source),
                            "normalized fields only",
                            fmt,
                            "Raw source fields are not copied verbatim; application-specific fields outside the normalized model are lost.",
                        )
                if r.measured_values:
                    report.add(
                        "measured-values",
                        r.name,
                        None,
                        r.measured_values,
                        "measured (not estimated)",
                        fmt,
                        "Measured source values are retained in memory; this target writer does not emit them.",
                    )
            if strict:
                report.check()
            # Read-back validation occurs before replacing even an existing destination.
            from brewconvert import read_recipes

            with TemporaryDirectory(prefix="brewconvert-") as directory:
                staged = Path(directory) / Path(path).name
                fn(recipes, staged, profile=profile)
                check = ConversionReport(fmt, fmt)
                after = read_recipes(staged, format=fmt, report=check)
                compare_recipes(recipes, after, report)
                if strict:
                    report.check()
                Path(path).write_bytes(staged.read_bytes())
            _publish(report, supplied)
            return report

        return write

    return decorate
