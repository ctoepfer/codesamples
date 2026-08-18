from __future__ import annotations

import argparse

from .core.app import Application


def _cmd_devices(args: argparse.Namespace) -> int:
    app = Application()
    app.devices.discover()
    for plugin in app.devices.all():
        info = plugin.info
        status = "ready" if info.implemented else "not yet implemented"
        print(f"{info.device_id:<16} {info.display_name:<28} {info.transport.value:<10} risk={info.risk.value:<9} [{status}]")
        if args.verbose:
            print(f"                 docs: {info.docs_reference}")
            if info.notes:
                print(f"                 notes: {info.notes}")
    return 0


def _cmd_gui(args: argparse.Namespace) -> int:
    try:
        from .gui.app import main as gui_main
    except ImportError as exc:
        raise SystemExit(
            "The GUI requires the 'gui' extra. Install with: pip install -e '.[gui]'"
        ) from exc
    gui_main()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brewpanel")
    sub = parser.add_subparsers(dest="command", required=True)

    devices_p = sub.add_parser("devices", help="List the discovered device catalog")
    devices_p.add_argument("-v", "--verbose", action="store_true")
    devices_p.set_defaults(func=_cmd_devices)

    gui_p = sub.add_parser("gui", help="Launch the NiceGUI dashboard (requires the 'gui' extra)")
    gui_p.set_defaults(func=_cmd_gui)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
