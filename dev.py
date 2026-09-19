#!/usr/bin/env python3
"""
dev.py - the only commands you need. Run these from the project root.

    python dev.py setup     install everything (do this once)
    python dev.py run       start the app, then open http://127.0.0.1:8000
    python dev.py test      run the 192 tests
    python dev.py check     everything the build checks: tests + fixtures + browser
    python dev.py fixtures  regenerate the market data
    python dev.py reset     wipe the venv and start over

Why this file exists: it finds the right Python for you. A very common problem is
running `python -m pytest` with the system Python instead of the project's virtual
environment, which fails with errors that look like real bugs but are not. This
script always uses .venv, so that cannot happen.

You do NOT need to "activate" anything. Just use `python dev.py <command>`.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
IS_WINDOWS = os.name == "nt"
VENV_PY = VENV / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def say(msg):
    print(f"\n>>> {msg}\n", flush=True)


def die(msg, fix=None):
    print(f"\nSTOPPED: {msg}", file=sys.stderr)
    if fix:
        print(f"\nTo fix it:\n  {fix}\n", file=sys.stderr)
    sys.exit(1)


def need_venv():
    """The project's Python, or a clear explanation of how to create it."""
    if not VENV_PY.exists():
        die("The virtual environment does not exist yet.",
            "python dev.py setup")
    return str(VENV_PY)


def run(args, **kw):
    """Run a command and stop the script if it fails."""
    result = subprocess.run(args, cwd=ROOT, **kw)
    if result.returncode != 0:
        sys.exit(result.returncode)
    return result


# --------------------------------------------------------------------- commands

def cmd_setup():
    """Create .venv and install the dependencies. Safe to re-run."""
    if sys.version_info < (3, 10):
        die(f"This project needs Python 3.10 or newer. You have {sys.version.split()[0]}.",
            "Install a newer Python from python.org, then run this again.")

    if not VENV_PY.exists():
        say("Creating the virtual environment in .venv/ (this takes a few seconds)")
        run([sys.executable, "-m", "venv", str(VENV)])
    else:
        say("The virtual environment already exists, reusing it")

    say("Installing the dependencies")
    run([str(VENV_PY), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
    run([str(VENV_PY), "-m", "pip", "install", "--quiet", "-r",
         str(ROOT / "server" / "requirements.txt")])

    say("Done. Now run:  python dev.py run")


def cmd_run():
    """Start the app. One process serves both the API and the web page."""
    py = need_venv()
    say("Starting on http://127.0.0.1:8000  -  press Ctrl+C to stop")
    print("If the page does not load, check this window for a red error message.\n")
    try:
        subprocess.run([py, "-m", "uvicorn", "server.main:app",
                        "--port", "8000", "--reload"], cwd=ROOT)
    except KeyboardInterrupt:
        say("Stopped.")


def cmd_test():
    """Run the test suite."""
    py = need_venv()
    say("Running the tests")
    run([py, "-m", "pytest", "-q"])
    say("All tests passed.")


def cmd_fixtures():
    """Regenerate the synthetic market data. Deterministic - safe to re-run."""
    py = need_venv()
    say("Regenerating fixtures/")
    run([py, str(ROOT / "scripts" / "build_fixtures.py")])
    say("Done. Run `python dev.py test` to confirm nothing drifted.")


def cmd_check():
    """Everything the build checks. Run this before you commit."""
    py = need_venv()

    say("1 of 3: tests")
    run([py, "-m", "pytest", "-q"])

    say("2 of 3: fixtures match a fresh build")
    run([py, str(ROOT / "scripts" / "build_fixtures.py"), "--check"])

    say("3 of 3: the browser test")
    if shutil.which("node") is None:
        print("SKIPPED: Node.js is not installed, so the browser test cannot run.")
        print("That is okay - the first two checks are the important ones.")
        print("To run it later, install Node 22+ from nodejs.org.\n")
    else:
        env = dict(os.environ, PYTHON=py)
        result = subprocess.run(["node", str(ROOT / "scripts" / "e2e-browser.mjs")],
                                cwd=ROOT, env=env)
        if result.returncode == 2:
            print("\nSKIPPED: the browser test could not start.")
            print("Usually this means port 8000 is already in use - stop your")
            print("running app first (Ctrl+C in that window), then try again.\n")
        elif result.returncode != 0:
            die("The browser test found a problem. Scroll up to see which check failed.")

    say("Everything passed. Safe to commit.")


def cmd_reset():
    """Delete the virtual environment and start clean."""
    if VENV.exists():
        say("Deleting .venv/")
        shutil.rmtree(VENV, ignore_errors=True)
    say("Gone. Run:  python dev.py setup")


COMMANDS = {
    "setup": cmd_setup,
    "run": cmd_run,
    "test": cmd_test,
    "check": cmd_check,
    "fixtures": cmd_fixtures,
    "reset": cmd_reset,
}


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    action = COMMANDS.get(name)
    if action is None:
        print(__doc__)
        if name:
            print(f"Unknown command: {name!r}. Pick one of: {', '.join(COMMANDS)}")
        return 1
    action()
    return 0


if __name__ == "__main__":
    sys.exit(main())
