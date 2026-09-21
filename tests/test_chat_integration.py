"""
First integration test for GopherGPT's /chat endpoint.

Goal: confirm that asking about a course's grade distribution causes the
agent to actually call the gophergrades_class tool, not just produce a
plausible-sounding answer.

Scope: LLM_PROVIDER=ollama only. Requires a local Ollama server running
the model set in LLM_MODEL (or the default qwen2.5:7b-instruct-q4_K_M).
"""

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_chat_triggers_gophergrades_class(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("DATA_DIR", "/tmp/gophergpt_test")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key-for-testing")

    with patch("autonomy.tools.gophergrades_api._get_json") as mock_get_json:
        mock_get_json.return_value = {
            "success": True,
            "data": {"grades": {"A": 50, "B": 30, "C": 10, "D": 5, "F": 5}},
        }

        from webservice.app import app

        with TestClient(app) as client:
            response = client.post(
                "/chat",
                json={"message": "What's the grade distribution for CSCI 1933?"},
            )

        assert response.status_code == 200
        mock_get_json.assert_called_once()

        called_url = mock_get_json.call_args[0][0]
        assert "/class/" in called_url
