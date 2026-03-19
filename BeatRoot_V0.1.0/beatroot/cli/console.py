from __future__ import annotations

import os
import sys
from datetime import datetime


class _Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    BLUE = "\033[38;5;63m"
    CYAN = "\033[38;5;45m"
    GREEN = "\033[38;5;83m"
    YELLOW = "\033[38;5;221m"
    RED = "\033[38;5;203m"
    GRAY = "\033[38;5;245m"


class Console:
    def __init__(self, interactive: bool = True):
        self.interactive = interactive
        self._use_color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")

    def _paint(self, text: str, color: str = "", bold: bool = False, dim: bool = False) -> str:
        if not self._use_color:
            return text
        prefix = ""
        if bold:
            prefix += _Ansi.BOLD
        if dim:
            prefix += _Ansi.DIM
        if color:
            prefix += color
        return f"{prefix}{text}{_Ansi.RESET}"

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def splash(self, target: str) -> None:
        logo = [
            " ▄▄▄▄▄▄                                  ▄▄▄▄▄▄                                 ",
            " ██▀▀▀▀██                        ██      ██▀▀▀▀██                        ██     ",
            " ██    ██   ▄████▄    ▄█████▄  ███████   ██    ██   ▄████▄    ▄████▄   ███████  ",
            " ███████   ██▄▄▄▄██   ▀ ▄▄▄██    ██      ███████   ██▀  ▀██  ██▀  ▀██    ██     ",
            " ██    ██  ██▀▀▀▀▀▀  ▄██▀▀▀██    ██      ██  ▀██▄  ██    ██  ██    ██    ██     ",
            " ██▄▄▄▄██  ▀██▄▄▄▄█  ██▄▄▄███    ██▄▄▄   ██    ██  ▀██▄▄██▀  ▀██▄▄██▀    ██▄▄▄  ",
            " ▀▀▀▀▀▀▀     ▀▀▀▀▀    ▀▀▀▀ ▀▀     ▀▀▀▀   ▀▀    ▀▀▀   ▀▀▀▀      ▀▀▀▀       ▀▀▀▀  ",                      
        ]
        print("")
        for line in logo:
            print(self._paint(line, _Ansi.BLUE, bold=True))
        print(self._paint("AI-Powered Security Assessment Assistant", _Ansi.GRAY))
        print(self._paint("v0.1.0", _Ansi.GRAY, dim=True))
        print("")
        self.topbar(target)
        print("")

    def topbar(self, target: str) -> None:
        left = self._paint("BeatRoot CTF Solver", _Ansi.BLUE, bold=True)
        version = self._paint("v0.1.0", _Ansi.GRAY)
        tgt = self._paint(f"Target: {target}", _Ansi.GRAY)
        print(f"[*] {left} {version} | {tgt}")

    def banner(self, message: str) -> None:
        print(f"\n{self._paint('==', _Ansi.GRAY, dim=True)} {self._paint(message, _Ansi.CYAN, bold=True)}")

    def section(self, title: str) -> None:
        print(f"\n{self._paint(f'[{title}]', _Ansi.CYAN, bold=True)}")

    def info(self, message: str) -> None:
        print(message)

    def warn(self, message: str) -> None:
        print(f"{self._paint('Warning:', _Ansi.YELLOW, bold=True)} {message}")

    def error(self, message: str) -> None:
        print(f"{self._paint('Error:', _Ansi.RED, bold=True)} {message}")

    def success(self, message: str) -> None:
        print(f"{self._paint('Success:', _Ansi.GREEN, bold=True)} {message}")

    def event(self, message: str, level: str = "info") -> None:
        palette = {
            "info": _Ansi.GRAY,
            "success": _Ansi.GREEN,
            "warn": _Ansi.YELLOW,
            "error": _Ansi.RED,
        }
        dot = self._paint("*", palette.get(level, _Ansi.GRAY), bold=True)
        timestamp = self._paint(self._ts(), _Ansi.GRAY, dim=True)
        print(f"{timestamp} {dot} {message}")

    def confirm(self, prompt: str, default: bool = False) -> bool:
        if not self.interactive:
            return default
        default_hint = "Y/n" if default else "y/N"
        raw = input(f"{prompt} [{default_hint}] ").strip().lower()
        if not raw:
            return default
        return raw in {"y", "yes"}
