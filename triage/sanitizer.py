# triage/sanitizer.py
# Hides sensitive values like passwords and API keys from logs and env vars

import re

# Keys that contain these words will have their values hidden
SENSITIVE_KEYWORDS = ["password", "token", "api_key", "secret"]


def sanitize_value(key, value):
    """
    Check if a key is sensitive. If yes, return a masked value.
    Example: sanitize_value("DB_PASSWORD", "mypass123") -> "****** [REDACTED]"
    """
    key_lower = key.lower()
    for keyword in SENSITIVE_KEYWORDS:
        if keyword in key_lower:
            return "****** [REDACTED]"
    return value


def sanitize_env_vars(env_dict):
    """
    Go through all environment variables and hide sensitive ones.
    Input: {"DB_PASSWORD": "secret123", "PORT": "5432"}
    Output: {"DB_PASSWORD": "****** [REDACTED]", "PORT": "5432"}
    """
    if not isinstance(env_dict, dict):
        return env_dict

    result = {}
    for key, value in env_dict.items():
        result[key] = sanitize_value(str(key), str(value))
    return result


def sanitize_logs(log_lines):
    """
    Scan log lines and mask sensitive values like:
      password=mysecret  ->  password=****** [REDACTED]
      token=abc123       ->  token=****** [REDACTED]
    Returns a new list of sanitized log lines.
    """
    sanitized = []
    # Match patterns like: password=VALUE or api_key="VALUE"
    pattern = re.compile(
        r'(password|token|api_key|secret)\s*[=:]\s*["\']?(\S+)["\']?',
        re.IGNORECASE
    )

    for line in log_lines:
        # Replace the value part with redacted text
        clean_line = pattern.sub(r'\1=****** [REDACTED]', line)
        sanitized.append(clean_line)

    return sanitized
