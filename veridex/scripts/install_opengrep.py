"""Download a pinned official release into this project, never a global installation."""
import hashlib
import json
import platform
from pathlib import Path
import urllib.request

VERSION = "1.33.1"


def main():
    system, machine = platform.system(), platform.machine()
    names = {("Darwin", "arm64"): "opengrep_osx_arm64", ("Darwin", "x86_64"): "opengrep_osx_x86",
             ("Linux", "x86_64"): "opengrep_manylinux_x86", ("Linux", "aarch64"): "opengrep_manylinux_aarch64"}
    if (system, machine) not in names:
        raise SystemExit("Unsupported platform for this hackathon installer")
    asset = names[system, machine]
    target = Path(__file__).resolve().parents[1] / ".tools"
    target.mkdir(mode=0o700, exist_ok=True)
    url = f"https://github.com/opengrep/opengrep/releases/download/v{VERSION}/{asset}"
    binary = target / "opengrep"
    temp = target / "opengrep.download"
    print(f"Downloading official OpenGrep v{VERSION} release ({asset})")
    urllib.request.urlretrieve(url, temp)
    checksum = hashlib.sha256(temp.read_bytes()).hexdigest()
    # TLS authenticates this initial download; this records an installation pin, not a publisher signature.
    temp.chmod(0o700)
    temp.replace(binary)
    (target / "toolchain.json").write_text(json.dumps({"version": VERSION, "asset": asset, "sha256": checksum, "url": url}, indent=2))
    print("Installed and recorded local SHA-256 pin. Run python -m backend.cli scan.")


if __name__ == "__main__":
    main()
