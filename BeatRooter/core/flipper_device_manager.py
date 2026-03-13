import platform
from pathlib import Path


class FlipperDeviceManager:
    """Detect mounted Flipper filesystems across common desktop platforms."""

    FLIPPER_NAME_HINTS = ("flipper", "flipper sd", "flipperzero", "flipper_zero")
    MARKER_DIRS = ("subghz", "badusb", "infrared", "nfc", "rfid", "ibutton")
    SERIAL_PORT_HINTS = ("ttyacm", "ttyusb", "flipper")

    @classmethod
    def find_connected_flipper_roots(cls) -> list:
        candidates = []
        system_name = platform.system().lower()

        if system_name == "linux":
            candidates.extend(cls._linux_mount_candidates())
        elif system_name == "darwin":
            candidates.extend(cls._darwin_mount_candidates())
        elif system_name == "windows":
            candidates.extend(cls._windows_mount_candidates())

        # Fallback scan in common user mount locations for every platform.
        candidates.extend(cls._common_mount_candidates())

        unique = {}
        for candidate in candidates:
            path = Path(candidate).expanduser()
            if not path.exists() or not path.is_dir():
                continue
            resolved = str(path.resolve())
            score = cls._score_candidate(path)
            if score <= 0:
                continue
            unique[resolved] = max(unique.get(resolved, 0), score)

        sorted_roots = sorted(unique.keys(), key=lambda item: unique[item], reverse=True)
        return sorted_roots

    @classmethod
    def find_connected_flipper_ports(cls) -> list:
        system_name = platform.system().lower()
        ports = []

        if system_name == "linux":
            ports.extend(cls._linux_serial_candidates())
        elif system_name == "darwin":
            ports.extend(cls._darwin_serial_candidates())
        elif system_name == "windows":
            ports.extend(cls._windows_serial_candidates())

        dedup = []
        seen = set()
        for port in ports:
            normalized = str(port).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            dedup.append(normalized)
        return dedup

    @classmethod
    def _linux_mount_candidates(cls) -> list:
        candidates = []
        mounts_file = Path("/proc/mounts")
        if not mounts_file.exists():
            return candidates

        try:
            with open(mounts_file, "r", encoding="utf-8", errors="ignore") as stream:
                for line in stream:
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    device = parts[0].lower()
                    mount_point = parts[1].replace("\\040", " ")
                    lower_mount = mount_point.lower()

                    if cls._contains_hint(lower_mount) or cls._contains_hint(device):
                        candidates.append(mount_point)
                        continue

                    if lower_mount.startswith("/media/") or lower_mount.startswith("/run/media/"):
                        candidates.append(mount_point)
        except OSError:
            return candidates

        return candidates

    @classmethod
    def _darwin_mount_candidates(cls) -> list:
        candidates = []
        volumes = Path("/Volumes")
        if not volumes.exists():
            return candidates

        for entry in volumes.iterdir():
            if not entry.is_dir():
                continue
            if cls._contains_hint(entry.name.lower()):
                candidates.append(str(entry))
            else:
                candidates.append(str(entry))
        return candidates

    @classmethod
    def _windows_mount_candidates(cls) -> list:
        # Windows detection without external packages: probe common drive letters.
        candidates = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = Path(f"{letter}:/")
            if not drive.exists():
                continue
            drive_name = str(drive).lower()
            if cls._contains_hint(drive_name):
                candidates.append(str(drive))
            else:
                candidates.append(str(drive))
        return candidates

    @classmethod
    def _common_mount_candidates(cls) -> list:
        candidates = []
        home = Path.home()
        common_roots = [
            home / "media",
            Path("/media") / home.name,
            Path("/run/media") / home.name,
            Path("/mnt"),
        ]

        for root in common_roots:
            if not root.exists() or not root.is_dir():
                continue
            for entry in root.iterdir():
                if entry.is_dir():
                    candidates.append(str(entry))

        return candidates

    @classmethod
    def _linux_serial_candidates(cls) -> list:
        candidates = []
        weak_candidates = []

        # Strongest signal: by-id symlinks usually include vendor/product names.
        by_id_dir = Path("/dev/serial/by-id")
        if by_id_dir.exists() and by_id_dir.is_dir():
            for entry in by_id_dir.iterdir():
                entry_name = entry.name.lower()
                if "flipper" not in entry_name:
                    continue
                try:
                    resolved = str(entry.resolve())
                except OSError:
                    resolved = str(entry)
                candidates.append(resolved)

        # Fallback: common USB serial device names.
        for pattern in ("/dev/ttyACM*", "/dev/ttyUSB*"):
            for path in Path("/dev").glob(Path(pattern).name):
                try:
                    if path.exists():
                        if cls._linux_port_matches_flipper(path):
                            candidates.append(str(path))
                        elif "ttyacm" in path.name.lower():
                            weak_candidates.append(str(path))
                except OSError:
                    continue

        if not candidates:
            # Last resort: expose ACM ports so user can still proceed with manual mount path.
            candidates.extend(weak_candidates[:3])

        return candidates

    @classmethod
    def _darwin_serial_candidates(cls) -> list:
        candidates = []
        for pattern in ("/dev/cu.usbmodem*", "/dev/tty.usbmodem*", "/dev/cu.usbserial*", "/dev/tty.usbserial*"):
            for path in Path("/dev").glob(Path(pattern).name):
                if path.exists():
                    candidates.append(str(path))
        return candidates

    @classmethod
    def _windows_serial_candidates(cls) -> list:
        # Without pyserial/registry parsing we cannot resolve friendly names reliably.
        # Return empty and rely on mounted-storage/manual selection path.
        return []

    @classmethod
    def _linux_port_matches_flipper(cls, port_path: Path) -> bool:
        tty_name = port_path.name
        sys_tty_path = Path("/sys/class/tty") / tty_name
        if not sys_tty_path.exists():
            return False

        metadata_paths = [
            sys_tty_path / "device" / "manufacturer",
            sys_tty_path / "device" / "product",
            sys_tty_path / "device" / "interface",
            sys_tty_path / "device" / "modalias",
            sys_tty_path / "device" / ".." / "manufacturer",
            sys_tty_path / "device" / ".." / "product",
        ]
        for metadata_path in metadata_paths:
            try:
                if metadata_path.exists():
                    value = metadata_path.read_text(encoding="utf-8", errors="ignore").strip().lower()
                    if "flipper" in value:
                        return True
            except OSError:
                continue

        return False

    @classmethod
    def _score_candidate(cls, root: Path) -> int:
        score = 0
        lowered = str(root).lower()
        has_name_hint = cls._contains_hint(lowered)

        if has_name_hint:
            score += 4

        marker_hits = 0
        for marker in cls.MARKER_DIRS:
            if (root / marker).exists() and (root / marker).is_dir():
                marker_hits += 1

        if not has_name_hint and marker_hits == 0:
            return 0

        score += marker_hits * 3

        # Basic filesystem presence indicates mount even without marker dirs.
        try:
            _ = next(root.iterdir(), None)
            score += 1
        except OSError:
            return 0

        return score

    @classmethod
    def _contains_hint(cls, value: str) -> bool:
        lowered = (value or "").lower()
        return any(hint in lowered for hint in cls.FLIPPER_NAME_HINTS)
