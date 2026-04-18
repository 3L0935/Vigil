# tests/test_setup_utils.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch
import setup_utils


def _make_mock_db(setup_complete="", llama_model=""):
    m = MagicMock()
    def _get(key, default=""):
        return {"setup_complete": setup_complete, "llama_model": llama_model}.get(key, default)
    m.get_setting.side_effect = _get
    return m


def test_needs_first_run_no_settings():
    mock_db = _make_mock_db()
    with patch.object(setup_utils, "db", mock_db):
        assert setup_utils.needs_first_run() is True


def test_needs_first_run_setup_complete():
    mock_db = _make_mock_db(setup_complete="1")
    with patch.object(setup_utils, "db", mock_db):
        assert setup_utils.needs_first_run() is False


def test_needs_first_run_has_model_no_flag():
    """Existing install without flag — llama_model present means setup was done."""
    mock_db = _make_mock_db(llama_model="/path/to/model.gguf")
    with patch.object(setup_utils, "db", mock_db):
        assert setup_utils.needs_first_run() is False


def test_find_terminal_returns_none_when_nothing_found():
    with patch("setup_utils.shutil.which", return_value=None):
        assert setup_utils.find_terminal() is None


def test_find_terminal_returns_first_match():
    def which(name):
        return "/usr/bin/konsole" if name == "konsole" else None
    with patch("setup_utils.shutil.which", side_effect=which):
        assert setup_utils.find_terminal() == "konsole"


def test_launch_in_terminal_returns_false_when_no_terminal():
    with patch("setup_utils.shutil.which", return_value=None):
        assert setup_utils.launch_in_terminal("echo test") is False


def test_launch_in_terminal_returns_true_when_terminal_found():
    with patch("setup_utils.find_terminal", return_value="xterm"), \
         patch("setup_utils.subprocess.Popen") as mock_popen:
        result = setup_utils.launch_in_terminal("echo test")
    assert result is True
    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    assert args[0][0] == "xterm"
    assert args[0][1] == "-e"
    assert args[0][2] == "bash"
