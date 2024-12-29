import pytest
from helpers import fetch_inventory, generate_openai_recipe

def test_fetch_inventory(monkeypatch):
    def mock_get(*args, **kwargs):
        class MockResponse:
            status_code = 200
            def json(self):
                return [{"name": "Test Hops"}]

        return MockResponse()

    monkeypatch.setattr("requests.get", mock_get)
    result = fetch_inventory("hops")
    assert result == [{"name": "Test Hops"}]

def test_generate_openai_recipe(monkeypatch):
    def mock_post(*args, **kwargs):
        class MockResponse:
            status_code = 200
            def json(self):
                return {"choices": [{"message": {"content": "Test Recipe"}}]}

        return MockResponse()

    monkeypatch.setattr("requests.post", mock_post)
    prompt = "Generate a test recipe."
    result = generate_openai_recipe(prompt)
    assert result == "Test Recipe"
