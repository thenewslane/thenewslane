#!/usr/bin/env bash
# apps/agent/setup.sh
# Create virtual environment and install all agent dependencies.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON="${PYTHON:-python3}"
VENV_DIR=".venv"

# --- Python version check ---
echo "-> Checking Python version..."
"$PYTHON" -c "
import sys
v = sys.version_info
if v < (3, 11):
    print('ERROR: Python 3.11+ required, found {}.{}.{}'.format(v.major, v.minor, v.micro))
    sys.exit(1)
print('   Python {}.{}.{} OK'.format(v.major, v.minor, v.micro))
"

# --- Create virtual environment ---
if [ -d "$VENV_DIR" ]; then
    echo "-> Virtual environment already exists at $VENV_DIR (skipping creation)"
else
    echo "-> Creating virtual environment at $VENV_DIR..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

# --- Activate ---
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo "-> Activated: $(which python)"

# --- Upgrade pip and build tools ---
echo "-> Upgrading pip, setuptools, wheel..."
pip install --quiet --upgrade pip setuptools wheel

# --- Install package with all dependencies ---
echo "-> Installing agent package in editable mode (this may take a few minutes)..."
pip install -e ".[dev]"

# --- Verify key imports ---
echo ""
echo "-> Verifying key imports..."
python - <<'PYCHECK'
import sys

py_version = sys.version_info[:2]

# (module_name, pip_package, known_broken_on_py314)
imports = [
    ("langgraph",          "langgraph",          False),
    ("langchain_anthropic","langchain-anthropic", False),
    ("supabase",           "supabase",            False),
    ("anthropic",          "anthropic",           False),
    ("groq",               "groq",                False),
    # replicate uses pydantic.v1 compat shim which is removed in Python 3.14
    ("replicate",          "replicate",           py_version >= (3, 14)),
    ("apify_client",       "apify-client",        False),
    ("vaderSentiment",     "vaderSentiment",      False),
    ("numpy",              "numpy",               False),
    ("pandas",             "pandas",              False),
    ("inngest",            "inngest",             False),
    ("boto3",              "boto3",               False),
    ("pydantic_settings",  "pydantic-settings",   False),
    ("httpx",              "httpx",               False),
    ("dotenv",             "python-dotenv",       False),
    ("ffmpeg",             "ffmpeg-python",       False),
]

ok, skipped, failed = [], [], []
for mod, pkg, known_broken in imports:
    try:
        __import__(mod)
        ok.append(pkg)
        print("  OK   " + pkg)
    except Exception as e:
        if known_broken:
            skipped.append((pkg, str(e)))
            print("  SKIP " + pkg + " (pydantic v1 compat removed in Python 3.14 -- known upstream issue)")
        else:
            failed.append((pkg, str(e)))
            print("  FAIL " + pkg + ": " + str(e))

print("")
print(str(len(ok)) + " packages OK, " + str(len(skipped)) + " skipped (known 3.14 issue), " + str(len(failed)) + " failed")

if skipped:
    print("")
    print("NOTE: The following packages have import issues on Python 3.14:")
    for pkg, _ in skipped:
        print("  - " + pkg + ": uses pydantic.v1 compat shim (removed in Python 3.14).")
    print("  Workaround: wrap import in try/except or use Python 3.12 for full compat.")
    print("  Tracking issue: https://github.com/pydantic/pydantic/issues/8202")

if failed:
    print("")
    print("FATAL: " + str(len(failed)) + " package(s) failed:")
    for pkg, err in failed:
        print("  - " + pkg + ": " + err)
    raise SystemExit(1)
PYCHECK

# --- Done ---
echo ""
echo "-------------------------------------------------------------"
echo "Setup complete!"
echo ""
echo "Activate with:  source apps/agent/.venv/bin/activate"
echo "Run pipeline:   python main.py"
echo ""
echo "NOTE: ffmpeg-python requires the ffmpeg system binary."
echo "  macOS:  brew install ffmpeg"
echo "  Ubuntu: sudo apt install ffmpeg"
echo "-------------------------------------------------------------"
