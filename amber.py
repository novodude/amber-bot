#!/usr/bin/env python3
"""
amber.py — Amber bot setup & launcher
Run this once to set everything up, then use it to start the bot.
Run update.py any time to pull the latest changes.

The domesticated-LLM is optional. If skipped or unavailable, the bot
uses the built-in synthesis engine for cat messages instead.
"""

import os
import sys
import subprocess
import platform
import json
from pathlib import Path

REPO_URL     = "https://github.com/novodude/amber-bot.git"
HF_MODEL_ID  = "Novodude/domesticated-LLM"   # HuggingFace repo
MODEL_DIR    = Path("domesticated-LLM")
VENV_DIR     = Path(".venv")
ENV_FILE     = Path(".env")
REQ_FILE     = Path("requirements.txt")

IS_WINDOWS   = platform.system() == "Windows"
PYTHON       = sys.executable
VENV_PYTHON  = str(VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python"))
VENV_PIP     = str(VENV_DIR / ("Scripts/pip.exe"    if IS_WINDOWS else "bin/pip"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def banner(text: str):
    print(f"\n{'─'*50}\n  {text}\n{'─'*50}")

def run(cmd: list[str], **kwargs) -> int:
    print(f"  › {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    return result.returncode

def ask(prompt: str, default: str = "") -> str:
    value = input(f"  {prompt} [{default}]: ").strip()
    return value if value else default

def yesno(prompt: str, default_yes: bool = False) -> bool:
    hint = "[Y/n]" if default_yes else "[y/N]"
    answer = input(f"  {prompt} {hint}: ").strip().lower()
    if not answer:
        return default_yes
    return answer in ("y", "yes")


# ── Steps ─────────────────────────────────────────────────────────────────────

def step_check_git():
    banner("1/7 — Checking for updates")
    if Path(".git").exists():
        code = run(["git", "pull", "--ff-only"])
        if code != 0:
            print("  ⚠️  Git pull failed — continuing with current files.")
    else:
        print("  Cloning repository...")
        run(["git", "clone", REPO_URL, "."])


def step_venv():
    banner("2/7 — Setting up virtual environment")
    if not VENV_DIR.exists():
        run([PYTHON, "-m", "venv", str(VENV_DIR)])
        print("  ✅ Virtual environment created.")
    else:
        print("  ✅ Virtual environment already exists.")


def step_install():
    banner("3/7 — Installing dependencies")
    if not REQ_FILE.exists():
        print("  ⚠️  requirements.txt not found — skipping.")
        return
    code = run([VENV_PIP, "install", "-r", str(REQ_FILE), "--quiet"])
    if code != 0:
        print("  ❌ pip install failed. Check your internet connection.")
        sys.exit(1)
    print("  ✅ Dependencies installed.")


def step_model():
    banner("4/7 — domesticated-LLM (optional)")

    # Already downloaded — nothing to decide
    if MODEL_DIR.exists() and any(MODEL_DIR.iterdir()):
        print(f"  ✅ Model already present at {MODEL_DIR}/")
        print("  ℹ️  Cat messages will use the LLM.")
        return

    print("  The domesticated-LLM generates AI cat messages.")
    print("  Without it, Amber uses the built-in synthesis engine instead —")
    print("  cat messages will still work, just without the neural flair.\n")
    print("  Requirements: ~500 MB disk, torch + transformers, decent CPU/GPU.")

    if not yesno("Download the model now?", default_yes=False):
        print("  ⏭️  Skipping model download — synthesis engine will be used.")
        print("  ℹ️  You can download it later by re-running amber.py.")
        return

    print(f"\n  Downloading from HuggingFace: {HF_MODEL_ID}")
    print("  Installing torch + transformers...")
    run([VENV_PIP, "install", "torch", "transformers", "accelerate", "--quiet"])

    print("  Downloading model weights (this may take a minute)...")
    script = f"""
from transformers import AutoTokenizer, AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained("{HF_MODEL_ID}")
tokenizer = AutoTokenizer.from_pretrained("{HF_MODEL_ID}")
model.save_pretrained("domesticated-LLM")
tokenizer.save_pretrained("domesticated-LLM")
print("Model saved to domesticated-LLM/")
"""
    code = run([VENV_PYTHON, "-c", script])
    if code != 0:
        print("  ❌ Download failed — Amber will fall back to the synthesis engine.")
        print("  ℹ️  Check your connection and try again by re-running amber.py.")
        # Don't exit — bot still works without the model
    else:
        print("  ✅ Model ready. Cat messages will use the LLM.")


def step_check_files():
    banner("5/7 — Checking required files")
    required      = ["main.py", "requirements.txt"]
    required_dirs = ["commands", "utils"]
    all_ok        = True

    for f in required:
        if Path(f).exists():
            print(f"  ✅ {f}")
        else:
            print(f"  ❌ Missing: {f}")
            all_ok = False

    for d in required_dirs:
        if Path(d).is_dir():
            print(f"  ✅ {d}/")
        else:
            print(f"  ❌ Missing directory: {d}/")
            all_ok = False

    if not all_ok:
        print("\n  Some files are missing. Try re-cloning the repository.")
        sys.exit(1)


def step_env():
    banner("6/7 — API keys setup")

    existing = {}
    if ENV_FILE.exists():
        print(f"  Found existing {ENV_FILE}. Checking for missing keys...")
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()

    keys = {
        "DISCORD_TOKEN":         ("Discord bot token", True),
        "GIPHY_API":             ("Giphy API key", False),
        "SPOTIFY_CLIENT_ID":     ("Spotify client ID", False),
        "SPOTIFY_CLIENT_SECRET": ("Spotify client secret", False),
        "RAPIDAPI_KEY":          ("RapidAPI key (optional, for /download)", False),
    }

    changed = False
    for key, (label, required) in keys.items():
        if key in existing:
            print(f"  ✅ {key} already set")
            continue
        tag   = " (required)" if required else " (optional, press Enter to skip)"
        value = ask(f"{label}{tag}")
        if value:
            existing[key] = value
            changed = True
        elif required:
            print(f"  ❌ {key} is required. Exiting.")
            sys.exit(1)

    if changed:
        lines = [f"{k}={v}" for k, v in existing.items()]
        ENV_FILE.write_text("\n".join(lines) + "\n")
        print(f"  ✅ Saved to {ENV_FILE}")
    else:
        print("  ✅ All keys present.")


def step_run():
    banner("7/7 — Starting Amber")

    # Remind user which message engine is active
    if MODEL_DIR.exists() and any(MODEL_DIR.iterdir()):
        print("  🧠 Cat message engine: domesticated-LLM")
    else:
        print("  🐱 Cat message engine: synthesis (no model downloaded)")

    print("  Launching main.py inside the virtual environment...\n")
    os.execv(VENV_PYTHON, [VENV_PYTHON, "main.py"])


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════╗
    ║       Amber Bot — Setup          ║
    ║   github.com/novodude/amber-bot  ║
    ╚══════════════════════════════════╝
    """)

    step_check_git()
    step_venv()
    step_install()
    step_model()
    step_check_files()
    step_env()
    step_run()
