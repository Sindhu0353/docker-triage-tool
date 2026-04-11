/* ================================================================
   Docker Failure Triage Tool — script.js
   
   All interactive logic for the triage page.
   Uses the native fetch() API only — no jQuery or external libraries.
   
   Flow:
   1. Page loads → call /api/containers → populate dropdown
   2. User clicks "Analyze Failure" → call /api/analyze/<id> → render results
   3. "Refresh Containers" button → re-fetch container list
================================================================ */

// ---- DOM References ---- //
// Grab all the elements we need once at the top.
const containerSelect = document.getElementById('container-select');
const analyzeBtn      = document.getElementById('analyze-btn');
const refreshBtn      = document.getElementById('refresh-btn');
const loadingEl       = document.getElementById('loading');
const resultsEl       = document.getElementById('results');
const emptyStateEl    = document.getElementById('empty-state');
const errorEl         = document.getElementById('error-message');
const errorTextEl     = document.getElementById('error-text');

// Result card bodies (where we inject HTML)
const detailsBody    = document.getElementById('container-details-body');
const classBody      = document.getElementById('classification-body');
const recBody        = document.getElementById('recommendations-body');
const evidenceBody   = document.getElementById('evidence-body');


/* ================================================================
   SECTION 1 — LOAD CONTAINERS
   Called on page load and when "Refresh Containers" is clicked.
   Fetches GET /api/containers and populates the <select> dropdown.
================================================================ */
function loadContainers() {
  // Reset UI state before fetching
  hideError();
  hideResults();
  emptyStateEl.classList.add('hidden');
  analyzeBtn.disabled = true;
  containerSelect.innerHTML = '<option value="">-- Loading containers... --</option>';

  fetch('/api/containers')
    .then(function(response) {
      // If the server returned an error status, throw so we hit .catch()
      if (!response.ok) {
        throw new Error('Server returned status ' + response.status);
      }
      return response.json();
    })
    .then(function(data) {
      // data.containers is a list of { id, name, status } objects
      var containers = data.containers || [];

      if (containers.length === 0) {
        // No containers found — show the empty state message
        containerSelect.innerHTML = '<option value="">-- No containers found --</option>';
        emptyStateEl.classList.remove('hidden');
        return;
      }

      // Build dropdown options from the container list
      containerSelect.innerHTML = '<option value="">-- Select a container --</option>';
      containers.forEach(function(c) {
        var option = document.createElement('option');
        option.value = c.id;                          // container ID used for analysis
        option.textContent = c.name + '  (' + c.status + ')'; // readable label
        containerSelect.appendChild(option);
      });

      // Enable the analyze button now that we have containers
      // (it becomes fully active once user selects an item)
      containerSelect.dispatchEvent(new Event('change'));
    })
    .catch(function(err) {
      // Docker might not be running, or the backend is down
      showError(
        'Could not load containers. Make sure Docker is running and the Flask server is started. ' +
        'Error: ' + err.message
      );
      containerSelect.innerHTML = '<option value="">-- Error loading containers --</option>';
    });
}

/* ================================================================
   SECTION 2 — ANALYZE FAILURE
   Called when "Analyze Failure" button is clicked.
   Fetches GET /api/analyze/<container_id> and renders all result cards.
================================================================ */
function analyzeContainer() {
  var containerId = containerSelect.value;

  // Guard: make sure a container is actually selected
  if (!containerId) {
    showError('Please select a container from the dropdown first.');
    return;
  }

  // Show loading, hide previous results and errors
  hideError();
  hideResults();
  showLoading();

  fetch('/api/analyze/' + encodeURIComponent(containerId))
    .then(function(response) {
      if (!response.ok) {
        throw new Error('Server returned status ' + response.status);
      }
      return response.json();
    })
    .then(function(data) {
      // Check for an application-level error message in the response
      if (data.error) {
        throw new Error(data.error);
      }

      // Render all four result sections with the returned data
      renderContainerDetails(data);
      renderClassification(data);
      renderRecommendations(data);
      renderEvidence(data.evidence_lines || []);

      // Show the results section
      hideLoading();
      showResults();
    })
    .catch(function(err) {
      hideLoading();
      showError('Analysis failed: ' + err.message);
    });
}


/* ================================================================
   SECTION 3 — RENDER HELPERS
   Each function fills a specific result card with HTML.
================================================================ */

/* ---- 3a. Container Details ---- */
function renderContainerDetails(data) {
  // data fields: container_name, status, exit_code, restart_count, cpu_usage, memory_usage
  var statusClass = getStatusClass(data.status || '');

  detailsBody.innerHTML =
    detailTile('Container', data.container_name || '—') +
    detailTile('Status',    '<span class="' + statusClass + '">' + (data.status || '—') + '</span>') +
    detailTile('Exit Code', data.exit_code !== undefined ? String(data.exit_code) : '—') +
    detailTile('Restarts',  data.restart_count !== undefined ? String(data.restart_count) : '—') +
    detailTile('CPU Usage', data.cpu_usage || '—') +
    detailTile('Memory',    data.memory_usage || '—');
}

