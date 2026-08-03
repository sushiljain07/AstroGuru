import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from main import app
from services.geocode import GeoResult

client = TestClient(app)

VALID_BODY = {
    "date": "1990-01-01",
    "time": "12:00",
    "place": "Delhi, India",
    "question": "What does my Pisces ascendant say about career?",
    "language": "en",
}


def _geo():
    return GeoResult(lat=28.6139, lon=77.2090, timezone="Asia/Kolkata", display_name="New Delhi")


def test_ask_returns_answer():
    # ask_chart returns a (answer, provider_label) tuple — see services/ai.py —
    # not a bare string. The mock previously returned a bare string here,
    # which `answer, provider = ask_chart(...)` in routes/kundli.py would have
    # failed to unpack; that was masked by an earlier, unrelated failure (this
    # test also had no geocode mock, so it depended on a live network call to
    # Nominatim that doesn't work in every environment).
    with patch("services.chart_context.geocode_place", return_value=_geo()), \
         patch("routes.kundli.ask_chart", return_value=("Test answer text.", "Claude")):
        resp = client.post("/api/kundli/ask", json=VALID_BODY)
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0


def test_ask_missing_question_returns_422():
    body = {k: v for k, v in VALID_BODY.items() if k != "question"}
    resp = client.post("/api/kundli/ask", json=body)
    assert resp.status_code == 422


def test_ask_overlong_question_returns_422():
    # question has a 500-char limit (see models/chart_data.py's AskRequest) —
    # this is the field that gets concatenated directly into the AI prompt,
    # so it's the most directly relevant constraint of the two H5 added.
    # No geocode mock needed: Pydantic validates the request body before the
    # route handler (and therefore geocoding) ever runs.
    resp = client.post("/api/kundli/ask", json={**VALID_BODY, "question": "a" * 501})
    assert resp.status_code == 422


def test_ask_invalid_place_returns_400():
    body = {**VALID_BODY, "place": "xyzzy_not_a_real_place_12345"}
    with patch("services.chart_context.geocode_place", side_effect=ValueError("Place not found")):
        resp = client.post("/api/kundli/ask", json=body)
    assert resp.status_code == 400


def test_ask_no_key_returns_503():
    # Today's failover order (see services/ai.py's _call_llm) tries
    # OpenRouter, then Claude (direct via ANTHROPIC_API_KEY), then Groq —
    # only raising 503 once *all three* are unavailable. This test
    # previously cleared only GROQ_API_KEY, which matched an earlier
    # Groq-primary architecture (see PROGRESS.md) but not the current one —
    # clearing just Groq while a real key for any earlier provider is present
    # in the environment would actually still succeed, not 503.
    keys_to_clear = ["OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY"]
    originals = {k: os.environ.get(k) for k in keys_to_clear}
    for k in keys_to_clear:
        os.environ[k] = ""
    try:
        with patch("services.chart_context.geocode_place", return_value=_geo()):
            resp = client.post("/api/kundli/ask", json=VALID_BODY)
        assert resp.status_code == 503
    finally:
        for k, v in originals.items():
            if v:
                os.environ[k] = v
            elif k in os.environ:
                del os.environ[k]
