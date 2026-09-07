import os
import subprocess

def main():
    print("Initializing Saeka GCP Deployer...")
    # Look in the same directory where deploy.py lives
    script_path = os.path.join(os.path.dirname(__file__), "setup.sh")
    
    if os.path.exists(script_path):
        os.chmod(script_path, 0o755)
        try:
            subprocess.run(["bash", script_path], check=True)
        except Exception as e:
            print(f"Deployment error: {e}")
    else:
        print(f"Error: setup.sh not found at {script_path}")

if __name__ == "__main__":
    main()
