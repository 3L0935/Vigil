"""Keep every test away from the user's live settings, logs and model cache."""
import os
import tempfile
from pathlib import Path

_TEST_ROOT = tempfile.TemporaryDirectory(prefix='vigil-tests-')
os.environ['XDG_DATA_HOME'] = str(Path(_TEST_ROOT.name) / 'data')
os.environ['XDG_CACHE_HOME'] = str(Path(_TEST_ROOT.name) / 'cache')
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'

import database
database.init()
