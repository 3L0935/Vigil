import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_detect_gpu_cuda():
    """Returns 'cuda' when nvidia-smi exits 0."""
    import first_run
    with patch("first_run.subprocess.run", return_value=MagicMock(returncode=0)):
        assert first_run.detect_gpu() == "cuda"


def test_detect_gpu_rocm():
    """Returns 'rocm' when nvidia-smi fails but rocm-smi exits 0."""
    import first_run
    def side_effect(cmd, **kwargs):
        r = MagicMock()
        r.returncode = 0 if cmd[0] == "rocm-smi" else 1
        return r
    with patch("first_run.subprocess.run", side_effect=side_effect):
        assert first_run.detect_gpu() == "rocm"


def test_detect_gpu_cpu_fallback():
    """Returns 'cpu' when all GPU tools return non-zero."""
    import first_run
    with patch("first_run.subprocess.run", return_value=MagicMock(returncode=1)):
        assert first_run.detect_gpu() == "cpu"


def test_select_model_tier_8gb():
    """8 GB VRAM → budget 4505 MB → Qwen3.5-4B fits (2500), Qwen3.5-9B does not (5500)."""
    import first_run
    result = first_run.select_model_tier(total_vram_mb=8192)
    assert result["name"] == "Qwen3.5-4B Q4_K_M"


def test_select_model_tier_20gb():
    """20 GB VRAM → budget 11264 MB → Qwen3.5-9B Q8_0 fits (10000)."""
    import first_run
    result = first_run.select_model_tier(total_vram_mb=20480)
    assert result["name"] == "Qwen3.5-9B Q8_0"


def test_select_model_tier_cpu_only():
    """0 MB VRAM → returns smallest model."""
    import first_run
    result = first_run.select_model_tier(total_vram_mb=0)
    assert result["name"] == "Qwen3.5-0.8B Q4_K_M"