/* Helper: build a single metric tile */
function detailTile(label, value) {
  return (
    '<div class="detail-item">' +
      '<span class="detail-label">' + escapeHtml(label) + '</span>' +
      '<span class="detail-value">' + value + '</span>' +
    '</div>'
  );
}

/* Helper: map status string to a CSS class for color */
function getStatusClass(status) {
  var s = status.toLowerCase();
  if (s.includes('running'))  return 'status-running';
  if (s.includes('exited'))   return 'status-exited';
  if (s.includes('stopped'))  return 'status-stopped';
  return 'status-other';
}


/* ---- 3b. Failure Classification ---- */
function renderClassification(data) {
  // data fields: classification.category, classification.confidence, classification.matched_keywords
  var cls = data.classification || {};
  var category = cls.category || 'Unknown';
  var confidence = cls.confidence || 'Low';
  var keywords = cls.matched_keywords || [];
  var tags, keywordsHtml;

  // Choose badge CSS class based on confidence level
  var badgeClass = 'badge-low';
  if (confidence === 'High')   badgeClass = 'badge-high';
  if (confidence === 'Medium') badgeClass = 'badge-medium';

  // Build keyword tags HTML
  keywordsHtml = '';
  if (keywords.length > 0) {
    tags = keywords.map(function(k) {
      return '<span class="keyword-tag">' + escapeHtml(k) + '</span>';
    }).join('');
    keywordsHtml =
      '<div class="keywords-section">' +
        '<div class="keywords-label">Matched keywords</div>' +
        '<div class="keywords-row">' + tags + '</div>' +
      '</div>';
  }

  classBody.innerHTML =
    '<div class="classification-category">' + escapeHtml(category) + '</div>' +
    '<div class="classification-confidence-row">' +
      '<span class="confidence-label">Confidence:</span>' +
      '<span class="badge ' + badgeClass + '">' + escapeHtml(confidence) + '</span>' +
    '</div>' +
    keywordsHtml;
}


/* ---- 3c. Recommendations ---- */
function renderRecommendations(data) {
  // data fields: recommendations.causes (list), recommendations.next_steps (list)
  var rec = data.recommendations || {};
  var causes = rec.causes || [];
  var steps  = rec.next_steps || [];

  // Build numbered causes list
  var causesItems = causes.map(function(c) {
    return '<li>' + escapeHtml(c) + '</li>';
  }).join('');

  // Build next steps list — highlight any `backtick` commands
  var stepsItems = steps.map(function(s) {
    // Convert `command` patterns into styled <code> elements
    var formatted = escapeHtml(s).replace(/`([^`]+)`/g, '<code class="cmd">$1</code>');
    return '<li>' + formatted + '</li>';
  }).join('');

  recBody.innerHTML =
    '<p class="rec-section-title">Top 3 Likely Causes</p>' +
    '<ol class="causes-list">' + causesItems + '</ol>' +
    '<p class="rec-section-title">Recommended Next Steps</p>' +
    '<ul class="steps-list">' + stepsItems + '</ul>';
}


/* ---- 3d. Evidence from Logs ---- */
function renderEvidence(lines) {
  // lines: array of up to 5 important log strings

  if (!lines || lines.length === 0) {
    // No evidence lines were matched
    evidenceBody.innerHTML = '<p class="no-evidence">No specific error lines were extracted from the logs.</p>';
    return;
  }

  // Render each line in a red-highlighted monospace box
  var html = lines.map(function(line) {
    return '<div class="evidence-line">' + escapeHtml(line) + '</div>';
  }).join('');

  evidenceBody.innerHTML = html;
}


/* ================================================================
   SECTION 4 — UI STATE HELPERS
   Small helper functions to show/hide UI elements cleanly.
================================================================ */

function showLoading()  { loadingEl.classList.remove('hidden'); }
function hideLoading()  { loadingEl.classList.add('hidden'); }
function showResults()  { resultsEl.classList.remove('hidden'); }
function hideResults()  { resultsEl.classList.add('hidden'); }

/* Show the error banner with a given message */
function showError(msg) {
  errorTextEl.textContent = msg;
  errorEl.classList.remove('hidden');
}

/* Hide the error banner */
function hideError() {
  errorEl.classList.add('hidden');
  errorTextEl.textContent = '';
}

/* ================================================================
   SECTION 5 — SECURITY HELPER
   Escape HTML special characters before injecting user data into
   the DOM. This prevents XSS if logs contain HTML-like content.
================================================================ */
function escapeHtml(str) {
  if (typeof str !== 'string') str = String(str);
  return str
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;')
    .replace(/'/g,  '&#39;');
}


/* ================================================================
   SECTION 6 — EVENT LISTENERS
================================================================ */

// Enable/disable Analyze button based on whether a container is selected
containerSelect.addEventListener('change', function() {
  analyzeBtn.disabled = !containerSelect.value;
});

// Analyze button click → run triage
analyzeBtn.addEventListener('click', analyzeContainer);

// Refresh button click → reload the container list
refreshBtn.addEventListener('click', loadContainers);


/* ================================================================
   SECTION 7 — PAGE INITIALIZATION
   Auto-load containers when the page first opens.
================================================================ */
document.addEventListener('DOMContentLoaded', function() {
  loadContainers();
});
