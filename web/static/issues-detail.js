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

async function loadIssueDetailPage() {
  const { domain, runId, id } = detailQuery();
  document.getElementById('detailBackToIssues').href = `/?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
  document.getElementById('detailOpenContexts').href = `/contexts?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
  document.getElementById('detailOpenPulls').href = `/pulls?${new URLSearchParams({ domain, run_id: runId }).toString()}`;

  const response = await fetch(`/api/issues/detail?${new URLSearchParams({ domain, run_id: runId, id }).toString()}`);
  const payload = await safeReadPayload(response);
  if (!response.ok) {
    setDetailStatus(payload.error || `Failed to load issue detail (${response.status})`, 'error');
    return;
  }
  const issue = payload.issue || {};
  const dd = payload.drilldown || {};
  const missing = Array.isArray(dd.missing_refs) ? dd.missing_refs : [];
  issueCore.innerHTML = `<h2>${issue.id || ''} · ${issue.category || ''}</h2><ul><li>Severity: ${issue.severity || ''}</li><li>Language: ${issue.language || ''}</li><li>State: ${issue.state || ''}</li><li>Message: ${issue.message || ''}</li></ul>`;
  const warning = dd.partial ? `<p class="warning">Partial evidence: missing ${missing.join(', ') || 'some related references'}.</p>` : '';
  const screenshot = dd.screenshot_uri ? `<p>Screenshot: <a href="${dd.screenshot_uri}" target="_blank" rel="noopener">${dd.screenshot_uri}</a></p>` : '<p>Screenshot: unavailable</p>';
  issueEvidence.innerHTML = `<h3>Evidence</h3>${warning}<p>URL: ${(issue.evidence || {}).url || ''}</p>${screenshot}<h4>Page</h4><pre>${safeJson(dd.page)}</pre><h4>Element</h4><pre>${safeJson(dd.element)}</pre>`;
  setDetailStatus('Issue detail loaded.', 'ok');
}

loadIssueDetailPage();
