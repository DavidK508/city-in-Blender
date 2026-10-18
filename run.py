"""Bootstrap for headless Blender: blender --background --python run.py -- [args]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from city.main import cli

if __name__ == "__main__":
    cli()
