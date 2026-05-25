"""docker compose down (volume'lar korunur)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    print("[down] docker compose down")
    subprocess.run(["docker", "compose", "down"], cwd=str(ROOT), check=True, shell=True)
    print("[down] Konteynerlar durduruldu. Volume'lar korundu (mysql verisi durur).")
    print("[down] Tamamen silmek icin: docker compose down -v")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
