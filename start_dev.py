#!/usr/bin/env python3
"""
Studio Desire — Development Server Launcher (Alias for start_up.py)
"""
import sys
import subprocess
from pathlib import Path

target = Path(__file__).resolve().parent / "start_up.py"
if not target.exists():
    print(f"[ERROR] Could not find start_up.py at {target}")
    sys.exit(1)

try:
    subprocess.run([sys.executable, str(target)] + sys.argv[1:], cwd=str(target.parent))
except KeyboardInterrupt:
    pass
