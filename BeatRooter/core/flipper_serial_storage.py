import errno
import os
import re
import tempfile
import termios
import time
from pathlib import Path


class FlipperSerialError(Exception):
    pass


class FlipperSerialBusyError(FlipperSerialError):
    pass


class FlipperSerialStorageMirror:
    """Create a local mirror of Flipper storage over serial CLI commands."""

    DEFAULT_BAUD = termios.B115200
    READ_TIMEOUT = 1.6
    QUIET_WINDOW = 0.25
    MAX_FILES = 1200
    MAX_NAME_LENGTH = 180
    MAX_LOCAL_PATH_LENGTH = 900

    REMOTE_SEED_DIRS = [
        "/ext/subghz",
        "/ext/badusb",
        "/ext/infrared",
        "/ext/nfc",
        "/ext/rfid",
        "/ext/ibutton",
        "/ext/u2f",
        "/ext/apps_data",
        "/int/infrared",
    ]

    TEXT_FILE_EXTENSIONS = {
        ".sub",
        ".ir",
        ".nfc",
        ".rfid",
        ".lf",
        ".ibtn",
        ".ibutton",
        ".txt",
        ".log",
        ".csv",
        ".json",
        ".badusb",
        ".duck",
        ".ducky",
        ".script",
        ".ps1",
        ".bat",
        ".cmd",
        ".sh",
    }

    def __init__(self, port_path: str):
        self.port_path = str(port_path)
        self.fd = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def open(self):
        try:
            self.fd = os.open(self.port_path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        except OSError as exc:
            if exc.errno in (errno.EBUSY, errno.EACCES, errno.EPERM):
                raise FlipperSerialBusyError(str(exc)) from exc
            raise FlipperSerialError(str(exc)) from exc

        attrs = termios.tcgetattr(self.fd)
        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[3] = 0
        attrs[4] = self.DEFAULT_BAUD
        attrs[5] = self.DEFAULT_BAUD
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = 1

        termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        termios.tcflush(self.fd, termios.TCIOFLUSH)

        # Wake device CLI.
        self._write_raw(b"\r\n")
        time.sleep(0.08)
        self._read_until_quiet(timeout=0.35)

    def close(self):
        if self.fd is None:
            return
        try:
            os.close(self.fd)
        except OSError:
            pass
        self.fd = None

    def create_local_mirror(self) -> str:
        local_root = Path(tempfile.mkdtemp(prefix="beatrooter_flipper_rpc_"))
        discovered_entries = 0

        queue = list(self.REMOTE_SEED_DIRS)
        seen_dirs = set()
        mirrored_files = 0

        while queue and mirrored_files < self.MAX_FILES:
            remote_dir = queue.pop(0)
            if remote_dir in seen_dirs:
                continue
            seen_dirs.add(remote_dir)

            entries = self.list_dir(remote_dir)
            if entries is None:
                continue

            discovered_entries += len(entries)
            for entry in entries:
                kind = entry["kind"]
                name = entry["name"]
                if not name or name in (".", ".."):
                    continue
                if len(name) > self.MAX_NAME_LENGTH:
                    continue

                remote_path = f"{remote_dir.rstrip('/')}/{name}".replace("//", "/")
                if kind == "dir":
                    queue.append(remote_path)
                    continue

                relative = remote_path.lstrip("/")
                local_path = local_root / relative
                if len(str(local_path)) > self.MAX_LOCAL_PATH_LENGTH:
                    continue
                local_path.parent.mkdir(parents=True, exist_ok=True)

                suffix = local_path.suffix.lower()
                if suffix in self.TEXT_FILE_EXTENSIONS:
                    payload = self.read_text_file(remote_path)
                    if payload is None:
                        continue
                    try:
                        local_path.write_text(payload, encoding="utf-8", errors="ignore")
                    except OSError:
                        continue
                else:
                    # Keep non-text artifacts as placeholders so they can still be represented.
                    placeholder = ""
                    if entry.get("size_text"):
                        placeholder = f"remote_size={entry['size_text']}\n"
                    try:
                        local_path.write_text(placeholder, encoding="utf-8", errors="ignore")
                    except OSError:
                        continue
                    if entry.get("size_bytes") and local_path.exists():
                        try:
                            os.truncate(local_path, entry["size_bytes"])
                        except OSError:
                            pass

                mirrored_files += 1
                if mirrored_files >= self.MAX_FILES:
                    break

        if discovered_entries == 0:
            raise FlipperSerialError("No remote entries discovered via serial storage commands")

        return str(local_root)

    def list_dir(self, remote_path: str):
        attempts = [
            f"storage list {remote_path}",
            f"storage list {remote_path} --plain",
            f"storage list {remote_path} -d",
        ]

        for command in attempts:
            output = self.send_command(command)
            if not output:
                continue
            parsed = self._parse_storage_list_output(output)
            if parsed is not None:
                return parsed
        return None

    def read_text_file(self, remote_path: str):
        attempts = [
            f"storage read {remote_path}",
            f"storage cat {remote_path}",
        ]

        for command in attempts:
            output = self.send_command(command)
            if not output:
                continue
            text = self._parse_storage_read_output(output, command)
            if text is not None:
                return text
        return None

    def send_command(self, command: str) -> str:
        self._write_raw((command + "\r\n").encode("utf-8"))
        payload = self._read_until_quiet(timeout=self.READ_TIMEOUT)
        return payload.decode("utf-8", errors="ignore") if payload else ""

    def _write_raw(self, payload: bytes):
        if self.fd is None:
            raise FlipperSerialError("Serial port not opened")
        os.write(self.fd, payload)

    def _read_until_quiet(self, timeout: float) -> bytes:
        if self.fd is None:
            return b""

        output = b""
        start = time.time()
        last_data = time.time()

        while time.time() - start < timeout:
            try:
                chunk = os.read(self.fd, 4096)
            except BlockingIOError:
                chunk = b""

            if chunk:
                output += chunk
                last_data = time.time()
                continue

            if output and (time.time() - last_data) >= self.QUIET_WINDOW:
                break
            time.sleep(0.03)

        return output

    def _parse_storage_list_output(self, output: str):
        cleaned = self._sanitize_output(output)
        if not cleaned:
            return None

        lowered = cleaned.lower()
        if "not found" in lowered or "error" in lowered or "fail" in lowered:
            return []

        entries = []
        for line in cleaned.splitlines():
            line = line.strip()
            if not line:
                continue

            if line.startswith("storage ") or line.startswith(">"):
                continue

            # Format examples:
            # [D] folder
            # [F] file.txt
            # [S] folder
            # D folder
            # F file.txt
            matched = re.match(r"^\[?([DFSdfs])\]?\s+(.+)$", line)
            if matched:
                kind = "dir" if matched.group(1).upper() in {"D", "S"} else "file"
                entry = self._parse_list_entry_payload(matched.group(2).strip(), kind)
                if entry:
                    entries.append(entry)
                continue

            # Generic folder suffix style.
            if line.endswith("/"):
                entries.append(
                    {
                        "kind": "dir",
                        "name": self._clean_remote_name(line[:-1]),
                        "size_text": "",
                        "size_bytes": 0,
                    }
                )
                continue

            # Fallback as file name line.
            entry = self._parse_list_entry_payload(line, "file")
            if entry:
                entries.append(entry)

        return entries

    def _parse_storage_read_output(self, output: str, command: str):
        cleaned = self._sanitize_output(output)
        if not cleaned:
            return ""

        lines = []
        for line in cleaned.splitlines():
            stripped = line.strip()
            if not stripped:
                lines.append("")
                continue
            if stripped == command:
                continue
            if stripped.startswith("storage "):
                continue
            if stripped.startswith(">"):
                continue
            if "not found" in stripped.lower() or stripped.lower().startswith("error"):
                return None
            lines.append(line)

        return "\n".join(lines).strip("\n")

    def _sanitize_output(self, output: str) -> str:
        text = output.replace("\r", "\n")
        text = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", text)
        text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", "", text)
        text = re.sub(r"\n+", "\n", text)
        return text.strip()

    def _clean_remote_name(self, name: str) -> str:
        value = name.strip().strip('"').strip("'")
        value = value.replace("\\", "/")
        return value

    def _parse_list_entry_payload(self, payload: str, default_kind: str) -> dict:
        value = payload.strip()
        if not value:
            return {}
        if self._looks_like_non_filename_payload(value):
            return {}

        # qFlipper/CLI style often appends a size token: "Port_casa.sub 163b"
        size_match = re.match(r"^(.*?)(?:\s+(\d+(?:\.\d+)?\s*[bkmg]?b))?$", value, flags=re.IGNORECASE)
        name_part = value
        size_text = ""
        size_bytes = 0
        if size_match:
            candidate_name = (size_match.group(1) or "").strip()
            candidate_size = (size_match.group(2) or "").strip()
            if candidate_name:
                name_part = candidate_name
            if candidate_size:
                size_text = candidate_size
                size_bytes = self._parse_size_to_bytes(candidate_size)

        kind = default_kind
        if name_part.endswith("/"):
            kind = "dir"
            name_part = name_part[:-1]
        if len(name_part) > self.MAX_NAME_LENGTH:
            return {}

        return {
            "kind": kind,
            "name": self._clean_remote_name(name_part),
            "size_text": size_text,
            "size_bytes": size_bytes,
        }

    def _looks_like_non_filename_payload(self, value: str) -> bool:
        # Guard against command output leaks being parsed as file names (e.g. "RAW_Data: 400 -400 ...").
        if len(value) > 260:
            return True
        lowered = value.lower()
        if lowered.startswith("raw_data:") or lowered.startswith("raw data:"):
            return True
        if ":" in value and re.search(r":\s*-?\d+\s+-?\d+", value):
            return True
        if value.count(" ") > 28 and re.search(r"-?\d+\s+-?\d+", value):
            return True
        return False

    def _parse_size_to_bytes(self, size_text: str) -> int:
        match = re.match(r"^(\d+(?:\.\d+)?)\s*([bkmg]?b)$", size_text.strip(), flags=re.IGNORECASE)
        if not match:
            return 0

        value = float(match.group(1))
        unit = match.group(2).lower()
        multiplier = {
            "b": 1,
            "kb": 1024,
            "mb": 1024 * 1024,
            "gb": 1024 * 1024 * 1024,
        }.get(unit, 1)
        return int(value * multiplier)
