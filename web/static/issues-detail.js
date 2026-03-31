const issueDetailStatus = document.getElementById('issueDetailStatus');
const issueCore = document.getElementById('issueCore');
const issueEvidence = document.getElementById('issueEvidence');

function detailQuery() {
  const params = new URLSearchParams(window.location.search);
  return {
    domain: (params.get('domain') || '').trim(),
    runId: (params.get('run_id') || '').trim(),
    id: (params.get('id') || '').trim(),
  };
}

function setDetailStatus(message, cls = '') {
  issueDetailStatus.className = cls;
  issueDetailStatus.textContent = message;
}

function safeJson(value) {
  return JSON.stringify(value || null, null, 2);
}

function readField(obj, keys = []) {
  for (const key of keys) {
    const value = obj?.[key];
    if (value !== undefined && value !== null && String(value).trim()) return String(value).trim();
  }
  return '';
}

function deriveSeverity(issue) {
  const explicit = readField(issue, ['severity', 'issue_severity', 'level']).toLowerCase();
  if (explicit) return explicit;
  const confidence = Number(issue?.confidence || issue?.score || 0);
  if (!Number.isNaN(confidence)) {
    if (confidence >= 0.9) return 'high';
    if (confidence >= 0.7) return 'medium';
    if (confidence > 0) return 'low';
  }
  return '—';
}

async function loadIssueDetailPage() {
  const { domain, runId, id } = detailQuery();
  document.getElementById('detailBackToIssues').href = `/?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
  document.getElementById('detailOpenContexts').href = `/contexts?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
  document.getElementById('detailOpenPulls').href = `/pulls?${new URLSearchParams({ domain, run_id: runId }).toString()}`;

  setDetailStatus('Loading issue detail…');
  const response = await fetch(`/api/issues/detail?${new URLSearchParams({ domain, run_id: runId, id }).toString()}`);
  const payload = await safeReadPayload(response);
  if (!response.ok) {
    setDetailStatus(payload.error || `Failed to load issue detail (${response.status})`, 'error');
    return;
  }

  const issue = payload.issue || {};
  const dd = payload.drilldown || {};
  const missing = Array.isArray(dd.missing_refs) ? dd.missing_refs : [];
  const evidence = issue.evidence || {};

  issueCore.innerHTML = `
    <h2>What is wrong</h2>
    <p>${issue.message || 'No message available.'}</p>

    <h2>Where it appears</h2>
    <p>${evidence.url || 'URL unavailable'}</p>

    <h2>Language</h2>
    <p>${issue.language || 'Unknown'}</p>

    <h2>Severity</h2>
    <p>${deriveSeverity(issue)}</p>

    <h2>Issue metadata</h2>
    <ul>
      <li>ID: ${issue.id || ''}</li>
      <li>Category: ${issue.category || ''}</li>
      <li>State: ${issue.state || ''}</li>
    </ul>
  `;

  const warning = dd.partial
    ? `<p class="warning">Partial evidence: missing ${missing.join(', ') || 'some related references'}.</p>`
    : '';
  const screenshotHref = dd.screenshot_view_url || dd.screenshot_uri || '';
  const screenshot = screenshotHref
    ? `<p>Screenshot: <a href="${screenshotHref}" target="_blank" rel="noopener">${screenshotHref}</a></p>`
    : '<p>Screenshot: unavailable</p>';

  issueEvidence.innerHTML = `
    <h3>Evidence snapshot</h3>
    ${warning}
    ${screenshot}
    <h4>Page JSON</h4>
    <pre>${safeJson(dd.page)}</pre>
    <h4>Element JSON</h4>
    <pre>${safeJson(dd.element)}</pre>
  `;

  setDetailStatus('Issue detail loaded.', 'ok');
}

loadIssueDetailPage();
