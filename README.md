# Docker Failure Triage Tool

A beginner-friendly web tool that helps students quickly figure out **why** their Docker or Docker Compose project is failing.

---

## What This Tool Does

When your Docker container crashes or keeps restarting, reading raw logs can be overwhelming. This tool:

1. **Collects** logs and system info from your Docker containers
2. **Classifies** the failure into one of three categories (Config Error, Network Error, Dependency Readiness)
3. **Recommends** the top 3 likely causes and specific next steps to fix it
4. **Highlights** the most important evidence lines from the logs

You get a clear, readable summary instead of scrolling through hundreds of log lines.

---

## Requirements

- **Python 3.8 or newer** — [Download here](https://www.python.org/downloads/)
- **pip** — comes with Python
- **Docker Desktop** *(optional)* — if Docker is not running, the tool automatically uses sample log files so you can still explore the features

---

## Setup Steps

Follow these steps in order. All commands are run in a terminal (PowerShell or Command Prompt on Windows).

**1. Clone or download this project**
```
git clone <repo-url>
cd DockerTriageTool
```
Or download the ZIP from GitHub and extract it.

**2. Open the project folder in VS Code**
```
code .
```

**3. Open a terminal inside VS Code**
Press `` Ctrl+` `` or go to **Terminal → New Terminal**.

**4. Install dependencies**
```
pip install -r requirements.txt
```

**5. Start the app**
```
python app.py
```

**6. Open your browser**
Go to: [http://localhost:5000](http://localhost:5000)

---

## Testing Without Docker

If Docker Desktop is not installed or not running, the tool will **automatically switch to demo mode** and load sample containers from the `sample_logs/` folder. This lets you explore all the features without needing a real Docker setup.

The three sample containers are:
| Container Name | Simulated Error |
|---|---|
| `demo-db-error` | Database not ready / migration failure |
| `demo-network-error` | DNS failure / connection refused |
| `demo-env-missing` | Missing environment variables / config errors |

---

## Folder Structure

```
DockerTriageTool/
│
├── app.py               ← Main Flask server. Starts the web app and handles API routes.
├── requirements.txt     ← List of Python packages to install.
│
├── static/
│   ├── style.css        ← All the visual styling (colours, layout, cards).
│   └── script.js        ← Frontend logic: fetches data from the server and updates the page.
│
├── templates/
│   └── index.html       ← The single HTML page the user sees in their browser.
│
├── triage/
│   ├── collector.py     ← Gathers data from Docker (logs, stats, exit codes).
│   ├── classifier.py    ← Reads the logs and decides what kind of error it is.
│   ├── recommender.py   ← Gives advice based on the error category.
│   └── sanitizer.py     ← Hides sensitive values like passwords and API keys.
│
├── sample_logs/
│   ├── db_error.txt     ← Sample logs for a database connection failure.
│   ├── network_error.txt ← Sample logs for a network/DNS failure.
│   └── env_missing.txt  ← Sample logs for missing environment variables.
│
├── sample-docker-compose.yml ← A working example compose file with comments.
└── README.md            ← This file.
```

---

## How It Works

The tool follows a simple four-step pipeline:

```
1. COLLECT  →  2. SANITIZE  →  3. CLASSIFY  →  4. RECOMMEND
```

**1. Collect** (`collector.py`)
Connects to Docker and reads the last 100 log lines, the exit code, restart count, and CPU/memory usage for the selected container.

**2. Sanitize** (`sanitizer.py`)
Scans environment variables and log lines for sensitive values (passwords, tokens, API keys) and replaces them with `******` before displaying anything on screen.

**3. Classify** (`classifier.py`)
Searches the log lines for known error keywords. Based on what it finds, it assigns a category (Config Error, Network Error, or Dependency Readiness) and a confidence level (High / Medium / Low).

**4. Recommend** (`recommender.py`)
Looks up a pre-written list of likely causes and next steps for the detected category and returns the top 3 suggestions.

---

## Understanding the Failure Categories

### ⚙️ Config Error
**What it means:** The container couldn't start because something in its configuration is wrong.

**Common examples:**
- A required environment variable (like `DATABASE_URL` or `SECRET_KEY`) was not set
- A port number is invalid or already in use
- The `docker-compose.yml` file has a YAML syntax mistake
- A file or volume the container expected is missing

**Quick fix:** Check your `.env` file. Run `docker compose config` to validate your compose file.

---

### 🌐 Network Error
**What it means:** The container started successfully but can't reach another service (like a database or API) over the network.

**Common examples:**
- The hostname in your code (`db`, `api-service`) doesn't match the service name in `docker-compose.yml`
- Two services are in different Docker networks and can't see each other
- The target service hasn't started yet or crashed

**Quick fix:** Make sure all services that need to talk to each other are listed under the same `networks:` section in your compose file. Check that service names match exactly.

---

### ⏳ Dependency Readiness Error
**What it means:** Your app started before its dependency (like a database) was fully ready to accept connections. Docker's `depends_on:` only waits for the container to *start*, not for the service inside to be *ready*.

**Common examples:**
- The web app tries to connect to Postgres while Postgres is still initialising
- Database migrations run before the tables exist
- A message queue or cache isn't ready when the app boots

**Quick fix:** Add a wait-for-db script or a `healthcheck:` to your compose file so your app retries the connection. Run your migrations separately after the database is ready.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'flask'` | Run `pip install -r requirements.txt` again |
| `Address already in use` on port 5000 | Change the port in `app.py` or stop the other program using port 5000 |
| No containers showing in dropdown | Make sure Docker Desktop is running, or use the demo sample containers |
| `docker: command not found` | Install Docker Desktop and restart VS Code |
