"""Noninteractive setup asset selection and platform guards."""

from unittest.mock import patch

import pytest

from vigil_ui import setup_service


def test_detect_backend_prefers_rocm_on_amd_host():
    def which(name):
        return "/opt/rocm/bin/rocminfo" if name == "rocminfo" else None

    with patch.object(setup_service.shutil, "which", side_effect=which):
        assert setup_service.detect_backend() == "rocm"


@pytest.mark.parametrize("vram, expected", [
    (0, "Qwen_Qwen3.5-0.8B-Q4_K_M.gguf"),
    (8192, "Qwen_Qwen3.5-4B-Q4_K_M.gguf"),
    (20480, "Qwen_Qwen3.5-9B-Q8_0.gguf"),
])
def test_recommended_model_respects_vram_budget(vram, expected):
    with patch.object(setup_service, "detect_vram_mb", return_value=vram):
        assert setup_service.recommended_model() == expected


def test_unsupported_platform_rejects_linux_binary_catalog():
    with patch.object(setup_service.platform, "system", return_value="Windows"):
        with pytest.raises(RuntimeError, match="Linux x86_64"):
            setup_service.fetch_binary_asset("rocm")
