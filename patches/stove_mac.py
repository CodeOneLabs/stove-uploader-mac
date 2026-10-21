"""Unpack STOVE's Windows PyInstaller executables into runnable macOS runner folders.

Used by setup.sh for the CLI and by sitecustomize.py, on first run, for the Updater and
the Core that the CLI downloads itself. A runner is re-extracted when its .exe changes
(the Updater replaces the Core when STOVE ships a new version).

    python3.11 stove_mac.py extract <exe> <runner-dir>   -> prints "<entry.pyc> <version>"
"""
import os
import shutil
import struct
import subprocess
import sys

APP_PACKAGES = ("karina_", "pymegastove")
STAMP = ".runner"
_HERE = os.path.dirname(os.path.abspath(__file__))


def pe_version(exe):
    """FileVersion from the exe's VS_FIXEDFILEINFO resource (what the frozen app reads on Windows)."""
    with open(exe, "rb") as f:
        head = f.read(16 << 20)
    i = head.find(struct.pack("<I", 0xFEEF04BD))
    if i < 0:
        return "1.0.0.0"
    ms, ls = struct.unpack_from("<II", head, i + 8)
    return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"


def _key(exe):
    st = os.stat(exe)
    return f"{st.st_size}:{int(st.st_mtime)}"


def read_stamp(runner):
    try:
        with open(os.path.join(runner, STAMP)) as f:
            key, entry, version = f.read().split()
        return key, entry, version
    except (OSError, ValueError):
        return None


def extract(exe, runner):
    """Extract exe into runner unless it is already current. Returns (entry, version)."""
    exe, runner = os.path.abspath(exe), os.path.abspath(runner)
    stamp = read_stamp(runner)
    if stamp and stamp[0] == _key(exe):
        return stamp[1], stamp[2]

    tmp = runner + ".extract"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    tool = os.path.join(os.environ.get("STOVE_MAC_ROOT", os.path.dirname(_HERE)), ".cache", "pyinstxtractor.py")
    out = subprocess.run([sys.executable, "-I", tool, exe], cwd=tmp, capture_output=True, text=True, check=True).stdout
    entries = [l.split(":", 1)[1].strip() for l in out.splitlines() if l.startswith("[+] Possible entry point:")]
    entry = next((e for e in entries if not e.startswith("pyi")), None)
    if entry is None:
        raise RuntimeError(f"Could not unpack {exe}:\n{out}")
    x = os.path.join(tmp, os.path.basename(exe) + "_extracted")
    pyz = os.path.join(x, "PYZ-00.pyz_extracted")

    # Keep any runtime data (Updater/Core installs, logs) that lives inside the runner folder.
    os.makedirs(runner, exist_ok=True)
    packages = [n for n in os.listdir(pyz) if n.startswith(APP_PACKAGES) and os.path.isdir(os.path.join(pyz, n))]
    for name in packages:
        dst = os.path.join(runner, name)
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(os.path.join(pyz, name), dst)
        # pyinstxtractor writes a package's __init__ as <pkg>.pyc beside <pkg>/; move each one inside.
        for base, dirs, _ in os.walk(dst):
            for d in dirs:
                init, flat = os.path.join(base, d, "__init__.pyc"), os.path.join(base, d + ".pyc")
                if os.path.isfile(flat) and not os.path.exists(init):
                    os.replace(flat, init)
        if os.path.isfile(os.path.join(pyz, name + ".pyc")):
            shutil.copy2(os.path.join(pyz, name + ".pyc"), os.path.join(dst, "__init__.pyc"))
    shutil.copy2(os.path.join(x, entry), os.path.join(runner, entry))

    version = pe_version(exe)
    with open(os.path.join(runner, STAMP), "w") as f:
        f.write(f"{_key(exe)} {entry} {version}\n")
    shutil.rmtree(tmp, ignore_errors=True)
    return entry, version


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] != "extract":
        sys.exit(__doc__)
    print(*extract(sys.argv[2], sys.argv[3]))
