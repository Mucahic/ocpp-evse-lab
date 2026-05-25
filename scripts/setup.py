"""
Lab kurulum scripti.

Sirayla:
1. external/steve klasoru yoksa SteVe (steve-community/steve) git clone eder.
2. docker compose build cagirir (MySQL pull + SteVe imajini build eder).

Kullanim:
    python scripts/setup.py
"""
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEVE_DIR = ROOT / "external" / "steve"
STEVE_REPO = "https://github.com/steve-community/steve.git"
STEVE_TAG = "steve-3.7.1"  # son stabil release


def run(cmd, cwd=None, check=True):
    if isinstance(cmd, str):
        printable = cmd
        args = shlex.split(cmd) if os.name != "nt" else cmd
        shell = os.name == "nt"
    else:
        printable = " ".join(cmd)
        args = cmd
        shell = False
    print(f"[setup] $ {printable}")
    return subprocess.run(args, cwd=cwd, check=check, shell=shell)


def clone_steve():
    if STEVE_DIR.exists():
        print(f"[setup] {STEVE_DIR} zaten var, clone atlandi.")
        return
    STEVE_DIR.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "--depth", "1", "--branch", STEVE_TAG, STEVE_REPO, str(STEVE_DIR)])


def docker_build():
    run(["docker", "compose", "build"], cwd=str(ROOT))


def main():
    print("[setup] OCPP EVSE Lab kurulumu basliyor.")
    clone_steve()
    docker_build()
    print("[setup] Tamam. Simdi: python scripts/up.py")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"[setup] HATA: komut basarisiz oldu (exit={e.returncode}).", file=sys.stderr)
        sys.exit(e.returncode)
