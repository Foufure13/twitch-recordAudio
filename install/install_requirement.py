import subprocess
import sys

def install_packages_from_requirements(file_path='install/requirements.txt'):
    with open(file_path, 'r') as f:
        packages = f.readlines()
    for package in packages:
        package = package.strip()
        if package:  # Assure que la ligne n'est pas vide
            try:
                print(f"Installation of {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            except subprocess.CalledProcessError as e:
                print(f"Failed to install --> {package}: {e}")

if __name__ == "__main__":
    install_packages_from_requirements()
    print("Installation of dependencies completed.")
