import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_ensure_running_managed_spawns_process():
    """ensure_running() spawns subprocess when managed=true and no process running."""
    from llm_manager import LlamaServerManager
    mgr = LlamaServerManager()

    with patch("llm_manager.db") as mock_db, \
         patch("llm_manager.subprocess.Popen") as mock_popen, \
         patch.object(mgr, "_wait_health"), \
         patch.object(mgr, "_reset_timer"):
        mock_db.get_setting.side_effect = lambda key, default="": {
            "llama_server_managed": "true",
            "llama_server_bin":     "/usr/bin/llama-server",
            "llama_model":          "/models/qwen.gguf",
            "llama_unload_timeout": "120",
        }.get(key, default)
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        mgr.ensure_running()

        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert "/usr/bin/llama-server" in args
        assert "/models/qwen.gguf" in args
        # -c must always be passed so llama-server doesn't fall back to the
        # GGUF's n_ctx_train (can be 32k–128k, blows VRAM).
        assert "-c" in args
        ctx_value = args[args.index("-c") + 1]
        assert int(ctx_value) > 0


def test_ensure_running_unmanaged_does_not_spawn():
    """ensure_running() does NOT spawn when managed=false."""
    from llm_manager import LlamaServerManager
    mgr = LlamaServerManager()

    with patch("llm_manager.db") as mock_db, \
         patch("llm_manager.subprocess.Popen") as mock_popen, \
         patch.object(mgr, "_wait_health"), \
         patch.object(mgr, "_reset_timer"):
        mock_db.get_setting.side_effect = lambda key, default="": {
            "llama_server_managed": "false",
        }.get(key, default)

        mgr.ensure_running()
        mock_popen.assert_not_called()


def test_auto_shutdown_kills_process():
    """_auto_shutdown() terminates the managed process."""
    from llm_manager import LlamaServerManager
    mgr = LlamaServerManager()
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mgr._process = mock_proc

    mgr._auto_shutdown()

    mock_proc.terminate.assert_called_once()


def test_timeout_zero_never_schedules_timer():
    """timeout=0 means never unload — no Timer is created."""
    from llm_manager import LlamaServerManager
    mgr = LlamaServerManager()

    with patch("llm_manager.db") as mock_db, \
         patch("llm_manager.threading.Timer") as mock_timer:
        mock_db.get_setting.return_value = "0"
        mgr._reset_timer()
        mock_timer.assert_not_called()


def test_ensure_running_ollama_does_not_spawn():
    """ensure_running() does NOT spawn when provider=ollama."""
    from llm_manager import LlamaServerManager
    mgr = LlamaServerManager()

    with patch("llm_manager.db") as mock_db, \
         patch("llm_manager.subprocess.Popen") as mock_popen, \
         patch.object(mgr, "_wait_health"), \
         patch.object(mgr, "_reset_timer"):
        mock_db.get_setting.side_effect = lambda key, default="": {
            "llm_provider": "ollama_local",
        }.get(key, default)

        mgr.ensure_running()
        mock_popen.assert_not_called()


def test_shutdown_ollama_is_noop():
    """shutdown() does nothing when provider=ollama."""
    from llm_manager import LlamaServerManager
    mgr = LlamaServerManager()
    mgr._process = MagicMock()  # would be dangerous if terminate() called

    with patch("llm_manager.db") as mock_db:
        mock_db.get_setting.return_value = "ollama"
        mgr.shutdown()

    mgr._process.terminate.assert_not_called()


def test_auto_shutdown_ollama_skips():
    """_auto_shutdown() does nothing when provider=ollama."""
    from llm_manager import LlamaServerManager
    mgr = LlamaServerManager()
    mgr._process = MagicMock()

    with patch("llm_manager.db") as mock_db:
        mock_db.get_setting.return_value = "ollama"
        mgr._auto_shutdown()

    mgr._process.terminate.assert_not_called()
