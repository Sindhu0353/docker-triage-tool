# triage/recommender.py
# Gives advice based on what type of error was found

# All recommendations stored in a simple dictionary
RECOMMENDATIONS = {
    "Config Error": {
        "causes": [
            "Missing environment variable in .env or compose file",
            "Wrong port number in docker-compose.yml",
            "Invalid docker-compose.yml syntax",
        ],
        "next_steps": [
            "Check your .env file for missing variables",
            "Verify port mapping in docker-compose.yml",
            "Run: docker compose config",
        ],
    },
    "Network Error": {
        "causes": [
            "Wrong service hostname in the connection string",
            "Container is not in the same Docker network",
            "Target service is not running",
        ],
        "next_steps": [
            "Check service names in your compose file match your connection strings",
            "Run: docker network inspect <network_name>",
            "Ping the service from inside the container: docker exec -it <name> ping <service>",
        ],
    },
    "Dependency Readiness": {
        "causes": [
            "Database started too slowly — app connected before it was ready",
            "Database migrations were not executed",
            "depends_on in compose file is incomplete or missing",
        ],
        "next_steps": [
            "Add a wait-for-db script (e.g. wait-for-it.sh) before starting your app",
            "Run migration command manually: docker exec -it <app> python manage.py migrate",
            "Add healthcheck in docker-compose.yml so depends_on waits properly",
        ],
    },
    "Unknown": {
        "causes": [
            "Unexpected application error",
            "Missing dependencies or packages",
            "Misconfiguration in Dockerfile or compose file",
        ],
        "next_steps": [
            "Check container logs with: docker logs <container_name>",
            "Verify all required services are running: docker ps",
            "Check the Dockerfile for missing steps or wrong base image",
        ],
    },
}


def get_recommendations(category):
    """
    Return causes and next steps for a given error category.

    Input: "Network Error"
    Output: {
        "causes": [...],
        "next_steps": [...]
    }
    """
    # Default to "Unknown" if category is not recognized
    return RECOMMENDATIONS.get(category, RECOMMENDATIONS["Unknown"])
