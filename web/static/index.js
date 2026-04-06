const applyBtn = document.getElementById('applyIssueQuery');
const exportCsvBtn = document.getElementById('exportIssuesCsv');
const queryInput = document.getElementById('issueQuery');
const domainSelect = document.getElementById('domainSelect');
const persistedResultSelect = document.getElementById('persistedResultSelect');
const refreshPersistedResults = document.getElementById('refreshPersistedResults');
const runIdInput = document.getElementById('runIdInput');
const languageFilter = document.getElementById('languageFilter');
const typeFilter = document.getElementById('typeFilter');
const stateFilter = document.getElementById('stateFilter');
const urlFilter = document.getElementById('urlFilter');
const domainFilter = document.getElementById('domainFilter');
const table = document.getElementById('issuesTable');
const tbody = table.querySelector('tbody');
const issueStatus = document.getElementById('issueStatus');
const targetLanguageHeader = document.getElementById('targetLanguageHeader');
const issuesBackToCheckLanguages = document.getElementById('issuesBackToCheckLanguages');
const workflowContextSummary = document.getElementById('workflowContextSummary');

const workflowContext = {
  domain: '',
  runId: '',
};
let persistedResults = [];
let persistedResultsDiagnostics = null;
let loadedIssues = [];
const issueDetailsCache = new Map();
let activePopoverState = null;
let pendingDetailRequest = null;
let popoverIdCounter = 0;
const llmResultDateFormatter = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Europe/Tallinn',
  day: '2-digit',
  month: '2-digit',
  year: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

class MultiSelectFilter {
  constructor(root, { key, singular, plural, onChange = () => {} }) {
    this.root = root;
    this.key = key;
    this.singular = singular;
    this.plural = plural;
    this.options = [];
    this.selected = new Set();
    this.onChange = onChange;
    this._renderShell();
  }

  _renderShell() {
    this.root.innerHTML = '';
    this.root.classList.add('multi-select-filter');
    this.button = document.createElement('button');
    this.button.type = 'button';
    this.button.className = 'multi-select-trigger';
    this.panel = document.createElement('div');
    this.panel.className = 'multi-select-panel hidden';
    this.root.appendChild(this.button);
    this.root.appendChild(this.panel);
    this.button.addEventListener('click', () => {
      this.panel.classList.toggle('hidden');
    });
    if (typeof document.addEventListener === 'function') {
      document.addEventListener('click', (event) => {
        if (typeof this.root.contains === 'function' && !this.root.contains(event.target)) this.panel.classList.add('hidden');
      });
    }
    this._updateTriggerLabel();
  }

  setOptions(values = []) {
    const normalized = [...new Set(values.map((value) => String(value || '').trim().toLowerCase()).filter(Boolean))].sort();
    const selectedBefore = new Set(this.selected);
    this.options = normalized;
    this.selected = new Set(this.options.filter((value) => selectedBefore.has(value)));
    if (!this.selected.size) this.selected = new Set(this.options);
    this._renderPanel();
    this._updateTriggerLabel();
  }

  value() {
    if (!this.options.length || this.selected.size === this.options.length) return '';
    if (!this.selected.size) return '__none__';
    return [...this.selected].join(',');
  }

  includes(value) {
    if (!this.options.length) return true;
    const normalized = String(value || '').trim().toLowerCase();
    if (!normalized) return false;
    return this.selected.has(normalized);
  }

