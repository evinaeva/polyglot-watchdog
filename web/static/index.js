const applyBtn = document.getElementById('applyIssueQuery');
const exportCsvBtn = document.getElementById('exportIssuesCsv');
const queryInput = document.getElementById('issueQuery');
const domainInput = document.getElementById('domainInput');
const persistedResultSelect = document.getElementById('persistedResultSelect');
const refreshPersistedResults = document.getElementById('refreshPersistedResults');
const runIdInput = document.getElementById('runIdInput');
const languageFilter = document.getElementById('languageFilter');
const severityFilter = document.getElementById('severityFilter');
const typeFilter = document.getElementById('typeFilter');
const stateFilter = document.getElementById('stateFilter');
const urlFilter = document.getElementById('urlFilter');
const domainFilter = document.getElementById('domainFilter');
const table = document.getElementById('issuesTable');
const tbody = table.querySelector('tbody');
const issueStatus = document.getElementById('issueStatus');
const issueCount = document.getElementById('issueCount');
const targetLanguageSummary = document.getElementById('targetLanguageSummary');
const targetLanguageHeader = document.getElementById('targetLanguageHeader');
const issuesBackToCheckLanguages = document.getElementById('issuesBackToCheckLanguages');
const workflowContextSummary = document.getElementById('workflowContextSummary');

const workflowContext = {
  domain: '',
  runId: '',
};
let persistedResults = [];
let persistedResultsDiagnostics = null;
const tallinnDateTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Europe/Tallinn',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

function queryParamsFromLocation() {
  const params = new URLSearchParams(window.location.search);
  return {
    domain: (params.get('domain') || '').trim(),
    runId: (params.get('run_id') || '').trim(),
  };
}

function setStatus(message, cls = '') {
  issueStatus.className = cls;
  issueStatus.textContent = message || '';
}

function clearIssuesView() {
  tbody.innerHTML = '';
  table.classList.add('hidden');
  issueCount.textContent = '';
  issueCount.classList.add('hidden');
  updateTargetLanguage([]);
}

