"""Put the repo root on sys.path so `import schema`, `import modules`, etc.
resolve when running pytest from anywhere."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