  _renderPanel() {
    this.panel.innerHTML = '';
    const actions = document.createElement('div');
    actions.className = 'multi-select-actions';
    const selectAll = document.createElement('button');
    selectAll.type = 'button';
    selectAll.textContent = 'Select all';
    const deselectAll = document.createElement('button');
    deselectAll.type = 'button';
    deselectAll.textContent = 'Deselect all';
    selectAll.addEventListener('click', (event) => {
      event.preventDefault();
      this.selected = new Set(this.options);
      this._renderPanel();
      this._updateTriggerLabel();
      this.onChange();
    });
    deselectAll.addEventListener('click', (event) => {
      event.preventDefault();
      this.selected = new Set();
      this._renderPanel();
      this._updateTriggerLabel();
      this.onChange();
    });
    actions.appendChild(selectAll);
    actions.appendChild(deselectAll);
    this.panel.appendChild(actions);
    for (const option of this.options) {
      const label = document.createElement('label');
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = this.selected.has(option);
      checkbox.addEventListener('change', () => {
        if (checkbox.checked) this.selected.add(option);
        else this.selected.delete(option);
        this._updateTriggerLabel();
        this.onChange();
      });
      const text = document.createElement('span');
      text.textContent = option;
      label.appendChild(checkbox);
      label.appendChild(text);
      this.panel.appendChild(label);
    }
  }

  _updateTriggerLabel() {
    if (!this.options.length || this.selected.size === this.options.length) {
      this.button.textContent = `All ${this.plural}`;
      return;
    }
    if (!this.selected.size) {
      this.button.textContent = `No ${this.plural} selected`;
      return;
    }
    this.button.textContent = `${this.selected.size} ${this.selected.size === 1 ? this.singular : this.plural} selected`;
  }
}

const stateMultiFilter = new MultiSelectFilter(stateFilter, { key: 'state', singular: 'state', plural: 'states', onChange: () => renderIssues() });
const typeMultiFilter = new MultiSelectFilter(typeFilter, { key: 'type', singular: 'type', plural: 'types', onChange: () => renderIssues() });

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
  closeIssueDetailsPopover({ restoreFocus: false, immediate: true });
  tbody.innerHTML = '';
  table.classList.add('hidden');
  loadedIssues = [];
  issueDetailsCache.clear();
  updateTargetLanguage([]);
}

function activeDomain() {
  return (domainSelect?.value || workflowContext.domain || '').trim();
}

function activeRunId() {
  const selected = selectedPersistedResult();
  if (selected) return String(selected.run_id || '').trim();
  const selectedValue = String((persistedResultSelect && persistedResultSelect.value) || '').trim();
  if (selectedValue.includes('|')) {
    const [, runIdPart] = selectedValue.split('|');
    return String(runIdPart || '').trim();
  }
  return selectedValue || workflowContext.runId || '';
}

function persistedResultKey(result) {
  const explicit = String((result || {}).result_key || '').trim();
  if (explicit) return explicit;
  const domain = String((result || {}).domain || '').trim();
  const runId = String((result || {}).run_id || '').trim();
  return domain ? `${domain}|${runId}` : runId;
}

function selectedPersistedResult() {
  const selectedValue = String((persistedResultSelect && persistedResultSelect.value) || '').trim();
  if (selectedValue) {
    const byValue = persistedResults.find((row) => persistedResultKey(row) === selectedValue);
    if (byValue) return byValue;
    const byRunId = persistedResults.find((row) => String((row || {}).run_id || '').trim() === selectedValue);
    if (byRunId) return byRunId;
  }
  const runId = String(workflowContext.runId || '').trim();
  if (!runId) return null;
  const matches = persistedResults.filter((row) => String((row || {}).run_id || '').trim() === runId);
  if (matches.length === 1) return matches[0];
  return matches.find((row) => String((row || {}).domain || '').trim() === activeDomain()) || null;
}

function activeArtifactDomain() {
  const selected = selectedPersistedResult();
  const selectedDomain = String((selected || {}).domain || '').trim();
  return selectedDomain || activeDomain();
}

