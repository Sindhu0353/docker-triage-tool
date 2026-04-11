# triage/stats.py
# Handles Docker container stats and docker-compose.yml parsing.
# Separated from collector.py to keep each file under 150 lines.

import docker
import os
import yaml
from typing import Any
from triage.sanitizer import sanitize_env_vars


def _get_client():
    """Try to connect to Docker. Returns None if Docker is not available."""
    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception:
        return None


def get_container_stats(container_id):
    """
    Get CPU and memory usage for a container.

    Returns: {"cpu_percent": "12%", "memory_usage": "120 MB"}
    If Docker is unavailable or container is stopped, returns default values.
    """
    client = _get_client()

    if client is None or container_id.startswith("sample"):
        return {"cpu_percent": "N/A", "memory_usage": "N/A"}

    try:
        container = client.containers.get(container_id)

        # Only running containers have stats
        if container.status != "running":
            return {"cpu_percent": "0%", "memory_usage": "0 MB"}

        # stream=False gets one snapshot of stats (faster than streaming)
        # We use Any here because the Docker SDK type stubs incorrectly
        # type stats(stream=False) as Iterator instead of dict.
        # At runtime this always returns a plain dictionary.
        stats: Any = container.stats(stream=False)

        # Calculate CPU percentage
        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                    stats["precpu_stats"]["cpu_usage"]["total_usage"]
        system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                       stats["precpu_stats"]["system_cpu_usage"]
        num_cpus = stats["cpu_stats"].get("online_cpus", 1)
        cpu_percent = 0.0
        if system_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0

        # Calculate memory usage in MB
        mem_bytes = stats["memory_stats"].get("usage", 0)
        mem_mb = round(mem_bytes / (1024 * 1024), 1)

        return {
            "cpu_percent": f"{round(cpu_percent, 1)}%",
            "memory_usage": f"{mem_mb} MB",
        }
    except Exception as e:
        print(f"Stats error: {e}")
        return {"cpu_percent": "N/A", "memory_usage": "N/A"}


def parse_compose_file(path="docker-compose.yml"):
    """
    Read a docker-compose.yml file and return service info.

    Returns dict with services, each containing ports and env vars.
    Env var values are sanitized to hide secrets.
    """
    if not os.path.exists(path):
        return {"error": "docker-compose.yml not found in current directory"}

    try:
        with open(path, "r") as f:
            compose = yaml.safe_load(f)

        services = compose.get("services", {})
        result = {}

        for service_name, service_config in services.items():
            # Get port mappings (may be a list like ["8080:80"])
            ports = service_config.get("ports", [])

            # Get environment variables (can be a list or a dict)
            env_raw = service_config.get("environment", {})
            env_dict = {}

            if isinstance(env_raw, list):
                # Convert ["KEY=value", "KEY2=value2"] to a dict
                for item in env_raw:
                    if "=" in item:
                        k, v = item.split("=", 1)
                        env_dict[k] = v
                    else:
                        env_dict[item] = ""
            elif isinstance(env_raw, dict):
                env_dict = env_raw

            # Sanitize env vars to hide passwords and tokens
            safe_env = sanitize_env_vars(env_dict)

            result[service_name] = {
                "ports": ports,
                "environment": safe_env,
            }

        return result

    except yaml.YAMLError as e:
        return {"error": f"YAML parsing error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}
