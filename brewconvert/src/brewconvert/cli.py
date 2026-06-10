from __future__ import annotations

import argparse
from pathlib import Path

from . import detect_format, read_recipes, write_recipes
from .report import ConversionReport


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
    recipes = read_recipes(args.input, format=src_fmt)
    write_recipes(recipes, args.output, format=args.to, profile=args.profile)
    report = ConversionReport(src_fmt, args.to, notes=[f"Wrote {args.output}"])
    if args.to == "beersmith-bsmx":
        report.warnings.append("BeerSmith BSMX writer is an MVP/draft writer; validate in BeerSmith before production use.")
    if args.to in {"beertools-btp", "promash-text"}:
        report.warnings.append("Legacy-format writer is pragmatic and should be validated in the target application before production use.")
    print(report.text())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brewconvert")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_p = sub.add_parser("inspect", help="Inspect a recipe file")
    inspect_p.add_argument("input", type=Path)
    inspect_p.set_defaults(func=_cmd_inspect)

    convert_p = sub.add_parser("convert", help="Convert recipe file")
    convert_p.add_argument("input", type=Path)
    convert_p.add_argument("output", type=Path)
    convert_p.add_argument("--to", required=True, choices=["beerxml", "beersmith-bsmx", "beerjson", "brewfather-json", "beertools-btp", "promash-text"])
    convert_p.add_argument("--profile", default=None)
    convert_p.set_defaults(func=_cmd_convert)

    args = parser.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