function buildParams() {
  const stateValue = stateMultiFilter.value();
  const typeValue = typeMultiFilter.value();
  return new URLSearchParams({
    domain: activeArtifactDomain(),
    run_id: activeRunId(),
    q: (queryInput.value || '').trim(),
    language: (languageFilter.value || '').trim(),
    type: typeValue || '',
    state: stateValue || '',
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
  workflowContextSummary.textContent = `Workflow context: ${contextParts.join(' \u00b7 ')}.`;
}

function syncDefaultsFromQuery() {
  const { domain, runId } = queryParamsFromLocation();
  workflowContext.domain = domain;
  workflowContext.runId = runId;

  const params = new URLSearchParams();
  if (workflowContext.domain) params.set('domain', workflowContext.domain);
  if (workflowContext.runId) params.set('run_id', workflowContext.runId);
  const hasWorkflowContext = Boolean(workflowContext.domain || workflowContext.runId);
  const basePath = hasWorkflowContext ? '/check-languages' : '/pulls';
  issuesBackToCheckLanguages.href = `${basePath}${params.toString() ? `?${params.toString()}` : ''}`;

  updateWorkflowSummary();
}

function resultOptionLabel(result) {
  const createdAtRaw = String((result || {}).created_at || '').trim();
  const parsed = createdAtRaw ? new Date(createdAtRaw) : null;
  const parts = parsed && !Number.isNaN(parsed.getTime())
    ? Object.fromEntries(llmResultDateFormatter.formatToParts(parsed).map((part) => [part.type, part.value]))
    : {};
  const datePart = parts.day && parts.month && parts.year ? `${parts.day}.${parts.month}.${parts.year}` : 'date unknown';
  const timePart = parts.hour && parts.minute ? `${parts.hour}:${parts.minute}` : 'time unknown';
  const language = resolveResultLanguage(result);
  return `LLM result - ${language} - ${datePart} | ${timePart}`;
}

function resolveResultLanguage(result) {
  const metadata = result && typeof result.metadata === 'object' ? result.metadata : {};
  for (const value of [
    result?.target_language,
    result?.language,
    result?.lang,
    result?.target_lang,
    result?.locale,
    metadata?.target_language,
    metadata?.language,
    metadata?.lang,
  ]) {
    const normalized = String(value || '').trim().toLowerCase();
    if (normalized) return normalized;
  }
  return 'unknown';
}

function fallbackSelectionTag(value) {
  const raw = String(value || '').trim();
  if (!raw) return '0000';
  const fingerprint = [...raw].reduce((acc, ch) => ((acc * 31) + ch.charCodeAt(0)) % 10000, 7);
  return String(fingerprint).padStart(4, '0');
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
  const runIdCounts = new Map();
  for (const row of persistedResults) {
    const runId = String((row || {}).run_id || '').trim();
    if (!runId) continue;
    runIdCounts.set(runId, (runIdCounts.get(runId) || 0) + 1);
  }
  const hasPreferred = selectedRunId && persistedResults.some((row) => String(row.run_id || '').trim() === selectedRunId);
  const preferredResult = hasPreferred
    ? (persistedResults.find((row) => String(row.run_id || '').trim() === selectedRunId) || null)
    : (persistedResults[0] || null);
  const preferredRunId = String((preferredResult || {}).run_id || '').trim();
  const preferredKey = preferredResult ? persistedResultKey(preferredResult) : '';
  if (selectedRunId && !hasPreferred) {
    const option = document.createElement('option');
    option.value = selectedRunId;
    option.textContent = `LLM result - unknown - date unknown | time unknown \u00b7 selection #${fallbackSelectionTag(selectedRunId)}`;
    option.selected = true;
    persistedResultSelect.appendChild(option);
  }
  for (const result of persistedResults) {
    const runId = String(result.run_id || '').trim();
    if (!runId) continue;
    const option = document.createElement('option');
    const runIdDuplicated = (runIdCounts.get(runId) || 0) > 1;
    option.value = runIdDuplicated ? persistedResultKey(result) : runId;
    const domainSuffix = runIdDuplicated ? ` \u00b7 ${String(result.domain || '').trim()}` : '';
    option.textContent = `${resultOptionLabel(result)}${domainSuffix}`;
    const shouldSelect = !selectedRunId || hasPreferred ? option.value === (runIdDuplicated ? preferredKey : preferredRunId) : false;
    option.selected = shouldSelect;
    persistedResultSelect.appendChild(option);
    if (shouldSelect) {
      persistedResultSelect.value = option.value;
      if (runIdInput) runIdInput.value = runId;
    }
  }
  if (selectedRunId && !hasPreferred) return;
}

async function loadPersistedResults(preferredRunId = '') {
  const domain = activeDomain();
  persistedResults = [];
  persistedResultsDiagnostics = null;
  renderPersistedResultOptions('');
  if (!domain) {
    setStatus('Select a domain to load persisted results.', 'muted');
    renderPersistedResultOptions('');
    return;
  }
  const response = await fetch(`/api/issues/results?${new URLSearchParams({ domain }).toString()}`);
  const payload = await safeReadPayload(response);
  if (!response.ok) throw new Error(payload.error || `Failed to load persisted results (${response.status})`);
  const rows = Array.isArray(payload.results) ? payload.results : [];
  persistedResults = rows;
  persistedResultsDiagnostics = payload.diagnostics && typeof payload.diagnostics === 'object' ? payload.diagnostics : null;
  renderPersistedResultOptions(preferredRunId);
}

async function loadDomains() {
  if (!domainSelect) return;
  try {
    const response = await fetch('/api/domains');
    const payload = await safeReadPayload(response);
    const items = Array.isArray(payload.items) ? payload.items : [];
    domainSelect.innerHTML = '<option value="">\u2014 select domain \u2014</option>';
    const domains = [...items];
    const prefilledDomain = workflowContext.domain;
    if (prefilledDomain && !domains.includes(prefilledDomain)) domains.push(prefilledDomain);
    for (const domain of domains) {
      const option = document.createElement('option');
      option.value = domain;
      option.textContent = domain;
      domainSelect.appendChild(option);
    }
    if (prefilledDomain) {
      domainSelect.value = prefilledDomain;
    } else if (items.length === 1) {
      domainSelect.value = items[0];
    }
    if (domainSelect.value) {
      await loadPersistedResults(workflowContext.runId || '');
    }
  } catch (_) {
    // fail silently
  }
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

function normalizeIssueDetailPayload(payload) {
  const issue = payload && typeof payload.issue === 'object' ? payload.issue : {};
  const evidence = issue && typeof issue.evidence === 'object' ? issue.evidence : {};
  const whatIsWrong = issue.message || issue.description || 'No message available.';
  const whereItAppears = readField(evidence, ['url', 'page_url', 'source_url']) || 'URL unavailable';
  return { whatIsWrong, whereItAppears };
}

function appendLinkifiedText(parent, textValue) {
  const appendPlainText = (value) => {
    if (typeof document.createTextNode === 'function') {
      parent.appendChild(document.createTextNode(value));
      return;
    }
    const fallbackText = document.createElement('span');
    fallbackText.textContent = value;
    parent.appendChild(fallbackText);
  };
  const text = String(textValue || '');
  const urlRegex = /https?:\/\/[^\s]+/gi;
  let lastIndex = 0;
  let match = urlRegex.exec(text);
  while (match) {
    const [matchedUrl] = match;
    if (match.index > lastIndex) {
      appendPlainText(text.slice(lastIndex, match.index));
    }
    const safeUrl = isSafeExternalHttpUrl(matchedUrl) ? matchedUrl : '';
    if (safeUrl) {
      const link = document.createElement('a');
      link.href = safeUrl;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = safeUrl;
      parent.appendChild(link);
    } else {
      appendPlainText(matchedUrl);
    }
    lastIndex = match.index + matchedUrl.length;
    match = urlRegex.exec(text);
  }
  if (lastIndex < text.length) {
    appendPlainText(text.slice(lastIndex));
  }
}

function createPopoverSection(label, value) {
  const section = document.createElement('div');
  section.className = 'issue-detail-popover-section';
  const heading = document.createElement('h4');
  heading.textContent = label;
  const content = document.createElement('p');
  content.className = 'issue-detail-popover-content';
  appendLinkifiedText(content, value);
  section.appendChild(heading);
  section.appendChild(content);
  return section;
}

function setElementAttribute(el, name, value) {
  if (!el) return;
  if (typeof el.setAttribute === 'function') {
    el.setAttribute(name, value);
    return;
  }
  el[name] = value;
}

function shouldReduceMotion() {
  if (!window || typeof window.matchMedia !== 'function') return false;
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch (_) {
    return false;
  }
}

function isAbortError(error) {
  return Boolean(error && (error.name === 'AbortError' || error.code === 20));
}

function measureRect(element, fallback = { left: 12, top: 12, width: 16, height: 16 }) {
  if (element && typeof element.getBoundingClientRect === 'function') {
    const rect = element.getBoundingClientRect();
    if (rect && Number.isFinite(rect.left) && Number.isFinite(rect.top)) return rect;
  }
  return {
    left: fallback.left,
    top: fallback.top,
    width: fallback.width,
    height: fallback.height,
    right: fallback.left + fallback.width,
    bottom: fallback.top + fallback.height,
  };
}

function positionIssueDetailsPopover(popover, trigger) {
  const viewportWidth = Number(window?.innerWidth) || 1280;
  const viewportHeight = Number(window?.innerHeight) || 720;
  const viewportPadding = 12;
  const panelWidth = Math.min(420, Math.max(280, viewportWidth * 0.36));
  const triggerRect = measureRect(trigger);
  const panelRect = measureRect(popover, { left: 0, top: 0, width: panelWidth, height: 200 });
  const panelHeight = Number(panelRect.height) || 200;
  const spaceBelow = viewportHeight - triggerRect.bottom;
  const spaceAbove = triggerRect.top;
  const placement = spaceBelow >= panelHeight + 16 || spaceBelow >= spaceAbove ? 'bottom' : 'top';
  const preferredLeft = triggerRect.left + (triggerRect.width / 2) - (panelWidth / 2);
  const left = Math.min(
    Math.max(preferredLeft, viewportPadding),
    Math.max(viewportPadding, viewportWidth - panelWidth - viewportPadding),
  );
  const top = placement === 'bottom'
    ? Math.min(triggerRect.bottom + 10, viewportHeight - panelHeight - viewportPadding)
    : Math.max(viewportPadding, triggerRect.top - panelHeight - 10);
  const triggerCenter = triggerRect.left + (triggerRect.width / 2);
  const caretLeft = Math.min(Math.max(triggerCenter - left, 14), panelWidth - 14);
  setElementAttribute(popover, 'data-placement', placement);
  if (!popover.style) popover.style = {};
  popover.style.left = `${Math.round(left)}px`;
  popover.style.top = `${Math.round(top)}px`;
  popover.style.width = `${Math.round(panelWidth)}px`;
  if (typeof popover.style.setProperty === 'function') {
    popover.style.setProperty('--issue-popover-caret-left', `${Math.round(caretLeft)}px`);
  } else {
    popover.style['--issue-popover-caret-left'] = `${Math.round(caretLeft)}px`;
  }
}

function syncPopoverPosition() {
  if (!activePopoverState) return;
  positionIssueDetailsPopover(activePopoverState.popover, activePopoverState.trigger);
}

function closeIssueDetailsPopover({ restoreFocus = true, immediate = false } = {}) {
  if (!activePopoverState) return;
  const { popover, trigger, cleanup = [] } = activePopoverState;
  for (const dispose of cleanup) {
    if (typeof dispose === 'function') dispose();
  }
  if (pendingDetailRequest && pendingDetailRequest.issueId === activePopoverState.issueId && pendingDetailRequest.controller) {
    pendingDetailRequest.controller.abort();
    pendingDetailRequest = null;
  }
  const removePopover = () => {
    if (popover?.parentNode) popover.parentNode.removeChild(popover);
  };
  if (!immediate && popover && !shouldReduceMotion()) {
    popover.classList.remove('is-open');
    popover.classList.add('is-closing');
    const schedule = (window && typeof window.setTimeout === 'function') ? window.setTimeout.bind(window) : setTimeout;
    const closingTimer = schedule(removePopover, 140);
    activePopoverState.closeTimer = closingTimer;
  } else {
    removePopover();
  }
  setElementAttribute(trigger, 'aria-expanded', 'false');
  if (trigger && typeof trigger.removeAttribute === 'function') trigger.removeAttribute('aria-controls');
  const shouldRestoreFocus = restoreFocus && trigger && typeof trigger.focus === 'function';
  activePopoverState = null;
  if (shouldRestoreFocus) trigger.focus();
}

async function loadIssueDetailData(issueId, { signal } = {}) {
  const cached = issueDetailsCache.get(issueId);
  if (cached && cached.status === 'loaded') return cached.data;
  if (cached && cached.status === 'loading' && cached.promise) return cached.promise;
  const promise = (async () => {
    const response = await fetch(`/api/issues/detail?${new URLSearchParams({
      domain: activeArtifactDomain(),
      run_id: activeRunId(),
      id: issueId,
    }).toString()}`, { signal });
    const payload = await safeReadPayload(response);
    if (!response.ok) throw new Error(payload.error || `Failed to load issue details (${response.status})`);
    return normalizeIssueDetailPayload(payload);
  })();
  issueDetailsCache.set(issueId, { status: 'loading', promise });
  try {
    const data = await promise;
    issueDetailsCache.set(issueId, { status: 'loaded', data });
    return data;
  } catch (error) {
    issueDetailsCache.set(issueId, { status: 'error', error });
    throw error;
  }
}

function renderIssueDetailPopoverBody(popover, state) {
  const existingCaret = Array.isArray(popover.children)
    ? popover.children.find((child) => child?.className === 'issue-detail-popover-caret')
    : null;
  popover.innerHTML = '';
  if (typeof popover.nodeType !== 'number' && Array.isArray(popover.children)) popover.children = [];
  if (existingCaret) popover.appendChild(existingCaret);
  if (state.status === 'loading') {
    const loading = document.createElement('p');
    loading.className = 'muted issue-detail-popover-loading';
    loading.textContent = 'Loading issue details…';
    popover.appendChild(loading);
    syncPopoverPosition();
    return;
  }
  if (state.status === 'error') {
    const errorText = document.createElement('p');
    errorText.className = 'error issue-detail-popover-error';
    errorText.textContent = state.message || 'Unable to load issue details.';
    popover.appendChild(errorText);
    syncPopoverPosition();
    return;
  }
  popover.appendChild(createPopoverSection('What is wrong', state.data.whatIsWrong));
  popover.appendChild(createPopoverSection('Where it appears', state.data.whereItAppears));
  syncPopoverPosition();
}

function openIssueDetailsPopover(issue, trigger, cell) {
  const issueId = String(issue?.id || '').trim();
  if (!issueId) return;
  if (activePopoverState && activePopoverState.issueId === issueId) {
    closeIssueDetailsPopover({ restoreFocus: false, immediate: true });
    return;
  }
  closeIssueDetailsPopover({ restoreFocus: false, immediate: true });
  const popover = document.createElement('div');
  popover.className = 'issue-detail-popover';
  setElementAttribute(popover, 'role', 'dialog');
  setElementAttribute(popover, 'id', `issue-detail-popover-${++popoverIdCounter}`);
  setElementAttribute(popover, 'aria-label', 'Issue details');
  popover.addEventListener('click', (event) => event.stopPropagation());
  popover.addEventListener('keydown', (event) => event.stopPropagation());
  const caret = document.createElement('span');
  caret.className = 'issue-detail-popover-caret';
  setElementAttribute(caret, 'aria-hidden', 'true');
  popover.appendChild(caret);
  const mount = document.body && typeof document.body.appendChild === 'function' ? document.body : cell;
  mount.appendChild(popover);
  positionIssueDetailsPopover(popover, trigger);
  if (shouldReduceMotion()) {
    popover.classList.add('is-open');
  } else if (typeof window.requestAnimationFrame === 'function') {
    window.requestAnimationFrame(() => popover.classList.add('is-open'));
  } else {
    popover.classList.add('is-open');
  }
  const cleanup = [];
  if (typeof window.addEventListener === 'function') {
    const onReposition = () => syncPopoverPosition();
    window.addEventListener('resize', onReposition);
    window.addEventListener('scroll', onReposition, true);
    cleanup.push(() => {
      window.removeEventListener('resize', onReposition);
      window.removeEventListener('scroll', onReposition, true);
    });
  }
  setElementAttribute(trigger, 'aria-expanded', 'true');
  setElementAttribute(trigger, 'aria-haspopup', 'dialog');
  setElementAttribute(trigger, 'aria-controls', popover.id);
  activePopoverState = { issueId, trigger, popover, cleanup };

  const cached = issueDetailsCache.get(issueId);
  if (cached && cached.status === 'loaded') {
    renderIssueDetailPopoverBody(popover, { status: 'loaded', data: cached.data });
    return;
  }
  if (cached && cached.status === 'error') {
    renderIssueDetailPopoverBody(popover, { status: 'error', message: cached.error?.message || 'Unable to load issue details.' });
    return;
  }
  renderIssueDetailPopoverBody(popover, { status: 'loading' });
  if (pendingDetailRequest && pendingDetailRequest.issueId !== issueId && pendingDetailRequest.controller) {
    pendingDetailRequest.controller.abort();
    pendingDetailRequest = null;
  }
  const controller = typeof AbortController === 'function' ? new AbortController() : null;
  pendingDetailRequest = { issueId, controller };
  loadIssueDetailData(issueId, { signal: controller ? controller.signal : undefined })
    .then((data) => {
      if (!activePopoverState || activePopoverState.issueId !== issueId) return;
      renderIssueDetailPopoverBody(popover, { status: 'loaded', data });
    })
    .catch((error) => {
      if (isAbortError(error)) return;
      if (!activePopoverState || activePopoverState.issueId !== issueId) return;
      renderIssueDetailPopoverBody(popover, { status: 'error', message: error.message });
    })
    .finally(() => {
      if (pendingDetailRequest && pendingDetailRequest.issueId === issueId) pendingDetailRequest = null;
    });
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
}

async function loadIssues() {
  updateWorkflowSummary();
  setStatus('Loading\u2026');
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
  loadedIssues = Array.isArray(payload.issues) ? payload.issues : [];
  updateTargetLanguage(loadedIssues, payload.target_language || '');
  syncFilterOptionsFromIssues(loadedIssues);
  renderIssues();
}

function syncFilterOptionsFromIssues(issues = []) {
  stateMultiFilter.setOptions(issues.map((issue) => String(issue?.state || '').trim().toLowerCase()).filter(Boolean));
  typeMultiFilter.setOptions(issues.map((issue) => String(issue?.category || '').trim().toLowerCase()).filter(Boolean));
}

function filteredIssues() {
  return loadedIssues.filter((issue) => {
    const issueState = String(issue?.state || '').trim().toLowerCase();
    const issueType = String(issue?.category || '').trim().toLowerCase();
    return stateMultiFilter.includes(issueState)
      && typeMultiFilter.includes(issueType);
  });
}

function renderIssues() {
  closeIssueDetailsPopover({ restoreFocus: false, immediate: true });
  const issues = filteredIssues();
  tbody.innerHTML = '';
  const count = typeof issues.length === 'number' ? issues.length : 0;
  const countSuffix = Number.isFinite(count) ? ` Count: ${count}` : '';
  if (!issues.length) {
    table.classList.add('hidden');
    setStatus(`No issues found for current filters.${countSuffix}`, 'empty');
    return;
  }
  setStatus(`Issues loaded.${countSuffix}`, 'ok');
  for (const issue of issues) {
    const tr = document.createElement('tr');

    const sourceTd = document.createElement('td');
    sourceTd.textContent = deriveSourceText(issue);
    tr.appendChild(sourceTd);

    const targetTd = document.createElement('td');
    targetTd.textContent = deriveTargetText(issue);
    tr.appendChild(targetTd);

    const issueTd = document.createElement('td');
    issueTd.className = 'issue-cell';
    if (typeof issueTd.nodeType !== 'number') issueTd.textContent = issueLabel(issue);
    const issueText = document.createElement('span');
    issueText.className = 'issue-label';
    issueText.textContent = issueLabel(issue);
    const detailsButton = document.createElement('button');
    detailsButton.type = 'button';
    detailsButton.className = 'issue-details-trigger';
    detailsButton.setAttribute('data-button-fx', 'off');
    setElementAttribute(detailsButton, 'aria-label', 'Open issue details');
    setElementAttribute(detailsButton, 'aria-haspopup', 'dialog');
    setElementAttribute(detailsButton, 'aria-expanded', 'false');
    detailsButton.innerHTML = '<span aria-hidden="true">?</span>';
    detailsButton.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      openIssueDetailsPopover(issue, detailsButton, issueTd);
    });
    issueTd.appendChild(issueText);
    issueTd.appendChild(detailsButton);
    tr.appendChild(issueTd);

    tbody.appendChild(tr);
  }
  table.classList.remove('hidden');
}

if (typeof document.addEventListener === 'function') {
  document.addEventListener('click', (event) => {
    if (!activePopoverState) return;
    const popover = activePopoverState.popover;
    const trigger = activePopoverState.trigger;
    const target = event.target;
    const clickedInsidePopover = Boolean(popover && typeof popover.contains === 'function' && popover.contains(target));
    const clickedTrigger = Boolean(trigger && typeof trigger.contains === 'function' && trigger.contains(target));
    if (!clickedInsidePopover && !clickedTrigger) closeIssueDetailsPopover({ restoreFocus: false, immediate: true });
  });
  document.addEventListener('keydown', (event) => {
    if (!activePopoverState) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      closeIssueDetailsPopover({ restoreFocus: true, immediate: true });
    }
  });
}

applyBtn.addEventListener('click', () => {
  const params = buildParams();
  window.history.replaceState({}, '', `/?${params.toString()}`);
  updateWorkflowSummary();
  loadIssues().catch((err) => setStatus(err.message, 'error'));
});

if (domainSelect) {
  domainSelect.addEventListener('change', async () => {
    updateWorkflowSummary();
    await loadPersistedResults('');
  });
}

if (persistedResultSelect) {
  persistedResultSelect.addEventListener('change', () => {
    if (runIdInput) runIdInput.value = activeRunId();
    updateWorkflowSummary();
    const params = buildParams();
    window.history.replaceState({}, '', `/?${params.toString()}`);
    loadIssues().catch((err) => setStatus(err.message, 'error'));
  });
}

if (refreshPersistedResults) {
  refreshPersistedResults.addEventListener('click', () => {
    const previousRunId = activeRunId();
    setStatus('Loading persisted results\u2026');
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
loadDomains()
  .then(() => {
    if (activeDomain() && activeRunId()) return loadIssues();
    if (activeDomain() && !persistedResults.length) {
      clearIssuesView();
      setStatus(noPersistedResultsMessage(), 'empty');
    }
    return null;
  })
  .catch((err) => setStatus(err.message, 'error'));