function formatUtcTimestampForUi(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  const parts = tallinnDateTimeFormatter.formatToParts(parsed);
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${map.year}-${map.month}-${map.day} ${map.hour}:${map.minute}`;
}

function activeDomain() {
  return (domainInput.value || workflowContext.domain || '').trim();
}

function activeRunId() {
  return (runIdInput.value || workflowContext.runId || '').trim();
}

function selectedPersistedResult() {
  const runId = activeRunId();
  if (!runId) return null;
  return persistedResults.find((row) => String((row || {}).run_id || '').trim() === runId) || null;
}

function activeArtifactDomain() {
  const selected = selectedPersistedResult();
  const selectedDomain = String((selected || {}).domain || '').trim();
  return selectedDomain || activeDomain();
}

function buildParams() {
  return new URLSearchParams({
    domain: activeArtifactDomain(),
    run_id: activeRunId(),
    q: (queryInput.value || '').trim(),
    language: (languageFilter.value || '').trim(),
    severity: (severityFilter.value || '').trim(),
    type: (typeFilter.value || '').trim(),
    state: (stateFilter.value || '').trim(),
    url: (urlFilter.value || '').trim(),
    domain_filter: (domainFilter.value || '').trim(),
  });
}

function updateWorkflowSummary() {
  if (!workflowContextSummary) return;
  const domain = activeDomain();
  const runId = activeRunId();
  if (!domain && !runId) {
    workflowContextSummary.textContent = 'Workflow context: none (provide filters and click Apply).';
    return;
  }
  const contextParts = [];
  if (domain) contextParts.push(`domain: ${domain}`);
  if (runId) contextParts.push(`run: ${runId}`);
  const artifactDomain = activeArtifactDomain();
  if (runId && artifactDomain && artifactDomain !== domain) {
    contextParts.push(`artifact-domain: ${artifactDomain}`);
  }
  workflowContextSummary.textContent = `Workflow context: ${contextParts.join(' · ')}.`;
}

function syncDefaultsFromQuery() {
  const { domain, runId } = queryParamsFromLocation();
  workflowContext.domain = domain;
  workflowContext.runId = runId;
  domainInput.value = domain;
  runIdInput.value = '';

  const params = new URLSearchParams();
  if (workflowContext.domain) params.set('domain', workflowContext.domain);
  if (workflowContext.runId) params.set('run_id', workflowContext.runId);
  const hasWorkflowContext = Boolean(workflowContext.domain || workflowContext.runId);
  const basePath = hasWorkflowContext ? '/check-languages' : '/pulls';
  issuesBackToCheckLanguages.href = `${basePath}${params.toString() ? `?${params.toString()}` : ''}`;

  updateWorkflowSummary();
}

function resultOptionLabel(result) {
  const runId = String((result || {}).run_id || '').trim();
  const createdAt = formatUtcTimestampForUi(result.created_at);
  const displayLabel = String((result || {}).display_label || '').trim();
  if (createdAt && displayLabel && displayLabel !== runId) return `${createdAt} · ${displayLabel} · ${runId}`;
  if (createdAt) return `${createdAt} · ${runId}`;
  if (displayLabel && displayLabel !== runId) return `${displayLabel} · ${runId}`;
  return runId;
}

function renderPersistedResultOptions(selectedRunId = '') {
  if (!persistedResultSelect) return;
  persistedResultSelect.innerHTML = '';
  if (!persistedResults.length) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'No persisted results available';
    persistedResultSelect.appendChild(option);
    persistedResultSelect.disabled = true;
    return;
  }
  persistedResultSelect.disabled = false;
  const hasPreferred = selectedRunId && persistedResults.some((row) => String(row.run_id || '') === selectedRunId);
  const preferredRunId = hasPreferred ? selectedRunId : String((persistedResults[0] || {}).run_id || '').trim();
  if (selectedRunId && !hasPreferred) {
    const option = document.createElement('option');
    option.value = selectedRunId;
    option.textContent = `${selectedRunId} · current selection`;
    option.selected = true;
    persistedResultSelect.appendChild(option);
  }
  for (const result of persistedResults) {
    const runId = String(result.run_id || '').trim();
    if (!runId) continue;
    const option = document.createElement('option');
    option.value = runId;
    option.textContent = resultOptionLabel(result);
    option.selected = !selectedRunId || hasPreferred ? runId === preferredRunId : false;
    persistedResultSelect.appendChild(option);
  }
  if (selectedRunId && !hasPreferred) {
    runIdInput.value = selectedRunId;
    return;
  }
  if (preferredRunId) runIdInput.value = preferredRunId;
}

async function loadPersistedResults(preferredRunId = '') {
  const domain = activeDomain();
  persistedResults = [];
  persistedResultsDiagnostics = null;
  renderPersistedResultOptions('');
  if (!domain) return;
  const response = await fetch(`/api/issues/results?${new URLSearchParams({ domain }).toString()}`);
  const payload = await safeReadPayload(response);
  if (!response.ok) throw new Error(payload.error || `Failed to load persisted results (${response.status})`);
  const rows = Array.isArray(payload.results) ? payload.results : [];
  persistedResults = rows;
  persistedResultsDiagnostics = payload.diagnostics && typeof payload.diagnostics === 'object' ? payload.diagnostics : null;
  renderPersistedResultOptions(preferredRunId);
}

function noPersistedResultsMessage() {
  if (!persistedResultsDiagnostics) return 'No persisted issue results found for this domain.';
  const searched = Array.isArray(persistedResultsDiagnostics.searched_domains)
    ? persistedResultsDiagnostics.searched_domains.filter((row) => String(row || '').trim())
    : [];
  if (!searched.length) return 'No persisted issue results found for this domain.';
  return `No persisted issue results found. Searched domains: ${searched.join(', ')}.`;
}

function issueLabel(issue) {
  return issue.message || issue.category || issue.id || '';
}

function readField(obj, keys = []) {
  for (const key of keys) {
    const value = obj?.[key];
    if (value !== undefined && value !== null && String(value).trim()) return String(value).trim();
  }
  return '';
}

function deriveSeverity(issue) {
  const explicit = readField(issue, ['severity', 'issue_severity', 'level', 'priority', 'risk_level']).toLowerCase();
  if (explicit) return explicit;
  const confidence = Number(issue?.confidence || issue?.score || 0);
  if (!Number.isNaN(confidence)) {
    if (confidence >= 0.9) return 'high';
    if (confidence >= 0.7) return 'medium';
    if (confidence > 0) return 'low';
  }
  return '—';
}

function isSafeExternalHttpUrl(value) {
  const raw = String(value || '').trim();
  if (!raw) return false;
  try {
    const parsed = new URL(raw);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch (_) {
    return false;
  }
}

function deriveSourceText(issue) {
  const evidence = issue?.evidence || {};
  return (
    readField(issue, ['source_text', 'en_text', 'source', 'original_text', 'sourceText', 'text_en']) ||
    readField(evidence, ['source_text', 'en_text', 'source', 'source_value', 'original_text', 'text_en']) ||
    '—'
  );
}

function deriveTargetText(issue) {
  const evidence = issue?.evidence || {};
  return (
    readField(issue, ['target_text', 'translated_text', 'target', 'translation', 'targetText', 'text_target']) ||
    readField(evidence, ['target_text', 'translated_text', 'target', 'target_value', 'translation', 'text_target']) ||
    '—'
  );
}

function deriveIssueLanguage(issue) {
  const evidence = issue?.evidence || {};
  return readField(issue, ['language', 'target_language', 'lang']) || readField(evidence, ['language', 'target_language', 'lang']);
}

function deterministicTargetLanguageFromIssues(issues = []) {
  const counts = new Map();
  for (const row of issues) {
    const language = deriveIssueLanguage(row).toLowerCase();
    if (!language) continue;
    counts.set(language, (counts.get(language) || 0) + 1);
  }
  if (!counts.size) return '';
  return [...counts.entries()]
    .sort((a, b) => {
      if (b[1] !== a[1]) return b[1] - a[1];
      return a[0].localeCompare(b[0]);
    })[0][0];
}

function updateTargetLanguage(issues = [], explicitTargetLanguage = '') {
  const explicit = String(explicitTargetLanguage || '').trim().toLowerCase();
  const preferred = (languageFilter?.value || '').trim().toLowerCase();
  const fallbackFromIssues = deterministicTargetLanguageFromIssues(issues);
  const candidates = explicit ? [explicit] : (preferred ? [preferred] : (fallbackFromIssues ? [fallbackFromIssues] : []));
  const selected = candidates[0] || 'target';
  if (targetLanguageHeader) targetLanguageHeader.textContent = selected;
  if (targetLanguageSummary) targetLanguageSummary.textContent = selected === 'target' ? 'Target language: —' : `Target language: ${selected.toUpperCase()}`;
}

async function loadIssues() {
  updateWorkflowSummary();
  setStatus('Loading…');
  issueCount.classList.add('hidden');
  tbody.innerHTML = '';
  const response = await fetch(`/api/issues?${buildParams().toString()}`);
  const payload = await safeReadPayload(response);
  if (response.status === 404 && payload.status === 'not_ready') {
    table.classList.add('hidden');
    setStatus('Not ready: issues.json artifact is missing. Run phase 6 or wait for pipeline.', 'warning');
    return;
  }
  if (!response.ok) {
    table.classList.add('hidden');
    setStatus(payload.error || `Issues query failed (${response.status})`, 'error');
    return;
  }
  const issues = payload.issues || [];
  updateTargetLanguage(issues, payload.target_language || '');
  issueCount.textContent = `Count: ${payload.count || 0}`;
  issueCount.classList.remove('hidden');
  if (!issues.length) {
    table.classList.add('hidden');
    setStatus('No issues found for current filters.', 'empty');
    return;
  }
  setStatus('Issues loaded.', 'ok');
  for (const issue of issues) {
    const tr = document.createElement('tr');
    const evidenceUrl = readField(issue?.evidence || {}, ['url', 'page_url', 'source_url']);
    const detailHref = `/issues/detail?${new URLSearchParams({
      domain: activeArtifactDomain(),
      run_id: activeRunId(),
      id: String(issue.id || ''),
    }).toString()}`;

    const sourceTd = document.createElement('td');
    sourceTd.textContent = deriveSourceText(issue);
    tr.appendChild(sourceTd);

    const targetTd = document.createElement('td');
    targetTd.textContent = deriveTargetText(issue);
    tr.appendChild(targetTd);

    const issueTd = document.createElement('td');
    issueTd.textContent = issueLabel(issue);
    tr.appendChild(issueTd);

    const severityTd = document.createElement('td');
    severityTd.textContent = deriveSeverity(issue);
    tr.appendChild(severityTd);

    const linksTd = document.createElement('td');
    const detailLink = document.createElement('a');
    detailLink.href = detailHref;
    detailLink.textContent = 'Open details';
    linksTd.appendChild(detailLink);
    if (isSafeExternalHttpUrl(evidenceUrl)) {
      const separator = document.createElement('span');
      separator.textContent = ' · ';
      linksTd.appendChild(separator);
      const urlLink = document.createElement('a');
      urlLink.href = evidenceUrl;
      urlLink.target = '_blank';
      urlLink.rel = 'noopener';
      urlLink.textContent = 'url';
      linksTd.appendChild(urlLink);
    }
    tr.appendChild(linksTd);

    tbody.appendChild(tr);
  }
  table.classList.remove('hidden');
}

applyBtn.addEventListener('click', () => {
  const params = buildParams();
  window.history.replaceState({}, '', `/?${params.toString()}`);
  updateWorkflowSummary();
  loadIssues().catch((err) => setStatus(err.message, 'error'));
});

if (runIdInput) {
  runIdInput.addEventListener('input', () => {
    updateWorkflowSummary();
  });
}

if (domainInput) {
  domainInput.addEventListener('input', () => {
    updateWorkflowSummary();
    const preferredRunId = String(workflowContext.runId || '').trim();
    loadPersistedResults(preferredRunId)
      .then(() => {
        if (!persistedResults.length) {
          clearIssuesView();
          setStatus(noPersistedResultsMessage(), 'empty');
          return;
        }
        loadIssues().catch((err) => setStatus(err.message, 'error'));
      })
      .catch((err) => setStatus(err.message, 'error'));
  });
}

if (persistedResultSelect) {
  persistedResultSelect.addEventListener('change', () => {
    runIdInput.value = String(persistedResultSelect.value || '').trim();
    updateWorkflowSummary();
    const params = buildParams();
    window.history.replaceState({}, '', `/?${params.toString()}`);
    loadIssues().catch((err) => setStatus(err.message, 'error'));
  });
}

if (refreshPersistedResults) {
  refreshPersistedResults.addEventListener('click', () => {
    const previousRunId = activeRunId();
    setStatus('Loading persisted results…');
    loadPersistedResults(previousRunId)
      .then(() => {
        if (!persistedResults.length) {
          clearIssuesView();
          setStatus(noPersistedResultsMessage(), 'empty');
          return;
        }
        const nextRunId = activeRunId();
        if (nextRunId !== previousRunId) {
          loadIssues().catch((err) => setStatus(err.message, 'error'));
          return;
        }
        setStatus('Persisted issue results loaded.', 'ok');
      })
      .catch((err) => setStatus(err.message, 'error'));
  });
}

if (exportCsvBtn) {
  exportCsvBtn.addEventListener('click', async () => {
    const params = buildParams();
    params.set('format', 'csv');
    const response = await fetch(`/api/issues/export?${params.toString()}`);
    if (!response.ok) {
      const payload = await safeReadPayload(response);
      setStatus(payload.error || `Export failed (${response.status})`, 'error');
      return;
    }
    const text = await response.text();
    const blob = new Blob([text], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'issues-export.csv';
    a.click();
    URL.revokeObjectURL(url);
  });
}

syncDefaultsFromQuery();
loadPersistedResults()
  .then(() => {
    if (activeDomain() && activeRunId()) return loadIssues();
    if (activeDomain() && !persistedResults.length) {
      clearIssuesView();
      setStatus(noPersistedResultsMessage(), 'empty');
    }
    return null;
  })
  .catch((err) => setStatus(err.message, 'error'));
