import sys
from pathlib import Path

# The app is packaged with `core` as the working directory, so its modules
# import each other by bare name. Mirror that here.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
