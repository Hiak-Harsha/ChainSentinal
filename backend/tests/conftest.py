# conftest.py - shared test fixtures
import sys
from pathlib import Path

# Ensure the backend directory is on the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
