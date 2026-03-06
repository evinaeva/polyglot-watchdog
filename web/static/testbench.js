async function fetchModules() {
  const response = await fetch('/api/testbench/modules');
  const payload = await response.json();
  return payload.modules || [];
}

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function statusLabel(status) {
  const s = String(status || '').toUpperCase();
  if (s === 'IMPLEMENTED') return 'Implemented';
  if (s === 'PARTIAL') return 'Partial';
  if (s === 'NOT_IMPLEMENTED') return 'NOT IMPLEMENTED';
  return s;
}

function renderModuleList(modules) {
  const moduleList = document.getElementById('moduleList');
  moduleList.innerHTML = '';
  modules.forEach((module, idx) => {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.className = 'module-button';
    btn.textContent = `[Phase ${module.phase}] ${module.title} (${statusLabel(module.status)})`;
    btn.onclick = () => renderModuleDetails(module);
    li.appendChild(btn);
    moduleList.appendChild(li);
    if (idx === 0) renderModuleDetails(module);
  });
}

function renderCaseOptions(testCases) {
  if (!testCases.length) {
    return '<p><strong>NO TEST FILES FOUND</strong>. Add suite files (*.suite.json / *.tests.json / suite.json).</p>';
  }
  return `
    <label for="caseSelect">Test case</label>
    <select id="caseSelect">
      ${testCases.map((testCase) => `<option value="${testCase.case_key}">${testCase.case_id} | ${testCase.source_type} | ${testCase.title}</option>`).join('')}
    </select>
  `;
}

function renderCaseMeta(testCase) {
  if (!testCase) return '(no case loaded)';
  return pretty({
    case_id: testCase.case_id,
    title: testCase.title,
    source_type: testCase.source_type,
    source_file: testCase.source_file,
    priority: testCase.priority,
    tags: testCase.tags,
    notes: testCase.notes,
    suite_version: testCase.suite_version,
    phase: testCase.phase,
    module_id: testCase.module_id,
    module_title: testCase.module_title,
  });
}

function renderModuleDetails(module) {
  const details = document.getElementById('moduleDetails');
  details.innerHTML = `
    <h2>${module.title}</h2>
    <p><strong>Status:</strong> ${statusLabel(module.status)}</p>
    <p>${module.description}</p>
    <h3>Overview</h3>
    <p><strong>Expected input artifacts:</strong> ${module.input_artifacts.join(', ') || 'n/a'}</p>
    <p><strong>Expected output artifacts:</strong> ${module.output_artifacts.join(', ') || 'n/a'}</p>
    <p><strong>Schema refs:</strong> ${module.schema_refs.join(', ') || 'No schema refs listed'}</p>
    <p><strong>Test JSON folder:</strong> ${module.test_data_path}</p>
    ${module.cases_message ? `<p>${module.cases_message}</p>` : ''}

    <h3>Test files / cases</h3>
    ${renderCaseOptions(module.test_cases || [])}

    <h3>Run</h3>
    <button id="loadInputBtn">Load selected case</button>
    <button id="runTestBtn">Run test</button>

    <h3>Case metadata</h3>
    <pre id="caseMetaPreview">(no case loaded)</pre>

    <h3>Input preview</h3>
    <pre id="inputPreview">(no input loaded)</pre>

    <h3>Expected</h3>
    <pre id="expectedPreview">(no expected loaded)</pre>

    <h3>Result</h3>
    <pre id="resultSummary">(not run yet)</pre>

    <h3>Actual output</h3>
    <pre id="outputPreview">(not run yet)</pre>

    <h3>Assertion results</h3>
    <pre id="assertionsPreview">(not run yet)</pre>

    <h3>Validation</h3>
    <pre id="validationPreview">(not run yet)</pre>

    <h3>Logs / Errors</h3>
    <pre id="errorPreview">(none)</pre>
  `;

  async function execute(loadOnly) {
    const caseSelect = document.getElementById('caseSelect');
    const caseKey = caseSelect ? caseSelect.value : null;

    const result = await fetch('/api/testbench/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ module_id: module.module_id, case_key: caseKey }),
    }).then((r) => r.json());

    document.getElementById('caseMetaPreview').textContent = renderCaseMeta(result.case);
    document.getElementById('inputPreview').textContent = pretty(result.input || {});
    document.getElementById('expectedPreview').textContent = pretty(result.expected || {});

    if (loadOnly) return;

    document.getElementById('resultSummary').textContent = pretty({
      status: result.status,
      duration_ms: result.duration_ms,
    });
    document.getElementById('outputPreview').textContent = pretty(result.output);
    document.getElementById('assertionsPreview').textContent = pretty(result.assertion_results || []);
    document.getElementById('validationPreview').textContent = pretty(result.validation_messages || []);
    document.getElementById('errorPreview').textContent = result.error || '(none)';
  }

  document.getElementById('loadInputBtn').onclick = () => execute(true);
  document.getElementById('runTestBtn').onclick = () => execute(false);
}

(async function init() {
  const modules = await fetchModules();
  renderModuleList(modules);
})();
