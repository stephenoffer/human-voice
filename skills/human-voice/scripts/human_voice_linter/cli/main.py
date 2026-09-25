"""main — the command-line entry point."""
from __future__ import annotations

from .commands import command_for
from .parser import build_parser
from .settings import resolve_config


def main(argv=None):
    args = build_parser().parse_args(argv)
    settings = resolve_config(args)
    return command_for(args, settings).run()


__all__ = ["main"]
