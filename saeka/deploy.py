import os
import subprocess
import sys

def main():
    print("Initializing Saeka GCP Deployer...")
    script_path = os.path.join(os.path.dirname(__file__), "..", "setup.sh")
    
    # Alternatively, you can embed your Bash logic directly here in Python 
    # or call your setup.sh if bundled as package data.
    if os.path.exists(script_path):
        os.chmod(script_path, 0o755)
        try:
            subprocess.run(["bash", script_path], check=True)
        except Exception as e:
            print(f"Deployment error: {e}")
    else:
        print("Error: please retry or contact saeka for troubleshooting.")

if __name__ == "__main__":
    main()
