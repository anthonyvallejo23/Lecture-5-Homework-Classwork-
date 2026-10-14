from flask import Flask, jsonify, render_template_string, request
from redactor import Redactor


def create_app(redactor_instance=None):
  app = Flask(__name__)
  app.config["SCORE_THRESHOLD"] = 0.80

  if redactor_instance is None:
    app.redactor = Redactor(min_score=app.config["SCORE_THRESHOLD"])
  else:
    app.redactor = redactor_instance

  # Load the raw template into memory once during startup to not lose the placeholder tokens
  with open("templates/index.html", "r", encoding="utf-8") as f:
    app.config["RAW_HTML_TEMPLATE"] = f.read()

  def render_html_page(
      text="",
      selected_types=None,
      error_msg="",
      results_data=None,
  ):
    """Safely updates a pristine copy of the HTML template string."""
    if selected_types is None:
      selected_types = {"PER", "LOC", "ORG", "MISC"}

    # Work from a fresh copy of the original layout string
    html_content = app.config["RAW_HTML_TEMPLATE"]

    error_html = (
        f'<p style="color: red; font-weight: bold;">Error: {error_msg}</p>'
        if error_msg
        else ""
    )

    results_html = ""
    if results_data:
      table_rows = "".join([
          f"<tr><td>{ent['type']}</td><td>{ent['text']}</td><td>{ent['score']:.3f}</td></tr>"
          for ent in results_data["entities"]
      ])
      results_html = f"""
            <h3>Redacted Text:</h3>
            <div style="background: #f9f9f9; padding: 15px; border: 1px solid #ccc; white-space: pre-wrap;">{results_data['redacted_text']}</div>
            
            <h3>Removed Entities:</h3>
            <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%; margin-top: 10px;">
                <thead>
                    <tr style="background: #f4f4f4;">
                        <th>Type</th>
                        <th>Original Text</th>
                        <th>Score</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows if table_rows else '<tr><td colspan="3">No entities removed.</td></tr>'}
                </tbody>
            </table>
            """

    # Swap out tokens cleanly
    html_content = html_content.replace("__INPUT_TEXT__", text)
    html_content = html_content.replace(
        "__PER_CHECKED__", "checked" if "PER" in selected_types else ""
    )
    html_content = html_content.replace(
        "__LOC_CHECKED__", "checked" if "LOC" in selected_types else ""
    )
    html_content = html_content.replace(
        "__ORG_CHECKED__", "checked" if "ORG" in selected_types else ""
    )
    html_content = html_content.replace(
        "__MISC_CHECKED__", "checked" if "MISC" in selected_types else ""
    )
    html_content = html_content.replace("__ERROR__", error_html)
    html_content = html_content.replace("__RESULTS__", results_html)

    return render_template_string(html_content)

  @app.errorhandler(404)
  def not_found(e):
    return jsonify({"error": "Not found"}), 404

  @app.route("/", methods=["GET"])
  def index():
    return render_html_page()

  @app.route("/redact", methods=["POST"])
  def redact_web():
    text = request.form.get("text", "")
    selected_types = request.form.getlist("entity_types")

    try:
      types_arg = selected_types if selected_types else None
      results = app.redactor.redact(text, types=types_arg)
      return render_html_page(
          text=text, selected_types=set(selected_types), results_data=results
      )
    except ValueError as err:
      return render_html_page(
          text=text, selected_types=set(selected_types), error_msg=str(err)
      )

  @app.route("/api/health", methods=["GET"])
  def health():
    return jsonify({"status": "ok", "model": app.redactor.model_name})

  @app.route("/api/redact", methods=["POST"])
  def api_redact():
    if not request.is_json:
      return jsonify({"error": "Request body must be JSON"}), 400

    data = request.get_json()
    if not data or "text" not in data:
      return jsonify({"error": "text is required"}), 400

    text = data["text"]
    types = data.get("types", None)

    try:
      results = app.redactor.redact(text, types=types)
      return jsonify(results), 200
    except ValueError as err:
      return jsonify({"error": str(err)}), 400

  return app


if __name__ == "__main__":
  application = create_app()
  application.run(host="127.0.0.1", port=5000, debug=False)
