# triage/classifier.py
# Looks at log lines and figures out what type of error is happening

# Keywords for each error category
CONFIG_KEYWORDS = [
    "KeyError",
    "Missing environment variable",
    "invalid port",
    "YAML error",
    "FileNotFoundError",
    "invalid compose syntax",
]

NETWORK_KEYWORDS = [
    "Connection refused",
    "Name or service not known",
    "Temporary failure in name resolution",
    "host not found",
    "Timeout",
]

DEPENDENCY_KEYWORDS = [
    "database system is starting up",
    "could not connect to postgres",
    "waiting for mysql",
    "migration failed",
    "relation does not exist",
]


def _count_matches(log_text, keywords):
    """
    Count how many keywords from the list appear in the log text.
    Returns a list of matched keywords.
    """
    matched = []
    log_lower = log_text.lower()
    for keyword in keywords:
        if keyword.lower() in log_lower:
            matched.append(keyword)
    return matched


def classify_logs(log_lines):
    """
    Scan all log lines and detect the most likely error category.

    Returns a dict like:
    {
        "category": "Network Error",
        "confidence": "High",
        "matched_keywords": ["Connection refused", "host not found"]
    }
    """
    # Join all log lines into one big string for easy searching
    full_log = "\n".join(log_lines)

    # Count matches for each category
    config_matches = _count_matches(full_log, CONFIG_KEYWORDS)
    network_matches = _count_matches(full_log, NETWORK_KEYWORDS)
    dependency_matches = _count_matches(full_log, DEPENDENCY_KEYWORDS)

    # Build a list of (category, matches) sorted by number of matches (highest first)
    candidates = [
        ("Config Error", config_matches),
        ("Network Error", network_matches),
        ("Dependency Readiness", dependency_matches),
    ]
    candidates.sort(key=lambda x: len(x[1]), reverse=True)

    best_category, best_matches = candidates[0]

    # If no keywords matched at all, it's unknown
    if len(best_matches) == 0:
        return {
            "category": "Unknown",
            "confidence": "Low",
            "matched_keywords": [],
        }

    # Determine confidence based on how many keywords matched
    match_count = len(best_matches)
    if match_count >= 3:
        confidence = "High"
    elif match_count >= 1:
        confidence = "Medium"
    else:
        confidence = "Low"

    return {
        "category": best_category,
        "confidence": confidence,
        "matched_keywords": best_matches,
    }
