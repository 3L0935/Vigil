import json

import pytest

import assistant
from assistant_tools import InvalidToolCall, validate_call


def call(name, args):
    return {"function": {"name": name, "arguments": json.dumps(args)}}


@pytest.mark.parametrize("name,args", [
    ("app_action", {"name": "Firefox", "action": "launchh"}),
    ("app_action", {"name": "Firefox"}),
    ("app_action", {"name": "Firefox", "action": "launch", "shell": "x"}),
    ("search_web", {"query": "x", "max_results": True}),
    ("search_web", {"query": "x", "max_results": 11}),
    ("search_web", {"query": " "}),
    ("search_files", {"folder": "downloads", "query": "x", "include_size": 1}),
])
def test_invalid_arguments_are_rejected(name, args):
    with pytest.raises(InvalidToolCall):
        validate_call(call(name, args), [assistant._WEB_SEARCH_TOOL,
                                         assistant._APP_ACTION_TOOL,
                                         assistant._SEARCH_FILES_TOOL])


def test_non_object_and_unadvertised_tool_are_rejected():
    with pytest.raises(InvalidToolCall):
        validate_call(call("app_action", ["Firefox"]), [assistant._APP_ACTION_TOOL])
    with pytest.raises(InvalidToolCall):
        validate_call(call("open_url", {"target": "example"}), [assistant._APP_ACTION_TOOL])
    with pytest.raises(InvalidToolCall):
        validate_call({"function": {"name": "app_action", "arguments": "{"}},
                      [assistant._APP_ACTION_TOOL])


def test_valid_call_keeps_exact_arguments():
    name, args = validate_call(call("app_action", {"name": "Firefox", "action": "close"}),
                               [assistant._APP_ACTION_TOOL])
    assert (name, args) == ("app_action", {"name": "Firefox", "action": "close"})
