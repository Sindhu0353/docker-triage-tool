# triage/collector.py
# Connects to Docker and collects container info and logs.
# Stats and compose parsing are in triage/stats.py to keep this file short.

import docker
import os
from triage.sanitizer import sanitize_logs
from triage.stats import get_container_stats, parse_compose_file  # noqa: F401 — re-exported for app.py


# Create Docker client — will fail gracefully if Docker is not running
def _get_client():
    """Try to connect to Docker. Returns None if Docker is not available."""
    try:
        client = docker.from_env()
        client.ping()  # Test the connection
        return client
    except Exception:
        return None


def get_containers():
    """
    Get a list of all running and stopped containers.

    Returns a list of dicts:
    [{"id": "abc123", "name": "web-app", "status": "running", "exit_code": 0, "restart_count": 0}]

    If Docker is not available, returns sample containers from sample_logs/.
    """
    client = _get_client()

    if client is None:
        # Docker is not running — return sample containers for testing
        return _get_sample_containers()

    containers = []
    try:
        # Get all containers (including stopped ones)
        for c in client.containers.list(all=True):
            # Get exit code and restart count from container attributes
            exit_code = c.attrs.get("State", {}).get("ExitCode", 0)
            restart_count = c.attrs.get("RestartCount", 0)

            containers.append({
                "id": c.short_id,
                "name": c.name,
                "status": c.status,
                "exit_code": exit_code,
                "restart_count": restart_count,
            })
    except Exception as e:
        print(f"Error listing containers: {e}")

    return containers


def _get_sample_containers():
    """
    Return fake containers based on sample log files.
    Used when Docker daemon is not running — great for classroom testing!
    """
    sample_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_logs")
    samples = []

    # Map each sample log file to a fake container
    sample_map = {
        "db_error.txt":      {"id": "sample01", "name": "sample-db-app",      "status": "exited",  "exit_code": 1, "restart_count": 3},
        "network_error.txt": {"id": "sample02", "name": "sample-web-app",     "status": "exited",  "exit_code": 1, "restart_count": 5},
        "env_missing.txt":   {"id": "sample03", "name": "sample-config-app",  "status": "exited",  "exit_code": 2, "restart_count": 2},
        "success_app.txt":   {"id": "sample04", "name": "sample-success-app", "status": "running", "exit_code": 0, "restart_count": 0},
    }

    for filename, info in sample_map.items():
        filepath = os.path.join(sample_dir, filename)
        if os.path.exists(filepath):
            samples.append(info)

    return samples


def get_container_details(container_id):
    """
    Get detailed info about a single container including logs.

    Returns dict with: name, status, exit_code, restart_count, logs (list of strings)
    """
    client = _get_client()

    # Handle sample containers
    if container_id.startswith("sample"):
        return _get_sample_details(container_id)

    if client is None:
        return {"error": "Docker is not available"}

    try:
        container = client.containers.get(container_id)
        exit_code = container.attrs.get("State", {}).get("ExitCode", 0)
        restart_count = container.attrs.get("RestartCount", 0)

        # Get last 100 log lines as a list
        raw_logs = container.logs(tail=100).decode("utf-8", errors="replace")
        log_lines = raw_logs.splitlines()

        # Sanitize logs to hide any sensitive values
        safe_logs = sanitize_logs(log_lines)

        return {
            "name": container.name,
            "status": container.status,
            "exit_code": exit_code,
            "restart_count": restart_count,
            "logs": safe_logs,
        }
    except Exception as e:
        return {"error": str(e)}


def _get_sample_details(container_id):
    """Load details and logs from a sample log file."""
    sample_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_logs")

    id_to_file = {
        "sample01": ("sample-db-app",      "db_error.txt",      "exited",  1, 3),
        "sample02": ("sample-web-app",     "network_error.txt", "exited",  1, 5),
        "sample03": ("sample-config-app",  "env_missing.txt",   "exited",  2, 2),
        "sample04": ("sample-success-app", "success_app.txt",   "running", 0, 0),
    }

    if container_id not in id_to_file:
        return {"error": "Sample container not found"}

    name, filename, status, exit_code, restart_count = id_to_file[container_id]
    filepath = os.path.join(sample_dir, filename)

    log_lines = []
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            log_lines = f.read().splitlines()

    return {
        "name": name,
        "status": status,
        "exit_code": exit_code,
        "restart_count": restart_count,
        "logs": sanitize_logs(log_lines),
    }
