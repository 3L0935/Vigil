"""Generation settings supported by the local llama.cpp API."""

from pathlib import Path
import re


def profile(model: str, provider: str) -> dict:
    if provider != "llama_cpp":
        return {}
    label = Path(model).name.lower()
    if "lfm2.5" in label and "instruct" in label:
        return {"temperature": 0.1, "top_k": 50, "repeat_penalty": 1.05,
                "parallel_tool_calls": False}
    if "lfm2.5-2.6b" in label:
        return {"temperature": 0.1, "top_k": 50, "repeat_penalty": 1.1,
                "parallel_tool_calls": False}
    if re.search(r"qwen3[-_]4b(?:[-_.]|$)", label) and "thinking" not in label:
        return {"temperature": 0.7, "top_p": 0.8, "top_k": 20,
                "min_p": 0, "chat_template_kwargs": {"enable_thinking": False},
                "parallel_tool_calls": False}
    return {"parallel_tool_calls": False}
