import subprocess
import sys
import os

if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), "frontend"))
    subprocess.run([sys.executable, "-m", "npm", "run", "dev"])