# app.py
# Main Flask server — runs on port 5000
# Start with: python app.py

from flask import Flask, jsonify, render_template
from triage.collector import get_containers, get_container_details, get_container_stats, parse_compose_file
from triage.classifier import classify_logs
from triage.recommender import get_recommendations

app = Flask(__name__)

# Keywords that indicate an important/relevant log line
EVIDENCE_KEYWORDS = [
    "error", "fatal", "warn", "exception", "traceback",
    "refused", "failed", "not found", "timeout",
    "could not", "missing", "invalid",
]


def extract_evidence(log_lines):
    """
    Find the most useful log lines — ones that contain error/warning keywords.
    Returns a maximum of 5 lines to keep the UI clean.
    """
    evidence = []
    for line in log_lines:
        line_lower = line.lower()
        # Check if this line contains any important keyword
        if any(keyword in line_lower for keyword in EVIDENCE_KEYWORDS):
            evidence.append(line)
            if len(evidence) >= 5:  # Stop at 5 lines
                break
    return evidence


@app.route("/")
def index():
    """Serve the main HTML page."""
    return render_template("index.html")


@app.route("/api/containers")
def api_containers():
    """
    GET /api/containers
    Returns a list of all running and stopped containers.
    Falls back to sample containers if Docker is not running.
    """
    containers = get_containers()
    # Wrap in an object — the frontend reads data.containers
    return jsonify({"containers": containers})


@app.route("/api/analyze/<container_id>")
def api_analyze(container_id):
    """
    GET /api/analyze/<container_id>
    Full triage pipeline:
    1. Collect container details and logs
    2. Get CPU/memory stats
    3. Sanitize logs (done inside collector)
    4. Classify the failure
    5. Get recommendations
    6. Extract key evidence lines
    Returns everything as JSON.
    """
    # Step 1: Get container details and logs
    details = get_container_details(container_id)
    if "error" in details:
        return jsonify({"error": details["error"]}), 404

    # Step 2: Get resource usage stats
    stats = get_container_stats(container_id)

    log_lines = details.get("logs", [])

    # Step 3: Classify the failure based on log content
    classification = classify_logs(log_lines)

    # Step 4: Get recommended causes and next steps
    recommendations = get_recommendations(classification["category"])

    # Step 5: Pull out the most important log lines as evidence
    evidence = extract_evidence(log_lines)

    # Build the full response — field names must match what script.js expects:
    # container_name, status, exit_code, restart_count, cpu_usage, memory_usage,
    # classification, recommendations, evidence_lines
    return jsonify({
        "container_name":  details.get("name", "unknown"),
        "status":          details.get("status", "unknown"),
        "exit_code":       details.get("exit_code", 0),
        "restart_count":   details.get("restart_count", 0),
        "cpu_usage":       stats.get("cpu_percent", "N/A"),
        "memory_usage":    stats.get("memory_usage", "N/A"),
        "classification":  classification,
        "recommendations": recommendations,
        "evidence_lines":  evidence,
    })


@app.route("/api/compose")
def api_compose():
    """
    GET /api/compose
    Reads docker-compose.yml from the current directory.
    Returns service names, port mappings, and sanitized environment variables.
    """
    services = parse_compose_file("docker-compose.yml")
    return jsonify(services)


if __name__ == "__main__":
    print("Starting Docker Failure Triage Tool...")
    print("Open your browser at: http://localhost:5000")
    app.run(debug=True, port=5000)
