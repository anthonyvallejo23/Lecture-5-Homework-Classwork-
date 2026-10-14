import pytest
from app import create_app

class FakeRedactor:
    """
    A lightweight test double that skips Hugging Face pipelines entirely 
    and simulates specific scenario models for unit tests.
    """
    def __init__(self, min_score=0.80):
        self.min_score = min_score
        self.model_name = "dslim/bert-base-NER"

    def redact(self, text, types=None):
        # Explicit input validation logic matching redactor.py constraints
        if not isinstance(text, str) or not 1 
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Text Redactor</title>
</head>
<body>
  <h1>Text Redactor</h1>

  <form method="post" action="/redact">
    <p>
      <label for="text">Text to redact</label><br>
      <textarea id="text" name="text" rows="10" cols="60" maxlength="10000" required placeholder="Enter your text here...">__INPUT_TEXT__</textarea>
    </p>

    <fieldset>
      <legend>Entity types</legend>
      <label> People (PER)</label><br>
      <label> Locations (LOC)</label><br>
      <label> Organizations (ORG)</label><br>
      <label> Miscellaneous Names (MISC)</label>
    </fieldset>

    <p><button type="submit">Redact text</button></p>
  </form>

  __ERROR__
  
  __RESULTS__
</body>
</html>"""
    
    template_file.write_text(html_layout, encoding="utf-8")
    
    # Intercept working path lookups dynamically
    monkeypatch.chdir(tmp_path)

    fake_redactor = FakeRedactor(min_score=0.80)
    app = create_app(redactor_instance=fake_redactor)
    app.config["TESTING"] = True
    
    with app.test_client() as test_client:
        yield test_client


 1. Cover a successful redaction
def test_successful_redaction(client):
    payload = {
        "text": "I met Dr. Maria Lopez at Riverside Clinic in Denver. Email me at maria@example.com."
    }
    response = client.post("/api/redact", json=payload)
    assert response.status_code == 200
    
    data = response.get_json()
    assert "[PER]" in data["redacted_text"]
    assert "[ORG]" in data["redacted_text"]
    assert "[LOC]" in data["redacted_text"]
    assert len(data["entities"]) == 4


 2. Cover the email rule (Regex matches and extracts emails)
def test_email_rule_redaction(client):
    payload = {"text": "Reach out via test@domain.com."}
    response = client.post("/api/redact", json=payload)
    assert response.status_code == 200
    
    data = response.get_json()
    assert "[EMAIL]" in data["redacted_text"]
    assert data["entities"][0]["type"] == "EMAIL"


# 3. Cover the score threshold
def test_score_threshold_enforcement(client):
    # App-level config value must pull exactly from app layout settings
    assert client.application.config["SCORE_THRESHOLD"] == 0.80
    
    payload = {"text": "lowconfidence entity entry text mapping."}
    response = client.post("/api/redact", json=payload)
    assert response.status_code == 200
    
    data = response.get_json()
    # Verify that the low score entity was dropped by checking that the entity list remains empty
    assert len(data["entities"]) == 0


 4. Cover invalid types
def test_invalid_entity_types(client):
    payload = {
        "text": "Valid length string.",
        "types": ["INVALID_LABEL_PROP"]
    }
    response = client.post("/api/redact", json=payload)
    assert response.status_code == 400
    
    data = response.get_json()
    assert "types must only be PER, LOC, ORG, or MISC" in data["error"]


 5. Cover empty or too-long text
def test_text_length_bounds(client):
    # Test blank empty string handling
    response_empty = client.post("/api/redact", json={"text": ""})
    assert response_empty.status_code == 400
    assert "Text must be between 1 and 10000 characters" in response_empty.get_json()["error"]

    # Test extreme over-capacity constraints
    response_long = client.post("/api/redact", json={"text": "X" * 10001})
    assert response_long.status_code == 400
    assert "Text must be between 1 and 10000 characters" in response_long.get_json()["error"]


 6. Cover a JSON 404
def test_unknown_routes_return_json_404(client):
    response = client.get("/api/invalid-route-path")
    assert response.status_code == 404
    assert response.is_json
    assert response.get_json() == {"error": "Not found"}
