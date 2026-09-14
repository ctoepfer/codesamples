from __future__ import annotations

import argparse
from pathlib import Path

from . import detect_format, read_recipes, write_recipes
from .report import ConversionReport, ValidationError


def _cmd_inspect(args: argparse.Namespace) -> int:
    fmt = detect_format(args.input)
    recipes = read_recipes(args.input, format=fmt)
    print(f"Format: {fmt}")
    print(f"Recipes: {len(recipes)}")
    for idx, recipe in enumerate(recipes, start=1):
        print(f"\n[{idx}] {recipe.summary()}")
        print(f"  Fermentables: {len(recipe.fermentables)}")
        print(f"  Hops:         {len(recipe.hops)}")
        print(f"  Yeasts:       {len(recipe.yeasts)}")
        print(f"  Miscs:        {len(recipe.miscs)}")
        print(f"  Mash steps:   {len(recipe.mash_steps)}")
    return 0


def _cmd_convert(args: argparse.Namespace) -> int:
    src_fmt = detect_format(args.input)
    report = ConversionReport(src_fmt, args.to)
    try:
        recipes = read_recipes(args.input, format=src_fmt, report=report)
        write_recipes(
            recipes,
            args.output,
            format=args.to,
            profile=args.profile,
            report=report,
            strict=args.strict,
        )
    except ValidationError:
        print(report.text())
        return 2
    report.notes.append(f"Wrote {args.output}")
    # Warnings are always visible; --report also requests clean conversion details.
    if args.report or report.warnings:
        print(report.text())
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    report = ConversionReport(detect_format(args.input), "validation")
    read_recipes(args.input, report=report)
    print(report.text())
    return 2 if args.strict and report.errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brewconvert")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_p = sub.add_parser("inspect", help="Inspect a recipe file")
    inspect_p.add_argument("input", type=Path)
    inspect_p.set_defaults(func=_cmd_inspect)

    convert_p = sub.add_parser("convert", help="Convert recipe file")
    convert_p.add_argument("input", type=Path)
    convert_p.add_argument("output", type=Path)
    convert_p.add_argument(
        "--to",
        required=True,
        choices=[
            "beerxml",
            "beersmith-bsmx",
            "beerjson",
            "brewfather-json",
            "beertools-btp",
            "promash-text",
        ],
    )
    convert_p.add_argument("--profile", default=None)
    convert_p.add_argument("--report", action="store_true")
    convert_p.add_argument("--strict", action="store_true")
    convert_p.set_defaults(func=_cmd_convert)

    validate_p = sub.add_parser(
        "validate", help="Validate recipe quantities and semantics"
    )
    validate_p.add_argument("input", type=Path)
    validate_p.add_argument("--strict", action="store_true")
    validate_p.set_defaults(func=_cmd_validate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
