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

function deriveSourceText(issue) {
  const evidence = issue?.evidence || {};
  return (
    readField(issue, ['source_text', 'en_text', 'source', 'original_text', 'sourceText', 'text_en']) ||
    readField(evidence, ['source_text', 'en_text', 'source', 'source_value', 'original_text', 'text_en']) ||
    '\u2014'
  );
}

function deriveTargetText(issue) {
  const evidence = issue?.evidence || {};
  return (
    readField(issue, ['target_text', 'translated_text', 'target', 'translation', 'targetText', 'text_target']) ||
    readField(evidence, ['target_text', 'translated_text', 'target', 'target_value', 'translation', 'text_target']) ||
    '\u2014'
  );
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

function isSafeLocalRelativeUrl(value) {
  const raw = String(value || '').trim();
  return raw.startsWith('/') && !raw.startsWith('//');
}

function replaceChildren(parent, children = []) {
  parent.textContent = '';
  for (const child of children) parent.appendChild(child);
}

function section(title, value) {
  const wrapper = document.createElement('div');
  const heading = document.createElement('h2');
  heading.textContent = title;
  const text = document.createElement('p');
  text.textContent = value;
  wrapper.append(heading, text);
  return wrapper;
}

async function loadIssueDetailPage() {
  const { domain, runId, id } = detailQuery();
  document.getElementById('detailBackToIssues').href = `/?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
  document.getElementById('detailOpenContexts').href = `/contexts?${new URLSearchParams({ domain, run_id: runId }).toString()}`;
  document.getElementById('detailOpenPulls').href = `/pulls?${new URLSearchParams({ domain, run_id: runId }).toString()}`;

  setDetailStatus('Loading issue detail\u2026');
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
  const language = readField(issue, ['language', 'target_language', 'lang']) || readField(evidence, ['language', 'target_language', 'lang']) || 'Unknown';
  const metadata = document.createElement('ul');
  for (const [label, value] of [
    ['ID', issue.id || ''],
    ['Category', issue.category || issue.type || ''],
    ['State', issue.state || ''],
  ]) {
    const item = document.createElement('li');
    item.textContent = `${label}: ${value}`;
    metadata.appendChild(item);
  }
  const metadataSection = document.createElement('div');
  const metadataHeading = document.createElement('h2');
  metadataHeading.textContent = 'Issue metadata';
  metadataSection.append(metadataHeading, metadata);
  replaceChildren(issueCore, [
    section('What is wrong', issue.message || issue.description || 'No message available.'),
    section('Where it appears', readField(evidence, ['url', 'page_url', 'source_url']) || 'URL unavailable'),
    section('Language', language),
    section('Source text (en)', deriveSourceText(issue)),
    section('Target text', deriveTargetText(issue)),
    metadataSection,
  ]);

  const evidenceNodes = [];
  const evidenceHeading = document.createElement('h3');
  evidenceHeading.textContent = 'Evidence snapshot';
  evidenceNodes.push(evidenceHeading);
  if (dd.partial) {
    const warning = document.createElement('p');
    warning.className = 'warning';
    warning.textContent = `Partial evidence: missing ${missing.join(', ') || 'some related references'}.`;
    evidenceNodes.push(warning);
  }
  const screenshotLine = document.createElement('p');
  screenshotLine.textContent = 'Screenshot: ';
  const screenshotHref = String(dd.screenshot_view_url || dd.screenshot_uri || '').trim();
  if (isSafeExternalHttpUrl(screenshotHref) || isSafeLocalRelativeUrl(screenshotHref)) {
    const screenshotLink = document.createElement('a');
    screenshotLink.href = screenshotHref;
    screenshotLink.target = '_blank';
    screenshotLink.rel = 'noopener';
    screenshotLink.textContent = screenshotHref;
    screenshotLine.appendChild(screenshotLink);
  } else {
    screenshotLine.appendChild(document.createTextNode('unavailable'));
  }
  evidenceNodes.push(screenshotLine);
  for (const [label, value] of [['Page JSON', dd.page], ['Element JSON', dd.element]]) {
    const subheading = document.createElement('h4');
    subheading.textContent = label;
    const pre = document.createElement('pre');
    pre.textContent = safeJson(value);
    evidenceNodes.push(subheading, pre);
  }
  replaceChildren(issueEvidence, evidenceNodes);

  setDetailStatus('Issue detail loaded.', 'ok');
}

loadIssueDetailPage();
