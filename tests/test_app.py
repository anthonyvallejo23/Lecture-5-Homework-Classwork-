import pytest
from app import create_app
from redactor import Redactor

@pytest.fixture
def mock_html_template(tmp_path, monkeypatch):
    """
    Creates a temporary pristine index.html inside a templates directory
    to satisfy the app's startup configuration file-read setup.
    """
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    html_file = templates_dir / "index.html"
    
    # Simple representation of template tokens to support the app's replacement logic
    html_file.write_text(
        "__INPUT_TEXT__ __PER_CHECKED__ __LOC_CHECKED__ __ORG_CHECKED__ "
        "__MISC_CHECKED__ __ERROR__ __RESULTS__", 
        encoding="utf-8"
    )
    
    # Force the app to open the file inside our temporary path
    monkeypatch.chdir(tmp_path)
    return html_file

@pytest.fixture
def client(mock_html_template):
    """
    Provides a configured test client with a mock pipeline to prevent 
    triggering the model download during test executions.
    """
    # Custom dummy pipeline function replacing transformers.pipeline
    def mock_ner_pipeline(text):
        results = []
        if "Maria Lopez" in text:
            results.append({
                "entity_group": "PER",
                "score": 0.998,
                "word": "Maria Lopez",
                "start": text.find("Maria Lopez"),
                "end": text.find("Maria Lopez") + len("Maria Lopez")
            })
        if "Denver" in text:
            results.append({
                "entity_group": "LOC",
                "score": 0.75,  # Intentionally under the default 0.80 threshold
                "word": "Denver",
                "start": text.find("Denver"),
                "end": text.find("Denver") + len("Denver")
            })
        return results

    # Inject mock pipeline directly into the real Redactor instance
    redactor = Redactor(min_score=0.80, ner_pipeline=mock_ner_pipeline)
    app = create_app(redactor_instance=redactor)
    app.config["TESTING"] = True
    
    with app.test_client() as test_client:
        yield test_client

# --- Test Case 1: Successful Redaction ---
def test_successful_redaction(client):
    payload = {
        "text": "I met Dr. Maria Lopez today.",
        "types": ["PER"]
    }
    response = client.post("/api/redact", json=payload)
    assert response.status_code == 200
    
    data = response.get_json()
    assert "redacted_text" in data
    assert "I met Dr. [PER] today." in data["redacted_text"]
    assert len(data["entities"]) == 1
    assert data["entities"][0]["type"] == "PER"  # Fixed array indexing here

# --- Test Case 2: Email Rule Always Triggers ---
def test_email_rule_always_triggers(client):
    payload = {
        "text": "Contact me at test@example.com right away.",
        "types": ["PER"]  # Even if PER is specified, emails must redact
    }
    response = client.post("/api/redact", json=payload)
    assert response.status_code == 200
    
    data = response.get_json()
    assert "[EMAIL]" in data["redacted_text"]
    assert len(data["entities"]) == 1
    assert data["entities"][0]["type"] == "EMAIL"  # Fixed array indexing here

# --- Test Case 3: Score Threshold Filters Entities ---
def test_score_threshold_filtering(client):
    # 'Denver' returns a mock score of 0.75, which is lower than min_score=0.80
    payload = {
        "text": "I went to Denver.",
        "types": ["LOC"]
    }
    response = client.post("/api/redact", json=payload)
    assert response.status_code == 200
    
    data = response.get_json()
    # Should NOT be redacted since it's below the threshold config line
    assert "Denver" in data["redacted_text"]
    assert "[LOC]" not in data["redacted_text"]
    assert len(data["entities"]) == 0

# --- Test Case 4: Invalid Entity Types Configuration ---
def test_invalid_types_returns_error(client):
    payload = {
        "text": "Hello world",
        "types": ["INVALID_TYPE", "PER"]
    }
    response = client.post("/api/redact", json=payload)
    
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "types must only be PER, LOC, ORG, or MISC" in data["error"]

# --- Test Case 5: Empty or Too-Long Text ---
def test_text_length_boundaries(client):
    # Test Empty boundary rule (0 chars)
    payload_empty = {"text": "", "types": ["PER"]}
    response_empty = client.post("/api/redact", json=payload_empty)
    assert response_empty.status_code == 400
    assert "Text must be between 1 and 10000 characters" in response_empty.get_json()["error"]
    
    # Test Too Long boundary rule (10,001 chars)
    payload_long = {"text": "A" * 10001, "types": ["PER"]}
    response_long = client.post("/api/redact", json=payload_long)
    assert response_long.status_code == 400
    assert "Text must be between 1 and 10000 characters" in response_long.get_json()["error"]

# --- Test Case 6: Custom JSON 404 Handler ---
def test_custom_json_404(client):
    response = client.get("/api/invalid_route_path")
    assert response.status_code == 404
    
    assert response.is_json
    data = response.get_json()
    assert data == {"error": "Not found"}
