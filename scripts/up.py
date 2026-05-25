"""docker compose up -d + saglik kontrolu."""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    print("[up] docker compose up -d")
    subprocess.run(["docker", "compose", "up", "-d"], cwd=str(ROOT), check=True, shell=True)
    print("[up] Konteynerlar acildi, SteVe acilisi icin bekliyorum (~30s)...")
    for i in range(30):
        time.sleep(2)
        r = subprocess.run(
            ["docker", "compose", "logs", "--tail", "5", "steve"],
            cwd=str(ROOT), capture_output=True, text=True, shell=True,
        )
        if "Started" in r.stdout or "Jetty started" in r.stdout or "8180" in r.stdout:
            print("[up] SteVe ayakta.")
            break
        print(f"[up] beklemek... ({i+1})")
    print("\n[up] WebApp:        http://localhost:8180/manager/home")
    print("[up] OCPP-J 1.6:    ws://localhost:8180/steve/websocket/CentralSystemService/<chargeBoxId>")
    print("[up] Login:         admin / 1234   (default)")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
