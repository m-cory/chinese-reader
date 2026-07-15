import os
import pathlib
import sys
import tempfile

# Make the backend package importable (tests live in backend/tests).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# Point the app at a throwaway data dir BEFORE app/config import happens.
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="cr-test-"))
os.environ["CR_DATA_DIR"] = str(_tmp)
os.environ["CR_DB_PATH"] = str(_tmp / "test.db")
