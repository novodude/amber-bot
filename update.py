#!/usr/bin/env python3
"""
update.py — Pull the latest Amber updates from GitHub.
Run this any time to update. Then run main.py (or amber.py) to start.
"""

import subprocess
import sys
from pathlib import Path

VENV_PIP = Path(".venv") / ("Scripts/pip.exe" if sys.platform == "win32" else "bin/pip")


def run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip() + result.stderr.strip()


def main():
    print("""
    ╔══════════════════════════════════╗
    ║       Amber Bot — Updater        ║
    ╚══════════════════════════════════╝
    """)

    # ── Check git is available ────────────────────────────────────────────────
    code, _ = run(["git", "--version"])
    if code != 0:
        print("  ❌ Git not found. Install git and try again.")
        sys.exit(1)

    if not Path(".git").exists():
        print("  ❌ This doesn't look like a git repository.")
        print("  Run amber.py for a fresh setup instead.")
        sys.exit(1)

    # ── Check remote for changes ──────────────────────────────────────────────
    print("  Fetching latest changes from GitHub...")
    run(["git", "fetch"])

    code, log = run(["git", "log", "HEAD..origin/main", "--oneline"])
    if not log:
        print("  ✅ Already up to date! No changes to pull.")
        print("\n  Run main.py to start the bot:")
        print("    .venv/bin/python main.py   (Linux/Mac)")
        print("    .venv\\Scripts\\python main.py  (Windows)")
        return

    # ── Show what's new ───────────────────────────────────────────────────────
    print(f"\n  📦 New updates available:\n")
    for line in log.splitlines():
        print(f"    • {line}")

    # ── Pull ──────────────────────────────────────────────────────────────────
    print("\n  Pulling updates...")
    code, out = run(["git", "pull", "--ff-only"])
    if code != 0:
        print(f"  ❌ Pull failed:\n{out}")
        print("\n  You may have local changes conflicting. Resolve them manually.")
        sys.exit(1)

    print("  ✅ Updated successfully!")

    # ── Update dependencies if requirements changed ───────────────────────────
    code, changed_files = run(["git", "diff", "HEAD@{1}", "HEAD", "--name-only"])
    if "requirements.txt" in changed_files:
        print("\n  requirements.txt changed — updating dependencies...")
        if VENV_PIP.exists():
            subprocess.run([str(VENV_PIP), "install", "-r", "requirements.txt", "--quiet"])
            print("  ✅ Dependencies updated.")
        else:
            print("  ⚠️  Virtual environment not found. Run amber.py to set it up.")

    # ── Done ──────────────────────────────────────────────────────────────────
    print("\n  ✅ All done! Start the bot with:")
    print("    .venv/bin/python main.py   (Linux/Mac)")
    print("    .venv\\Scripts\\python main.py  (Windows)")
    print("\n  Or just run:  python amber.py")


if __name__ == "__main__":
    main()
