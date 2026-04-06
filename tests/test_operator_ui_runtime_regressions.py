import json
import re
import subprocess
import textwrap
import types
import sys
from pathlib import Path


def _run_node_json(script: str) -> dict:
    proc = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout.strip())


def test_urls_runtime_uses_live_typed_domain_for_continue_and_api_mutations():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          return {
            id,
            value: '',
            href: '',
            textContent: '',
            innerHTML: '',
            dataset: {},
            disabled: false,
            children: [],
            options: [],
            className: '',
            classList: {
              add(name){ classes.add(name); },
              remove(name){ classes.delete(name); },
              toggle(name){ if (classes.has(name)) { classes.delete(name); return false; } classes.add(name); return true; },
              contains(name){ return classes.has(name); },
            },
            setAttribute(){},
            appendChild(child){ this.children.push(child); this.options.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            querySelector(){ return makeElement('qs'); },
            querySelectorAll(){ return []; },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            click(){ if (listeners.click) return listeners.click({ target: this }); },
          };
        }

        const els = {
          domainInput: makeElement('domainInput'),
          domainSavedToggle: makeElement('domainSavedToggle'),
          domainSavedMenu: makeElement('domainSavedMenu'),
          loadButton: makeElement('loadButton'),
          replaceButton: makeElement('replaceButton'),
          addButton: makeElement('addButton'),
          clearButton: makeElement('clearButton'),
          urlsMultiline: makeElement('urlsMultiline'),
          updatedAt: makeElement('updatedAt'),
          savedUrlsBody: makeElement('savedUrlsBody'),
          errorBox: makeElement('errorBox'),
          statusBox: makeElement('statusBox'),
          continueFirstRun: makeElement('continueFirstRun'),
        };
        els.domainSavedMenu.classList.add('hidden');
        els.domainInput.value = '';

        const documentListeners = {};
        const payloads = [];

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          setTimeout: (fn) => { fn(); return 1; },
          clearTimeout: () => {},
          window: { i18n: { t: (_k, fallback) => fallback } },
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
            addEventListener: (event, cb) => { documentListeners[event] = cb; },
          },
          fetch: async (url, init = {}) => {
            if (url === '/api/domains') {
              return { ok: true, json: async () => ({ items: ['bongacams.com', 'typed.example'], last_used_first_run_domain: 'typed.example' }) };
            }
            if (url.startsWith('/api/recipes?')) {
              return { ok: true, json: async () => ({ recipes: [] }) };
            }
            if (url.startsWith('/api/seed-urls?')) {
              return { ok: true, json: async () => ({ urls: [], updated_at: '2026-03-24T00:00:00Z' }) };
            }
            if (url === '/api/seed-urls/add') {
              payloads.push(JSON.parse(init.body || '{}'));
              return { ok: true, json: async () => ({ urls: [], updated_at: '2026-03-24T00:00:00Z' }) };
            }
            throw new Error('Unexpected URL: ' + url);
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/urls.js', 'utf8'), sandbox);

        (async () => {
          await documentListeners['pw:i18n:ready']();
          const preselectedAfterLoad = els.domainInput.value;
          els.domainInput.value = 'typed.example';
          els.domainInput.dispatch('input');
          els.urlsMultiline.value = 'https://typed.example/a';
          await els.addButton.click();
          console.log(JSON.stringify({
            preselectedAfterLoad,
            continueHref: els.continueFirstRun.href,
            addPayloadDomain: payloads[0] ? payloads[0].domain : '',
            defaultValueStillExpected: els.domainInput.value,
          }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert out["preselectedAfterLoad"] == "typed.example"
    assert out["continueHref"] == "/workflow?domain=typed.example"
    assert out["addPayloadDomain"] == "typed.example"
    assert out["defaultValueStillExpected"] == "typed.example"


def test_workflow_runtime_uses_canonical_screenshot_view_url_and_safe_empty_state_and_run_label():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const el = {
            id,
            value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            children: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            querySelector(){ return makeElement('qs'); },
          };
          return el;
        }

        const ids = ['wfDomain','wfRefreshUrls','wfStartCapture','wfGenerateDataset','wfContinuePulls','wfStatus','wfStatusSummary','wfPayload','wfTransition','wfExistingRuns','wfUseExistingRun','wfRefreshRuns','wfRunsStatus','wfContextsStatus','wfContextsTable','wfContextsBody'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        els.wfContextsBody.children = [];

        const document = {
          getElementById: (id) => els[id],
          createElement: (tag) => {
            const el = makeElement(tag);
            if (tag === 'tr') {
              Object.defineProperty(el, 'innerHTML', {
                set(value) {
                  this._innerHTML = value;
                  this.lastElementChild = { appendChild(){} };
                },
                get() { return this._innerHTML || ''; },
              });
            }
            return el;
          },
        };

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          window: { location: { search: '' }, history: { replaceState(){} } },
          document,
          fetch: async (url) => {
            if (url === '/api/domains') return { ok: true, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/seed-urls?')) return { ok: true, json: async () => ({ urls: [] }) };
            if (url.startsWith('/api/capture/runs?')) return { ok: true, json: async () => ({ runs: [] }) };
            if (url.startsWith('/api/workflow/status?')) return { ok: true, json: async () => ({ capture: { status: 'not_started' }, run: {} }) };
            if (url.startsWith('/api/capture/contexts?')) return { ok: true, json: async () => ({ contexts: [] }) };
            return { ok: true, json: async () => ({}) };
          },
          setInterval: () => 1,
          clearInterval: () => {},
          setTimeout: (fn) => { fn(); return 1; },
          clearTimeout: () => {},
          safeReadPayload: async (response) => response.json(),
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/workflow.js', 'utf8'), sandbox);

        const labelDisplay = sandbox.formatRunLabel('run-123', 'First_run_18:31|24.03.2026');
        const labelFallback = sandbox.formatRunLabel('run-123', 'none');

        sandbox.renderContextsRows('example.com', 'run-123', [{
          url: 'https://example.com',
          language: 'en',
          state: 'baseline',
          viewport_kind: 'desktop',
          user_tier: 'guest',
          elements_count: 1,
          screenshot_view_url: '/api/page-screenshot?domain=example.com&run_id=run-123&page_id=p1',
          storage_uri: 'gs://should-not-be-used',
          review_status: {},
        }]);

        sandbox.renderContextsRows('example.com', 'run-123', [{
          url: 'https://example.com/empty',
          language: 'en',
          state: 'baseline',
          viewport_kind: 'desktop',
          user_tier: 'guest',
          elements_count: 1,
          screenshot_view_url: '',
          storage_uri: 'gs://still-not-used',
          review_status: {},
        }]);

        const firstHtml = els.wfContextsBody.children[0]._innerHTML || '';
        const secondHtml = els.wfContextsBody.children[1]._innerHTML || '';

        console.log(JSON.stringify({ labelDisplay, labelFallback, firstHtml, secondHtml }));
        """
    )
    out = _run_node_json(script)
    assert out["labelDisplay"] == "First_run_18:31|24.03.2026"
    assert out["labelFallback"] == "run-123"
    assert '/api/page-screenshot?domain=example.com&run_id=run-123&page_id=p1' in out["firstHtml"]
    assert 'gs://should-not-be-used' not in out["firstHtml"]
    assert 'open</a>' not in out["secondHtml"]


def test_urls_drawer_keeps_url_domain_for_row_mutations_when_recipe_domain_changes():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          const el = {
            id,
            value: '',
            href: '',
            textContent: '',
            innerHTML: '',
            dataset: {},
            checked: true,
            disabled: false,
            files: [{ name: 'r.json' }],
            children: [],
            options: [],
            selectedOptions: [],
            className: '',
            classList: {
              add(name){ classes.add(name); },
              remove(name){ classes.delete(name); },
              toggle(name){ if (classes.has(name)) { classes.delete(name); return false; } classes.add(name); return true; },
              contains(name){ return classes.has(name); },
            },
            setAttribute(){},
            appendChild(child){ this.children.push(child); this.options.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this, key: '' }); },
            click(){ if (listeners.click) return listeners.click({ target: this }); },
            querySelector(){ return makeElement('qs'); },
            querySelectorAll(){ return []; },
          };
          return el;
        }

        const els = {
          domainInput: makeElement('domainInput'),
          domainSavedToggle: makeElement('domainSavedToggle'),
          domainSavedMenu: makeElement('domainSavedMenu'),
          loadButton: makeElement('loadButton'),
          replaceButton: makeElement('replaceButton'),
          addButton: makeElement('addButton'),
          clearButton: makeElement('clearButton'),
          urlsMultiline: makeElement('urlsMultiline'),
          updatedAt: makeElement('updatedAt'),
          savedUrlsBody: makeElement('savedUrlsBody'),
          errorBox: makeElement('errorBox'),
          statusBox: makeElement('statusBox'),
          continueFirstRun: makeElement('continueFirstRun'),
          recipeDrawer: makeElement('recipeDrawer'),
          closeRecipeDrawer: makeElement('closeRecipeDrawer'),
          recipeDrawerUrl: makeElement('recipeDrawerUrl'),
          recipeDomainSelect: makeElement('recipeDomainSelect'),
          recipeAttachToggle: makeElement('recipeAttachToggle'),
          recipeFileInput: makeElement('recipeFileInput'),
          uploadRecipeButton: makeElement('uploadRecipeButton'),
          attachedRecipesList: makeElement('attachedRecipesList'),
          allRecipesList: makeElement('allRecipesList'),
        };
        els.domainInput.value = 'domain-a.com';
        els.recipeDomainSelect.value = 'domain-a.com';
        els.domainSavedMenu.classList.add('hidden');

        const documentListeners = {};
        const calls = [];
        const seedRows = {
          'domain-a.com': { urls: [{ url: 'https://domain-a.com/u', recipe_ids: ['a-r1'], active: true }], updated_at: '2026-03-01T00:00:00Z' },
          'domain-b.com': { urls: [{ url: 'https://domain-b.com/u', recipe_ids: ['b-r1'], active: true }], updated_at: '2026-03-01T00:00:00Z' },
        };

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          FormData: class { constructor(){ this.map = new Map(); } append(k,v){ this.map.set(k,v); } },
          window: { i18n: { t: (_k, fb) => fb }, confirm: () => true },
          setTimeout: (fn) => { fn(); return 1; },
          clearTimeout: () => {},
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
            addEventListener: (event, cb) => { documentListeners[event] = cb; },
          },
          fetch: async (url, init = {}) => {
            calls.push({ url, init });
            if (url === '/api/domains') {
              return { ok: true, json: async () => ({ items: ['domain-a.com', 'domain-b.com'] }) };
            }
            if (url.startsWith('/api/recipes?')) return { ok: true, json: async () => ({ recipes: [{ recipe_id: 'b-r1' }] }) };
            if (url.startsWith('/api/seed-urls?')) {
              const domain = decodeURIComponent(url.split('domain=')[1] || '');
              return { ok: true, json: async () => seedRows[domain] || { urls: [], updated_at: '' } };
            }
            if (url === '/api/seed-urls/row-upsert') {
              const payload = JSON.parse(init.body || '{}');
              return { ok: true, json: async () => ({ urls: [{ url: payload.row.url, recipe_ids: payload.row.recipe_ids, active: true }], updated_at: '2026-03-02T00:00:00Z' }) };
            }
            if (url === '/api/recipes/upload') {
              return { ok: true, json: async () => ({ status: 'ok', recipe_id: 'b-r1', overwrote: false }) };
            }
            if (url === '/api/recipes/delete') return { ok: true, json: async () => ({ status: 'ok' }) };
            if (url === '/api/seed-urls/add' || url === '/api/seed-urls/clear' || url === '/api/seed-urls/delete' || url === '/api/seed-urls') {
              return { ok: true, json: async () => ({ urls: [], updated_at: '2026-03-01T00:00:00Z' }) };
            }
            throw new Error('Unexpected URL: ' + url);
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/urls.js', 'utf8'), sandbox);

        (async () => {
          await documentListeners['pw:i18n:ready']();
          await sandbox.load();
          sandbox.openRecipeDrawer('https://domain-a.com/u');
          els.recipeDomainSelect.value = 'domain-b.com';
          await sandbox.loadRecipeManagementData();
          await sandbox.upsertRowRecipes('https://domain-a.com/u', ['a-r1', 'b-r1']);
          const recipeCalls = calls.filter((row) => row.url.startsWith('/api/recipes?domain='));
          console.log(JSON.stringify({
            rowUpsertDomain: JSON.parse(calls.find((row) => row.url === '/api/seed-urls/row-upsert').init.body).domain,
            recipeFetchDomain: recipeCalls.length ? recipeCalls[recipeCalls.length - 1].url : '',
            seedFetchUsedRecipeDomain: calls.some((row) => row.url === '/api/seed-urls?domain=domain-b.com'),
          }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert out["rowUpsertDomain"] == "domain-a.com"
    assert out["recipeFetchDomain"].endswith("domain-b.com")
    assert out["seedFetchUsedRecipeDomain"] is False


def test_workflow_runtime_formats_utc_timestamps_in_tallinn_with_dst():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          return {
            id,
            value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(){},
            addEventListener(){},
            querySelector(){ return makeElement('qs'); },
          };
        }

        const ids = ['wfDomain','wfRefreshUrls','wfStartCapture','wfGenerateDataset','wfContinuePulls','wfStatus','wfStatusSummary','wfPayload','wfTransition','wfExistingRuns','wfUseExistingRun','wfRefreshRuns','wfRunsStatus','wfContextsStatus','wfContextsTable','wfContextsBody'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        const sandbox = {
          console,
          URL,
          URLSearchParams,
          window: { location: { search: '' }, history: { replaceState(){} } },
          document: { getElementById: (id) => els[id], createElement: () => makeElement('created') },
          fetch: async () => ({ ok: true, json: async () => ({ runs: [], items: [], contexts: [], capture: { status: 'not_started' }, run: {} }) }),
          setInterval: () => 1,
          clearInterval: () => {},
          safeReadPayload: async (response) => response.json(),
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/workflow.js', 'utf8'), sandbox);

        console.log(JSON.stringify({
          winter: sandbox.formatUtcTimestampForUi('2026-01-15T10:00:00Z'),
          summer: sandbox.formatUtcTimestampForUi('2026-07-15T10:00:00Z'),
        }));
        """
    )
    out = _run_node_json(script)
    assert out["winter"] == "2026-01-15 12:00"
    assert out["summer"] == "2026-07-15 13:00"


def test_workflow_runtime_sorting_uses_raw_utc_timestamp_not_display_value():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');
        function makeElement(id='') {
          return {
            id, value: '', href: '', innerHTML: '', textContent: '', className: '', dataset: {}, disabled: false,
            classList: { add(){}, remove(){}, toggle(){} }, setAttribute(){}, appendChild(){}, addEventListener(){},
            querySelector(){ return makeElement('qs'); },
          };
        }
        const ids = ['wfDomain','wfRefreshUrls','wfStartCapture','wfGenerateDataset','wfContinuePulls','wfStatus','wfStatusSummary','wfPayload','wfTransition','wfExistingRuns','wfUseExistingRun','wfRefreshRuns','wfRunsStatus','wfContextsStatus','wfContextsTable','wfContextsBody'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        const sandbox = {
          console,
          URL,
          URLSearchParams,
          window: { location: { search: '' }, history: { replaceState(){} } },
          document: { getElementById: (id) => els[id], createElement: () => makeElement('created') },
          fetch: async () => ({ ok: true, json: async () => ({ runs: [], items: [], contexts: [], capture: { status: 'not_started' }, run: {} }) }),
          setInterval: () => 1,
          clearInterval: () => {},
          safeReadPayload: async (response) => response.json(),
        };
        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/workflow.js', 'utf8'), sandbox);
        const out = sandbox.sortRunsNewestFirst([
          { run_id: 'older', created_at: '2026-01-15T10:00:00Z' },
          { run_id: 'newer', created_at: '2026-01-15T11:00:00Z' },
        ]);
        console.log(JSON.stringify({ first: out[0].run_id, second: out[1].run_id }));
        """
    )
    out = _run_node_json(script)
    assert out["first"] == "newer"
    assert out["second"] == "older"


def test_workflow_existing_runs_default_selection_prefers_newest_and_handles_empty_states():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const el = {
            id,
            value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            children: [],
            options: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); this.options.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            querySelector(){ return makeElement('qs'); },
          };
          if (id === 'wfExistingRuns') {
            Object.defineProperty(el, 'innerHTML', {
              set(value) {
                this._innerHTML = value;
                this.children = [];
                this.options = [];
                this.value = '';
                if (String(value).includes('No runs found')) {
                  this.options.push({ value: '' });
                }
              },
              get() { return this._innerHTML || ''; },
            });
          }
          return el;
        }

        const ids = ['wfDomain','wfRefreshUrls','wfStartCapture','wfGenerateDataset','wfContinuePulls','wfStatus','wfStatusSummary','wfPayload','wfTransition','wfExistingRuns','wfUseExistingRun','wfRefreshRuns','wfRunsStatus','wfContextsStatus','wfContextsTable','wfContextsBody'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        els.wfDomain.value = 'example.com';

        const runsPayloads = [
          { runs: [
            { run_id: 'run-older', created_at: '2026-03-10T10:00:00Z', display_name: 'First_run_12:00|10.03.2026' },
            { run_id: 'run-newest', created_at: '2026-03-12T10:00:00Z', display_name: 'First_run_12:00|12.03.2026' },
            { run_id: 'run-middle', created_at: '2026-03-11T10:00:00Z', display_name: 'First_run_12:00|11.03.2026' },
          ] },
          { runs: [{ run_id: 'run-only', created_at: '2026-03-20T10:00:00Z', display_name: 'First_run_12:00|20.03.2026' }] },
          { runs: [] },
          { runs: [
            { run_id: 'run-a', created_at: '2026-03-01T10:00:00Z', display_name: 'First_run_12:00|01.03.2026' },
            { run_id: 'run-z-newest', created_at: '2026-03-30T10:00:00Z', display_name: 'First_run_12:00|30.03.2026' },
            { run_id: 'run-m', created_at: '2026-03-15T10:00:00Z', display_name: 'First_run_12:00|15.03.2026' },
          ] },
        ];
        let runsCallIndex = 0;

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          window: { location: { search: '' }, history: { replaceState(){} } },
          document: {
            getElementById: (id) => els[id],
            createElement: (tag) => makeElement(tag),
          },
          fetch: async (url) => {
            if (url.startsWith('/api/capture/runs?')) {
              const payload = runsPayloads[Math.min(runsCallIndex, runsPayloads.length - 1)];
              runsCallIndex += 1;
              return { ok: true, json: async () => payload };
            }
            if (url === '/api/domains') return { ok: true, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/seed-urls?')) return { ok: true, json: async () => ({ urls: [] }) };
            if (url.startsWith('/api/workflow/status?')) return { ok: true, json: async () => ({ capture: { status: 'not_started' }, run: {} }) };
            if (url.startsWith('/api/capture/contexts?')) return { ok: true, json: async () => ({ contexts: [] }) };
            return { ok: true, json: async () => ({}) };
          },
          setInterval: () => 1,
          clearInterval: () => {},
          safeReadPayload: async (response) => response.json(),
        };

        vm.createContext(sandbox);
        const workflowSource = fs
          .readFileSync('web/static/workflow.js', 'utf8')
          .replace("initWorkflow().catch((err) => setStatus(err.message, 'error'));", '');
        vm.runInContext(workflowSource, sandbox);

        (async () => {
          await sandbox.loadExistingRuns();
          const multiDefault = els.wfExistingRuns.value;
          const multiOptions = els.wfExistingRuns.options.map((opt) => opt.value);
          els.wfExistingRuns.value = 'run-middle';
          els.wfExistingRuns.disabled = false;

          await sandbox.loadExistingRuns();
          const singleDefault = els.wfExistingRuns.value;
          const singleDisabled = els.wfUseExistingRun.disabled;

          await sandbox.loadExistingRuns();
          const emptyDefault = els.wfExistingRuns.value;
          const emptyDisabled = els.wfUseExistingRun.disabled;
          const emptyStatus = els.wfRunsStatus.textContent;

          await sandbox.loadExistingRuns();
          const unsortedDefault = els.wfExistingRuns.value;
          const unsortedOptions = els.wfExistingRuns.options.map((opt) => opt.value);

          console.log(JSON.stringify({
            multiDefault,
            multiOptions,
            singleDefault,
            singleDisabled,
            emptyDefault,
            emptyDisabled,
            emptyStatus,
            unsortedDefault,
            unsortedOptions,
          }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert out["multiDefault"] == "run-newest"
    assert out["multiOptions"] == ["run-newest", "run-middle", "run-older"]
    assert out["singleDefault"] == "run-only"
    assert out["singleDisabled"] is False
    assert out["emptyDefault"] == ""
    assert out["emptyDisabled"] is True
    assert out["emptyStatus"] == "No existing runs found for this domain yet."
    assert out["unsortedDefault"] == "run-z-newest"
    assert out["unsortedOptions"] == ["run-z-newest", "run-m", "run-a"]


def test_workflow_existing_runs_preserves_explicit_non_first_query_selection_without_fallback_rewrite():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          return {
            id,
            _value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            children: [],
            options: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); this.options.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            querySelector(){ return makeElement('qs'); },
            get value(){ return this._value; },
            set value(v){ this._value = String(v || ''); },
          };
        }

        const ids = ['wfDomain','wfRefreshUrls','wfStartCapture','wfGenerateDataset','wfContinuePulls','wfStatus','wfStatusSummary','wfPayload','wfTransition','wfExistingRuns','wfUseExistingRun','wfRefreshRuns','wfRunsStatus','wfContextsStatus','wfContextsTable','wfContextsBody'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        els.wfDomain.value = 'example.com';

        const replaced = [];

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          window: {
            location: { search: '?domain=example.com&run_id=run-check-languages-latest' },
            history: { replaceState: (_s, _t, url) => replaced.push(url) },
          },
          document: { getElementById: (id) => els[id], createElement: (tag) => makeElement(tag) },
          fetch: async (url) => {
            if (url.startsWith('/api/capture/runs?')) {
              return {
                ok: true,
                json: async () => ({
                  runs: [
                    {
                      run_id: 'run-check-languages-latest',
                      created_at: '2026-03-30T11:00:00Z',
                      jobs: [{ job_id: 'check-languages-1', type: 'check_languages', status: 'queued' }],
                    },
                    {
                      run_id: 'run-first-old',
                      created_at: '2026-03-29T11:00:00Z',
                      jobs: [{ job_id: 'phase1-old', type: 'capture', context: { language: 'en', state: 'baseline' } }],
                    },
                    {
                      run_id: 'run-first-new',
                      created_at: '2026-03-30T10:00:00Z',
                      metadata: { flow: 'first_run' },
                      jobs: [],
                    },
                  ],
                }),
              };
            }
            if (url === '/api/domains') return { ok: true, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/seed-urls?')) return { ok: true, json: async () => ({ urls: [] }) };
            if (url.startsWith('/api/workflow/status?')) return { ok: true, json: async () => ({ capture: { status: 'not_started' }, run: {} }) };
            if (url.startsWith('/api/capture/contexts?')) return { ok: true, json: async () => ({ contexts: [] }) };
            return { ok: true, json: async () => ({}) };
          },
          setInterval: () => 1,
          clearInterval: () => {},
          safeReadPayload: async (response) => response.json(),
        };

        vm.createContext(sandbox);
        const workflowSource = fs
          .readFileSync('web/static/workflow.js', 'utf8')
          .replace("initWorkflow().catch((err) => setStatus(err.message, 'error'));", '');
        vm.runInContext(workflowSource, sandbox);
        vm.runInContext("activeRunId = 'run-check-languages-latest';", sandbox);

        (async () => {
          await sandbox.loadExistingRuns();
          const optionValues = els.wfExistingRuns.options.map((opt) => opt.value);
          const selected = els.wfExistingRuns.value;
          console.log(JSON.stringify({ optionValues, selected, replaced, status: els.wfRunsStatus.textContent }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert out["optionValues"] == ["run-first-new", "run-first-old"]
    assert out["selected"] == ""
    assert out["replaced"] == []
    assert out["status"] == "Current run is not in the First run list. Keeping current run context."


def test_workflow_existing_runs_option_labels_use_human_first_run_format_only():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          return {
            id,
            _value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            children: [],
            options: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); this.options.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            querySelector(){ return makeElement('qs'); },
            get value(){ return this._value; },
            set value(v){ this._value = String(v || ''); },
          };
        }

        const ids = ['wfDomain','wfRefreshUrls','wfStartCapture','wfGenerateDataset','wfContinuePulls','wfStatus','wfStatusSummary','wfPayload','wfTransition','wfExistingRuns','wfUseExistingRun','wfRefreshRuns','wfRunsStatus','wfContextsStatus','wfContextsTable','wfContextsBody'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        els.wfDomain.value = 'example.com';

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          window: { location: { search: '?domain=example.com' }, history: { replaceState(){} } },
          document: { getElementById: (id) => els[id], createElement: (tag) => makeElement(tag) },
          fetch: async (url) => {
            if (url.startsWith('/api/capture/runs?')) {
              return {
                ok: true,
                json: async () => ({
                  runs: [
                    {
                      run_id: 'run-123',
                      created_at: '2026-03-30T07:24:00Z',
                      jobs: [{ job_id: 'phase1-123-en-desktop-baseline', type: 'capture', context: { language: 'en', state: 'baseline' } }],
                    },
                  ],
                }),
              };
            }
            if (url === '/api/domains') return { ok: true, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/seed-urls?')) return { ok: true, json: async () => ({ urls: [] }) };
            if (url.startsWith('/api/workflow/status?')) return { ok: true, json: async () => ({ capture: { status: 'not_started' }, run: {} }) };
            if (url.startsWith('/api/capture/contexts?')) return { ok: true, json: async () => ({ contexts: [] }) };
            return { ok: true, json: async () => ({}) };
          },
          setInterval: () => 1,
          clearInterval: () => {},
          safeReadPayload: async (response) => response.json(),
        };

        vm.createContext(sandbox);
        const workflowSource = fs
          .readFileSync('web/static/workflow.js', 'utf8')
          .replace("initWorkflow().catch((err) => setStatus(err.message, 'error'));", '');
        vm.runInContext(workflowSource, sandbox);

        (async () => {
          await sandbox.loadExistingRuns();
          const label = String((els.wfExistingRuns.options[0] || {}).textContent || '');
          console.log(JSON.stringify({ label }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert re.fullmatch(r"First run \d{2}:\d{2}, \d{2}\.\d{2}\.\d{4}", out["label"])
    assert "run-123" not in out["label"]
    assert "jobs:" not in out["label"]
    assert "idle" not in out["label"]
    assert "running" not in out["label"]


def test_workflow_existing_runs_preserves_active_selected_run_on_reload():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const el = {
            id,
            value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            children: [],
            options: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); this.options.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            click(){ if (listeners.click) return listeners.click({ target: this }); },
            querySelector(){ return makeElement('qs'); },
          };
          if (id === 'wfExistingRuns') {
            Object.defineProperty(el, 'innerHTML', {
              set(value) {
                this._innerHTML = value;
                this.children = [];
                this.options = [];
                this.value = '';
                if (String(value).includes('No runs found')) this.options.push({ value: '' });
              },
              get() { return this._innerHTML || ''; },
            });
          }
          return el;
        }

        const ids = ['wfDomain','wfRefreshUrls','wfStartCapture','wfGenerateDataset','wfContinuePulls','wfStatus','wfStatusSummary','wfPayload','wfTransition','wfExistingRuns','wfUseExistingRun','wfRefreshRuns','wfRunsStatus','wfContextsStatus','wfContextsTable','wfContextsBody'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));

        const runPayload = {
          runs: [
            { run_id: 'run-older', created_at: '2026-03-10T10:00:00Z', display_name: 'First_run_12:00|10.03.2026' },
            { run_id: 'run-newest', created_at: '2026-03-12T10:00:00Z', display_name: 'First_run_12:00|12.03.2026' },
            { run_id: 'run-middle', created_at: '2026-03-11T10:00:00Z', display_name: 'First_run_12:00|11.03.2026' },
          ],
        };

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          window: { location: { search: '?domain=example.com&run_id=run-middle' }, history: { replaceState(){} } },
          document: {
            getElementById: (id) => els[id],
            createElement: (tag) => makeElement(tag),
          },
          fetch: async (url) => {
            if (url === '/api/domains') return { ok: true, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/seed-urls?')) return { ok: true, json: async () => ({ urls: [] }) };
            if (url.startsWith('/api/capture/runs?')) return { ok: true, json: async () => runPayload };
            if (url.startsWith('/api/workflow/status?')) return { ok: true, json: async () => ({ capture: { status: 'ready' }, run: { run_id: 'run-middle' } }) };
            if (url.startsWith('/api/capture/contexts?')) return { ok: true, json: async () => ({ contexts: [] }) };
            return { ok: true, json: async () => ({}) };
          },
          setInterval: () => 1,
          clearInterval: () => {},
          safeReadPayload: async (response) => response.json(),
        };

        vm.createContext(sandbox);
        const workflowSource = fs
          .readFileSync('web/static/workflow.js', 'utf8')
          .replace("initWorkflow().catch((err) => setStatus(err.message, 'error'));", '');
        vm.runInContext(workflowSource, sandbox);

        (async () => {
          await sandbox.initWorkflow();
          els.wfExistingRuns.value = 'run-middle';
          await els.wfUseExistingRun.click();
          await sandbox.loadExistingRuns();
          const afterReload = els.wfExistingRuns.value;
          console.log(JSON.stringify({ afterReload }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert out["afterReload"] == "run-middle"


def test_upsert_job_status_keeps_utc_storage_timestamps(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    sys.modules.setdefault(
        "jsonschema",
        types.SimpleNamespace(validate=lambda *_a, **_k: None, ValidationError=Exception, Draft7Validator=object),
    )
    from app.skeleton_server import _upsert_job_status

    state = {"runs": []}

    def fake_load(_domain):
        return state

    def fake_save(_domain, payload):
        state.clear()
        state.update(payload)

    monkeypatch.setattr("app.skeleton_server._load_runs", fake_load)
    monkeypatch.setattr("app.skeleton_server._save_runs", fake_save)
    monkeypatch.setattr("app.skeleton_server.time.strftime", lambda *_args, **_kwargs: "2026-01-15T10:00:00Z")

    _upsert_job_status("example.com", "r1", {"job_id": "j1", "status": "queued"})

    run = state["runs"][0]
    job = run["jobs"][0]
    assert run["created_at"] == "2026-01-15T10:00:00Z"
    assert job["created_at"] == "2026-01-15T10:00:00Z"
    assert job["updated_at"] == "2026-01-15T10:00:00Z"


def test_en_standard_helper_and_pulls_success_message_runtime_flow():
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    sys.modules.setdefault(
        "jsonschema",
        types.SimpleNamespace(validate=lambda *_a, **_k: None, ValidationError=Exception, Draft7Validator=object),
    )
    from app.skeleton_server import _en_standard_display_name_today

    label = _en_standard_display_name_today()
    assert re.fullmatch(r"EN_standard_\d{2}:\d{2}\|\d{2}\.\d{2}\.\d{4}", label)

    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const el = {
            id,
            value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            children: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            addEventListener(type, cb){ listeners[type] = cb; },
            click(){ if (listeners.click) return listeners.click({ target: this }); },
            querySelector(){ return makeElement('qs'); },
          };
          return el;
        }

        const ids = ['pullsStatus','pullsTable','pullsUrlSearch','pullsElementTypeFilter','pullsLanguageSummary','pullsWorkflowContextSummary','pullsWhitelistInput','pullsWhitelistAdd','pullsWhitelistStatus','pullsWhitelistChips','pullsPrepareCapturedData','pullsPrepareCapturedDataStatus','pullsPreviewModal','pullsPreviewOverlay','pullsPreviewClose','pullsPreviewStatus','pullsPreviewImage','pullsPreviewBbox','pullsPreviewDetails','pullsScreenshotViewport','pullsScreenshotCanvas','pullsZoomIn','pullsZoomOut','pullsCenterElement','pullsImageAssetSection','pullsImageAsset','pullsImageAssetFallback','pullsImageAssetMeta','pullsBackToRunHub','continueCheckLanguages','continueCheckLanguagesBottom','pullsOpenContexts','pullsOpenIssues'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        els.pullsTable.querySelector = () => ({ innerHTML: '', appendChild(){}, children: [] });

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          window: { location: { search: '?domain=example.com&run_id=run-1' }, addEventListener(){} },
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
            addEventListener() {},
          },
          safeReadPayload: async (response) => response.json(),
          setTimeout: (fn) => { fn(); return 1; },
          clearTimeout: () => {},
          ResizeObserver: function(){ this.observe = () => {}; this.disconnect = () => {}; },
          fetch: async (url, init = {}) => {
            if (url.startsWith('/api/pulls?')) return { ok: true, status: 200, json: async () => ({ rows: [] }) };
            if (url.startsWith('/api/element-type-whitelist?')) return { ok: true, status: 200, json: async () => ({ entries: [] }) };
            if (url === '/api/workflow/generate-eligible-dataset') return { ok: true, status: 200, json: async () => ({ status: 'started' }) };
            if (url.startsWith('/api/workflow/status?')) {
              return {
                ok: true,
                status: 200,
                json: async () => ({
                  eligible_dataset: { status: 'ready', en_standard_display_name: 'EN_standard_18:31|24.03.2026' },
                  run: { en_standard_display_name: '' },
                }),
              };
            }
            return { ok: true, status: 200, json: async () => ({}) };
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/pulls.js', 'utf8'), sandbox);

        (async () => {
          await sandbox.triggerEligibleDatasetGeneration('example.com', 'run-1');
          console.log(JSON.stringify({ statusMessage: els.pullsPrepareCapturedDataStatus.textContent }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert out["statusMessage"] == "Captured data prepared successfully: EN_standard_18:31|24.03.2026."


def test_pulls_top_and_bottom_next_step_links_receive_same_runtime_href():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          return {
            id,
            value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            children: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            addEventListener(type, cb){ listeners[type] = cb; },
            querySelector(){ return { innerHTML: '', appendChild(){} }; },
          };
        }

        const ids = ['pullsStatus','pullsTable','pullsUrlSearch','pullsElementTypeFilter','pullsLanguageSummary','pullsWorkflowContextSummary','pullsWhitelistInput','pullsWhitelistAdd','pullsWhitelistStatus','pullsWhitelistChips','pullsPrepareCapturedData','pullsPrepareCapturedDataStatus','pullsPreviewModal','pullsPreviewOverlay','pullsPreviewClose','pullsPreviewStatus','pullsPreviewImage','pullsPreviewBbox','pullsPreviewDetails','pullsScreenshotViewport','pullsScreenshotCanvas','pullsZoomIn','pullsZoomOut','pullsCenterElement','pullsImageAssetSection','pullsImageAsset','pullsImageAssetFallback','pullsImageAssetMeta','pullsBackToRunHub','continueCheckLanguages','continueCheckLanguagesBottom','pullsOpenContexts','pullsOpenIssues'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          window: { location: { search: '?domain=example.com&run_id=run-77' }, history: { replaceState(){} }, addEventListener(){} },
          document: { getElementById: (id) => els[id], createElement: () => makeElement('created'), addEventListener(){} },
          safeReadPayload: async (response) => response.json(),
          setTimeout: (fn) => { fn(); return 1; },
          clearTimeout: () => {},
          ResizeObserver: function(){ this.observe = () => {}; this.disconnect = () => {}; },
          fetch: async (url) => {
            if (url.startsWith('/api/pulls?')) return { ok: true, status: 200, json: async () => ({ rows: [] }) };
            if (url.startsWith('/api/element-type-whitelist?')) return { ok: true, status: 200, json: async () => ({ entries: [] }) };
            return { ok: true, status: 200, json: async () => ({}) };
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/pulls.js', 'utf8'), sandbox);

        setTimeout(() => {
          console.log(JSON.stringify({ top: els.continueCheckLanguages.href, bottom: els.continueCheckLanguagesBottom.href }));
        }, 0);
        """
    )
    out = _run_node_json(script)
    expected = "/check-languages?domain=example.com&en_run_id=run-77"
    assert out["top"] == expected
    assert out["bottom"] == expected


def test_workflow_defaults_to_latest_run_by_timestamp_and_preserves_manual_selection_for_pulls_link():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const el = {
            id,
            _value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            children: [],
            options: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); this.options.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            querySelector(){ return makeElement('qs'); },
            get value(){ return this._value; },
            set value(v){ this._value = String(v || ''); },
          };
          return el;
        }

        const ids = ['wfDomain','wfRefreshUrls','wfStartCapture','wfGenerateDataset','wfContinuePulls','wfStatus','wfStatusSummary','wfPayload','wfTransition','wfExistingRuns','wfUseExistingRun','wfRefreshRuns','wfRunsStatus','wfContextsStatus','wfContextsTable','wfContextsBody'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        els.wfDomain.value = 'example.com';
        els.wfExistingRuns.options = [];
        Object.defineProperty(els.wfExistingRuns, 'innerHTML', {
          set(value) { this._innerHTML = value; if (value === '') { this.children = []; this.options = []; this._value = ''; } },
          get() { return this._innerHTML || ''; },
        });

        const historyUrls = [];

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          window: {
            location: { search: '?domain=example.com' },
            history: { replaceState: (_s, _t, url) => historyUrls.push(url) },
          },
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
          },
          fetch: async (url) => {
            if (url === '/api/domains') return { ok: true, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/seed-urls?')) return { ok: true, json: async () => ({ urls: [] }) };
            if (url.startsWith('/api/capture/runs?')) {
              return {
                ok: true,
                json: async () => ({
                  runs: [
                    { run_id: 'run-aaa', created_at: '2026-03-27T10:00:00Z', display_name: 'First_run_12:00|27.03.2026', jobs: [] },
                    { run_id: 'run-zzz', created_at: '2026-03-28T10:00:00Z', display_name: 'First_run_12:00|28.03.2026', jobs: [] },
                  ],
                }),
              };
            }
            if (url.startsWith('/api/workflow/status?')) return { ok: true, json: async () => ({ capture: { status: 'ready' }, run: {} }) };
            if (url.startsWith('/api/capture/contexts?')) return { ok: true, json: async () => ({ contexts: [] }) };
            return { ok: true, json: async () => ({}) };
          },
          setInterval: () => 1,
          clearInterval: () => {},
          safeReadPayload: async (response) => response.json(),
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/workflow.js', 'utf8'), sandbox);

        (async () => {
          await new Promise((resolve) => setTimeout(resolve, 0));
          const defaultSelected = els.wfExistingRuns.value;
          const defaultContinueHref = els.wfContinuePulls.href;
          els.wfExistingRuns.value = 'run-aaa';
          await els.wfUseExistingRun.dispatch('click');
          const manualContinueHref = els.wfContinuePulls.href;
          console.log(JSON.stringify({ defaultSelected, defaultContinueHref, manualContinueHref, historyUrls }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert out["defaultSelected"] == "run-zzz"
    assert out["defaultContinueHref"].endswith("domain=example.com&run_id=run-zzz")
    assert out["manualContinueHref"].endswith("domain=example.com&run_id=run-aaa")
    assert any("run_id=run-aaa" in entry for entry in out["historyUrls"])


def test_pulls_respects_explicit_run_and_uses_latest_timestamp_when_missing_and_keeps_single_resolved_run():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function runScenario(search, mutateSearchAfterInit = '') {
          function makeElement(id='') {
            const listeners = {};
            return {
              id,
              value: '',
              href: '',
              innerHTML: '',
              textContent: '',
              className: '',
              dataset: {},
              disabled: false,
              children: [],
              classList: { add(){}, remove(){}, toggle(){} },
              setAttribute(){},
              appendChild(child){ this.children.push(child); return child; },
              append(...nodes){ this.children.push(...nodes); },
              addEventListener(type, cb){ listeners[type] = cb; },
              dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
              querySelector(){ return { innerHTML: '', appendChild(){} }; },
            };
          }

          const ids = ['pullsStatus','pullsTable','pullsUrlSearch','pullsElementTypeFilter','pullsLanguageSummary','pullsWorkflowContextSummary','pullsWhitelistInput','pullsWhitelistAdd','pullsWhitelistStatus','pullsWhitelistChips','pullsPrepareCapturedData','pullsPrepareCapturedDataStatus','pullsPreviewModal','pullsPreviewOverlay','pullsPreviewClose','pullsPreviewStatus','pullsPreviewImage','pullsPreviewBbox','pullsPreviewDetails','pullsScreenshotViewport','pullsScreenshotCanvas','pullsZoomIn','pullsZoomOut','pullsCenterElement','pullsImageAssetSection','pullsImageAsset','pullsImageAssetFallback','pullsImageAssetMeta','pullsBackToRunHub','continueCheckLanguages','continueCheckLanguagesBottom','pullsOpenContexts','pullsOpenIssues'];
          const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
          const pullCalls = [];
          const runsCalls = [];
          const replaced = [];
          const generatedRunIds = [];

          const sandbox = {
            console,
            URLSearchParams,
            window: {
              location: { search },
              history: { replaceState: (_s, _t, url) => replaced.push(url) },
              addEventListener() {},
            },
            document: { getElementById: (id) => els[id], createElement: () => makeElement('created'), addEventListener(){} },
            safeReadPayload: async (response) => response.json(),
            setTimeout: (fn) => { fn(); return 1; },
            clearTimeout: () => {},
            ResizeObserver: function(){ this.observe = () => {}; this.disconnect = () => {}; },
            fetch: async (url, init = {}) => {
              if (url.startsWith('/api/pulls?')) {
                pullCalls.push(url);
                return { ok: true, status: 200, json: async () => ({ rows: [] }) };
              }
              if (url.startsWith('/api/capture/runs?')) {
                runsCalls.push(url);
                return { ok: true, status: 200, json: async () => ({
                  runs: [
                    { run_id: 'run-zzz', created_at: '2026-03-27T10:00:00Z' },
                    { run_id: 'run-aaa', created_at: '2026-03-28T10:00:00Z' },
                  ],
                }) };
              }
              if (url.startsWith('/api/element-type-whitelist?')) return { ok: true, status: 200, json: async () => ({ entries: [] }) };
              if (url.startsWith('/api/workflow/status?')) {
                return { ok: true, status: 200, json: async () => ({ eligible_dataset: { status: 'ready', en_standard_display_name: 'EN_standard_10:00|29.03.2026' }, run: {} }) };
              }
              if (url === '/api/workflow/generate-eligible-dataset') {
                if (init?.body) {
                  const parsed = JSON.parse(init.body);
                  generatedRunIds.push(parsed.run_id || '');
                }
                return {
                  ok: true,
                  status: 200,
                  json: async () => ({ status: 'started' }),
                  text: async () => '',
                  body: {
                    getReader: () => ({
                      read: async () => ({ done: true, value: null }),
                    }),
                  },
                };
              }
              return { ok: true, status: 200, json: async () => ({}) };
            },
          };

          vm.createContext(sandbox);
          vm.runInContext(fs.readFileSync('web/static/pulls.js', 'utf8'), sandbox);
          return new Promise((resolve) => setTimeout(async () => {
            if (mutateSearchAfterInit) sandbox.window.location.search = mutateSearchAfterInit;
            await els.pullsPrepareCapturedData.dispatch('click');
            resolve({
              pullCalls,
              runsCalls,
              replaced,
              summary: els.pullsWorkflowContextSummary.textContent,
              contextHref: els.pullsOpenContexts.href,
              issuesHref: els.pullsOpenIssues.href,
              nextHref: els.continueCheckLanguages.href,
              prepareStatus: els.pullsPrepareCapturedDataStatus.textContent,
              generatedRunIds,
            });
          }, 0));
        }

        (async () => {
          const explicit = await runScenario('?domain=example.com&run_id=run-zzz', '?domain=example.com&run_id=run-aaa');
          const inferred = await runScenario('?domain=example.com');
          console.log(JSON.stringify({ explicit, inferred }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert any("run_id=run-zzz" in call for call in out["explicit"]["pullCalls"])
    assert out["explicit"]["runsCalls"] == []
    assert "run: run-zzz" in out["explicit"]["summary"]
    assert out["explicit"]["contextHref"].endswith("domain=example.com&run_id=run-zzz")
    assert out["explicit"]["issuesHref"].endswith("domain=example.com&run_id=run-zzz")
    assert out["explicit"]["nextHref"].endswith("domain=example.com&en_run_id=run-zzz")
    assert out["explicit"]["prepareStatus"] == "Captured data prepared successfully: EN_standard_10:00|29.03.2026."
    assert out["explicit"]["generatedRunIds"] == ["run-zzz"]
    assert any("run_id=run-aaa" in call for call in out["inferred"]["pullCalls"])
    assert len(out["inferred"]["runsCalls"]) == 1
    assert any("run_id=run-aaa" in url for url in out["inferred"]["replaced"])
    assert out["inferred"]["generatedRunIds"] == ["run-aaa"]


def test_urls_saved_domain_menu_filters_malformed_values_and_supports_selection():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          return {
            id,
            value: '',
            href: '',
            textContent: '',
            innerHTML: '',
            dataset: {},
            disabled: false,
            children: [],
            options: [],
            className: '',
            classList: {
              add(name){ classes.add(name); },
              remove(name){ classes.delete(name); },
              toggle(name){ if (classes.has(name)) { classes.delete(name); return false; } classes.add(name); return true; },
              contains(name){ return classes.has(name); },
            },
            setAttribute(){},
            contains(){ return false; },
            appendChild(child){ this.children.push(child); this.options.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            querySelector(){ return this.children.find((child) => child.className === 'domain-saved-option') || null; },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type, payload = {}){ if (listeners[type]) return listeners[type]({ target: this, ...payload }); },
            click(){ if (listeners.click) return listeners.click({ target: this }); },
            focus(){},
          };
        }

        const els = {
          domainInput: makeElement('domainInput'),
          domainSavedToggle: makeElement('domainSavedToggle'),
          domainSavedMenu: makeElement('domainSavedMenu'),
          loadButton: makeElement('loadButton'),
          replaceButton: makeElement('replaceButton'),
          addButton: makeElement('addButton'),
          clearButton: makeElement('clearButton'),
          urlsMultiline: makeElement('urlsMultiline'),
          updatedAt: makeElement('updatedAt'),
          savedUrlsBody: makeElement('savedUrlsBody'),
          errorBox: makeElement('errorBox'),
          statusBox: makeElement('statusBox'),
          continueFirstRun: makeElement('continueFirstRun'),
        };
        els.domainSavedMenu.classList.add('hidden');

        const documentListeners = {};
        const sandbox = {
          console,
          URL,
          URLSearchParams,
          URL,
          setTimeout: (fn) => { fn(); return 1; },
          clearTimeout: () => {},
          window: { i18n: { t: (_k, fallback) => fallback } },
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
            addEventListener: (event, cb) => { documentListeners[event] = cb; },
          },
          fetch: async (url) => {
            if (url === '/api/domains') {
              return { ok: true, json: async () => ({ items: ['good.example', 'bhttps://evinaeva.github.io/polyglot-watchdog-testsite/'], last_used_first_run_domain: '' }) };
            }
            if (url.startsWith('/api/recipes?')) return { ok: true, json: async () => ({ recipes: [] }) };
            if (url.startsWith('/api/seed-urls?')) return { ok: true, json: async () => ({ urls: [], updated_at: '2026-03-24T00:00:00Z' }) };
            return { ok: true, json: async () => ({}) };
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/urls.js', 'utf8'), sandbox);

        (async () => {
          await documentListeners['pw:i18n:ready']();
          els.domainSavedToggle.click();
          const savedValues = els.domainSavedMenu.children.map((child) => child.textContent);
          const firstOption = els.domainSavedMenu.children.find((child) => child.className === 'domain-saved-option');
          if (firstOption) firstOption.click();
          console.log(JSON.stringify({
            savedValues,
            selectedDomain: els.domainInput.value,
            continueHref: els.continueFirstRun.href,
          }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert "good.example" in out["savedValues"]
    assert "bhttps://evinaeva.github.io/polyglot-watchdog-testsite/" not in out["savedValues"]
    assert out["selectedDomain"] == "good.example"
    assert out["continueHref"] == "/workflow?domain=good.example"


def test_pulls_advanced_primary_labels_are_readable_and_user_tier_defaults_to_free():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          return {
            id,
            value: '',
            href: '',
            innerHTML: '',
            textContent: '',
            className: '',
            dataset: {},
            disabled: false,
            children: [],
            classList: { add(){}, remove(){}, toggle(){} },
            setAttribute(){},
            appendChild(child){ this.children.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            addEventListener(type, cb){ listeners[type] = cb; },
            querySelector(){ return { addEventListener(){}, value: 'exclude' }; },
            focus(){},
          };
        }

        const ids = ['pullsStatus','pullsTable','pullsUrlSearch','pullsElementTypeFilter','pullsLanguageSummary','pullsWorkflowContextSummary','pullsWhitelistInput','pullsWhitelistAdd','pullsWhitelistStatus','pullsWhitelistChips','pullsPrepareCapturedData','pullsPrepareCapturedDataStatus','pullsPreviewModal','pullsPreviewOverlay','pullsPreviewClose','pullsPreviewStatus','pullsPreviewImage','pullsPreviewBbox','pullsPreviewDetails','pullsScreenshotViewport','pullsScreenshotCanvas','pullsZoomIn','pullsZoomOut','pullsCenterElement','pullsImageAssetSection','pullsImageAsset','pullsImageAssetFallback','pullsImageAssetMeta','pullsBackToRunHub','continueCheckLanguages','continueCheckLanguagesBottom','pullsOpenContexts','pullsOpenIssues'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        els.pullsTable.querySelector = () => ({ innerHTML: '', appendChild(){}, children: [] });

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          window: { location: { search: '?domain=example.com&run_id=run-1' }, addEventListener(){} },
          document: {
            getElementById: (id) => els[id],
            createElement: (tag) => {
              const el = makeElement(tag);
              if (tag === 'tr') {
                Object.defineProperty(el, 'innerHTML', {
                  set(value) {
                    this._innerHTML = value;
                    this.lastElementChild = { appendChild(){} };
                  },
                  get() { return this._innerHTML || ''; },
                });
              }
              return el;
            },
            addEventListener() {},
          },
          safeReadPayload: async (response) => response.json(),
          setTimeout: (fn) => { fn(); return 1; },
          clearTimeout: () => {},
          ResizeObserver: function(){ this.observe = () => {}; this.disconnect = () => {}; },
          fetch: async (url) => {
            if (url.startsWith('/api/pulls?')) return { ok: true, status: 200, json: async () => ({ rows: [] }) };
            if (url.startsWith('/api/element-type-whitelist?')) return { ok: true, status: 200, json: async () => ({ entries: [] }) };
            return { ok: true, status: 200, json: async () => ({}) };
          },
        };

        vm.createContext(sandbox);
        const source = fs.readFileSync('web/static/pulls.js', 'utf8');
        vm.runInContext(source, sandbox);
        console.log(JSON.stringify({
          defaultTier: sandbox.formatUserTier(''),
          summary: sandbox.captureContextSummary({ language: 'en', viewport_kind: 'desktop', state: 'baseline', user_tier: '' }),
          hasReadableAdvancedLabel: source.includes('Capture context:'),
          hasTechnicalDisclosure: source.includes('Technical IDs'),
        }));
        """
    )
    out = _run_node_json(script)
    assert out["defaultTier"] == "Free"
    assert out["summary"] == "EN · Desktop · baseline · Free"
    assert out["hasReadableAdvancedLabel"] is True
    assert out["hasTechnicalDisclosure"] is True


def test_index_runtime_uses_newest_persisted_result_and_allows_selection_change():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          const el = {
            id,
            value: '',
            href: '',
            textContent: '',
            innerHTML: '',
            disabled: false,
            children: [],
            className: '',
            classList: {
              add(name){ classes.add(name); },
              remove(name){ classes.delete(name); },
              toggle(name, force){ if (force === true) classes.add(name); else if (force === false) classes.delete(name); },
            },
            appendChild(child){ this.children.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            querySelector(){ return makeElement('qs'); },
          };
          Object.defineProperty(el, 'options', { get(){ return this.children; } });
          return el;
        }

        const ids = ['applyIssueQuery','exportIssuesCsv','issueQuery','domainSelect','domainInput','persistedResultSelect','refreshPersistedResults','runIdInput','languageFilter','severityFilter','typeFilter','stateFilter','urlFilter','domainFilter','issuesTable','issueStatus','issueCount','targetLanguageSummary','targetLanguageHeader','issuesBackToCheckLanguages','workflowContextSummary'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        const tbody = makeElement('tbody');
        els.issuesTable.querySelector = () => tbody;

        const calls = [];
        const sandbox = {
          console,
          URL,
          URLSearchParams,
          Intl,
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
          },
          window: {
            location: { search: '?domain=example.com' },
            history: { replaceState(){} },
          },
          safeReadPayload: async (response) => response.json(),
          fetch: async (url) => {
            calls.push(url);
            if (url === '/api/domains') return { ok: true, status: 200, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/issues/results?')) {
              return { ok: true, status: 200, json: async () => ({ results: [
                { run_id: 'run-new', created_at: '2026-03-02T10:00:00Z', display_label: 'First_run_12:00|02.03.2026' },
                { run_id: 'run-old', created_at: '2026-03-01T10:00:00Z', display_label: 'First_run_12:00|01.03.2026' },
              ]}) };
            }
            if (url.startsWith('/api/issues?')) {
              return { ok: true, status: 200, json: async () => ({ issues: [{ id: '1', message: 'x', evidence: { url: 'https://example.com' } }], count: 1 }) };
            }
            throw new Error('Unexpected URL: ' + url);
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/index.js', 'utf8'), sandbox);

        setTimeout(() => {
          const initialRunId = els.runIdInput.value;
          const initialIssuesCall = calls.find((url) => url.includes('/api/issues?')) || '';
          els.persistedResultSelect.value = 'run-old';
          els.persistedResultSelect.dispatch('change');
          setTimeout(() => {
            const latestIssuesCall = [...calls].reverse().find((url) => url.includes('/api/issues?')) || '';
            console.log(JSON.stringify({
              optionValues: els.persistedResultSelect.options.map((row) => row.value),
              initialRunId,
              initialIssuesCall,
              latestIssuesCall,
            }));
          }, 0);
        }, 0);
        """
    )
    out = _run_node_json(script)
    option_values = [value for value in out["optionValues"] if value]
    assert option_values[:2] == ["run-new", "run-old"]
    assert out["initialRunId"] == "run-new"
    assert "run_id=run-new" in out["initialIssuesCall"]
    assert "run_id=run-old" in out["latestIssuesCall"]


def test_index_runtime_uses_selected_result_domain_for_issues_and_detail_links():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          const el = {
            id,
            value: '',
            href: '',
            textContent: '',
            innerHTML: '',
            disabled: false,
            children: [],
            className: '',
            classList: {
              add(name){ classes.add(name); },
              remove(name){ classes.delete(name); },
              toggle(name, force){ if (force === true) classes.add(name); else if (force === false) classes.delete(name); },
            },
            appendChild(child){ this.children.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            querySelector(){ return makeElement('qs'); },
          };
          Object.defineProperty(el, 'options', { get(){ return this.children; } });
          return el;
        }

        const ids = ['applyIssueQuery','exportIssuesCsv','issueQuery','domainSelect','domainInput','persistedResultSelect','refreshPersistedResults','runIdInput','languageFilter','severityFilter','typeFilter','stateFilter','urlFilter','domainFilter','issuesTable','issueStatus','issueCount','targetLanguageSummary','targetLanguageHeader','issuesBackToCheckLanguages','workflowContextSummary'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        const tbody = makeElement('tbody');
        els.issuesTable.querySelector = () => tbody;

        const calls = [];
        const sandbox = {
          console,
          URL,
          URLSearchParams,
          Intl,
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
          },
          window: {
            location: { search: '?domain=https://evinaeva.github.io/polyglot-watchdog-testsite/en/index.html' },
            history: { replaceState(){} },
          },
          safeReadPayload: async (response) => response.json(),
          fetch: async (url) => {
            calls.push(url);
            if (url === '/api/domains') return { ok: true, status: 200, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/issues/results?')) {
              return { ok: true, status: 200, json: async () => ({ results: [
                { run_id: 'run-legacy', domain: 'https://evinaeva.github.io/', created_at: '2026-03-02T10:00:00Z', display_label: 'First_run_12:00|02.03.2026' },
              ]}) };
            }
            if (url.startsWith('/api/issues?')) {
              return { ok: true, status: 200, json: async () => ({ issues: [{ id: '1', message: 'x', evidence: { url: 'https://example.com' } }], count: 1 }) };
            }
            throw new Error('Unexpected URL: ' + url);
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/index.js', 'utf8'), sandbox);

        setTimeout(() => {
          const initialIssuesCall = calls.find((url) => url.includes('/api/issues?')) || '';
          const detailHref = (((tbody.children[0] || {}).children || [])[4] || {}).children ? ((((tbody.children[0] || {}).children || [])[4] || {}).children[0] || {}).href || '' : '';
          console.log(JSON.stringify({
            initialIssuesCall,
            detailHref,
            workflowSummary: els.workflowContextSummary.textContent,
          }));
        }, 0);
        """
    )
    out = _run_node_json(script)
    assert "domain=https%3A%2F%2Fevinaeva.github.io%2F" in out["initialIssuesCall"]
    assert "run_id=run-legacy" in out["initialIssuesCall"]
    assert "domain=https%3A%2F%2Fevinaeva.github.io%2F" in out["detailHref"]
    assert "artifact-domain: https://evinaeva.github.io/" in out["workflowSummary"]


def test_index_runtime_allows_selecting_duplicate_run_ids_across_domains():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          const el = {
            id,
            value: '',
            href: '',
            textContent: '',
            innerHTML: '',
            disabled: false,
            children: [],
            className: '',
            classList: {
              add(name){ classes.add(name); },
              remove(name){ classes.delete(name); },
              toggle(name, force){ if (force === true) classes.add(name); else if (force === false) classes.delete(name); },
            },
            appendChild(child){ this.children.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            querySelector(){ return makeElement('qs'); },
          };
          Object.defineProperty(el, 'options', { get(){ return this.children; } });
          return el;
        }

        const ids = ['applyIssueQuery','exportIssuesCsv','issueQuery','domainSelect','domainInput','persistedResultSelect','refreshPersistedResults','runIdInput','languageFilter','severityFilter','typeFilter','stateFilter','urlFilter','domainFilter','issuesTable','issueStatus','issueCount','targetLanguageSummary','targetLanguageHeader','issuesBackToCheckLanguages','workflowContextSummary'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        const tbody = makeElement('tbody');
        els.issuesTable.querySelector = () => tbody;

        const calls = [];
        const sandbox = {
          console,
          URL,
          URLSearchParams,
          Intl,
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
          },
          window: { location: { search: '?domain=https://evinaeva.github.io/polyglot-watchdog-testsite/en/index.html' }, history: { replaceState(){} } },
          safeReadPayload: async (response) => response.json(),
          fetch: async (url) => {
            calls.push(url);
            if (url === '/api/domains') return { ok: true, status: 200, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/issues/results?')) {
              return { ok: true, status: 200, json: async () => ({ results: [
                { run_id: 'run-shared', result_key: 'https://evinaeva.github.io/polyglot-watchdog-testsite/en/index.html|run-shared', domain: 'https://evinaeva.github.io/polyglot-watchdog-testsite/en/index.html', created_at: '2026-03-03T10:00:00Z', display_label: 'Canonical run' },
                { run_id: 'run-shared', result_key: 'https://evinaeva.github.io/|run-shared', domain: 'https://evinaeva.github.io/', created_at: '2026-03-02T10:00:00Z', display_label: 'Legacy run' },
              ]}) };
            }
            if (url.startsWith('/api/issues?')) {
              return { ok: true, status: 200, json: async () => ({ issues: [{ id: '1', message: 'x', evidence: { url: 'https://example.com' } }], count: 1 }) };
            }
            throw new Error('Unexpected URL: ' + url);
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/index.js', 'utf8'), sandbox);

        setTimeout(() => {
          const optionValues = els.persistedResultSelect.options.map((row) => row.value);
          els.persistedResultSelect.value = 'https://evinaeva.github.io/|run-shared';
          els.persistedResultSelect.dispatch('change');
          setTimeout(() => {
            const latestIssuesCall = [...calls].reverse().find((url) => url.includes('/api/issues?')) || '';
            console.log(JSON.stringify({ optionValues, latestIssuesCall }));
          }, 0);
        }, 0);
        """
    )
    out = _run_node_json(script)
    assert "https://evinaeva.github.io/|run-shared" in out["optionValues"]
    assert "domain=https%3A%2F%2Fevinaeva.github.io%2F" in out["latestIssuesCall"]
    assert "run_id=run-shared" in out["latestIssuesCall"]


def test_index_runtime_handles_empty_persisted_results_state():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          const el = {
            id,
            value: '',
            textContent: '',
            innerHTML: '',
            disabled: false,
            children: [],
            className: '',
            classList: {
              add(name){ classes.add(name); },
              remove(name){ classes.delete(name); },
              toggle(name, force){ if (force === true) classes.add(name); else if (force === false) classes.delete(name); },
            },
            appendChild(child){ this.children.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            querySelector(){ return makeElement('qs'); },
          };
          Object.defineProperty(el, 'options', { get(){ return this.children; } });
          return el;
        }

        const ids = ['applyIssueQuery','exportIssuesCsv','issueQuery','domainSelect','domainInput','persistedResultSelect','refreshPersistedResults','runIdInput','languageFilter','severityFilter','typeFilter','stateFilter','urlFilter','domainFilter','issuesTable','issueStatus','issueCount','targetLanguageSummary','targetLanguageHeader','issuesBackToCheckLanguages','workflowContextSummary'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        els.issuesTable.querySelector = () => makeElement('tbody');

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          Intl,
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
          },
          window: { location: { search: '?domain=example.com' }, history: { replaceState(){} } },
          safeReadPayload: async (response) => response.json(),
          fetch: async (url) => {
            if (url === '/api/domains') return { ok: true, status: 200, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/issues/results?')) {
              return { ok: true, status: 200, json: async () => ({ results: [] }) };
            }
            throw new Error('Unexpected URL: ' + url);
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/index.js', 'utf8'), sandbox);

        setTimeout(() => {
          console.log(JSON.stringify({
            optionText: els.persistedResultSelect.options[0] ? els.persistedResultSelect.options[0].textContent : '',
            selectDisabled: els.persistedResultSelect.disabled,
            statusText: els.issueStatus.textContent,
          }));
        }, 0);
        """
    )
    out = _run_node_json(script)
    assert out["optionText"] == "No persisted results available"
    assert out["selectDisabled"] is True
    assert "No persisted issue results found" in out["statusText"]


def test_index_runtime_empty_state_surfaces_searched_domains_diagnostics():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          const el = {
            id,
            value: '',
            textContent: '',
            innerHTML: '',
            disabled: false,
            children: [],
            className: '',
            classList: {
              add(name){ classes.add(name); },
              remove(name){ classes.delete(name); },
              toggle(name, force){ if (force === true) classes.add(name); else if (force === false) classes.delete(name); },
            },
            appendChild(child){ this.children.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            querySelector(){ return makeElement('qs'); },
          };
          Object.defineProperty(el, 'options', { get(){ return this.children; } });
          return el;
        }

        const ids = ['applyIssueQuery','exportIssuesCsv','issueQuery','domainSelect','domainInput','persistedResultSelect','refreshPersistedResults','runIdInput','languageFilter','severityFilter','typeFilter','stateFilter','urlFilter','domainFilter','issuesTable','issueStatus','issueCount','targetLanguageSummary','targetLanguageHeader','issuesBackToCheckLanguages','workflowContextSummary'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        els.issuesTable.querySelector = () => makeElement('tbody');

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          Intl,
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
          },
          window: { location: { search: '?domain=https://evinaeva.github.io/polyglot-watchdog-testsite/en/index.html' }, history: { replaceState(){} } },
          safeReadPayload: async (response) => response.json(),
          fetch: async (url) => {
            if (url === '/api/domains') return { ok: true, status: 200, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/issues/results?')) {
              return {
                ok: true,
                status: 200,
                json: async () => ({ results: [], diagnostics: { searched_domains: ['https://evinaeva.github.io/polyglot-watchdog-testsite/en/index.html', 'https://evinaeva.github.io/'] } }),
              };
            }
            throw new Error('Unexpected URL: ' + url);
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/index.js', 'utf8'), sandbox);

        setTimeout(() => {
          console.log(JSON.stringify({ statusText: els.issueStatus.textContent }));
        }, 0);
        """
    )
    out = _run_node_json(script)
    assert "Searched domains:" in out["statusText"]
    assert "https://evinaeva.github.io/" in out["statusText"]


def test_index_domain_change_auto_loads_newest_result_for_new_domain():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          const el = {
            id,
            value: '',
            textContent: '',
            innerHTML: '',
            disabled: false,
            children: [],
            className: '',
            classList: {
              add(name){ classes.add(name); },
              remove(name){ classes.delete(name); },
              toggle(name, force){ if (force === true) classes.add(name); else if (force === false) classes.delete(name); },
              contains(name){ return classes.has(name); },
            },
            appendChild(child){ this.children.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            querySelector(){ return makeElement('qs'); },
          };
          Object.defineProperty(el, 'options', { get(){ return this.children; } });
          return el;
        }

        const ids = ['applyIssueQuery','exportIssuesCsv','issueQuery','domainSelect','domainInput','persistedResultSelect','refreshPersistedResults','runIdInput','languageFilter','severityFilter','typeFilter','stateFilter','urlFilter','domainFilter','issuesTable','issueStatus','issueCount','targetLanguageSummary','targetLanguageHeader','issuesBackToCheckLanguages','workflowContextSummary'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        const tbody = makeElement('tbody');
        els.issuesTable.querySelector = () => tbody;

        const calls = [];
        const sandbox = {
          console,
          URL,
          URLSearchParams,
          Intl,
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
          },
          window: { location: { search: '?domain=domain-a' }, history: { replaceState(){} } },
          safeReadPayload: async (response) => response.json(),
          fetch: async (url) => {
            calls.push(url);
            if (url === '/api/domains') return { ok: true, status: 200, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/issues/results?')) {
              if (url.includes('domain=domain-a')) {
                return { ok: true, status: 200, json: async () => ({ results: [
                  { run_id: 'a-run-1', created_at: '2026-03-01T10:00:00Z', display_label: 'A1' },
                ]}) };
              }
              return { ok: true, status: 200, json: async () => ({ results: [
                { run_id: 'b-run-new', created_at: '2026-03-03T10:00:00Z', display_label: 'B-new' },
                { run_id: 'b-run-old', created_at: '2026-03-02T10:00:00Z', display_label: 'B-old' },
              ]}) };
            }
            if (url.startsWith('/api/issues?')) {
              return { ok: true, status: 200, json: async () => ({ issues: [{ id: '1', message: 'x', evidence: { url: 'https://example.com' } }], count: 1 }) };
            }
            throw new Error('Unexpected URL: ' + url);
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/index.js', 'utf8'), sandbox);

        setTimeout(() => {
          els.domainInput.value = 'domain-b';
          els.domainInput.dispatch('input');
          setTimeout(() => {
            const latestIssuesCall = [...calls].reverse().find((url) => url.includes('/api/issues?')) || '';
            console.log(JSON.stringify({
              selectedRunId: els.runIdInput.value,
              latestIssuesCall,
            }));
          }, 0);
        }, 0);
        """
    )
    out = _run_node_json(script)
    assert out["selectedRunId"] == "b-run-new"
    assert "domain=domain-b" in out["latestIssuesCall"]
    assert "run_id=b-run-new" in out["latestIssuesCall"]


def test_index_domain_change_to_empty_results_clears_stale_issue_table():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          const el = {
            id,
            value: '',
            textContent: '',
            _innerHTML: '',
            disabled: false,
            children: [],
            className: '',
            classList: {
              add(name){ classes.add(name); },
              remove(name){ classes.delete(name); },
              toggle(name, force){ if (force === true) classes.add(name); else if (force === false) classes.delete(name); },
              contains(name){ return classes.has(name); },
            },
            appendChild(child){ this.children.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            querySelector(){ return makeElement('qs'); },
          };
          Object.defineProperty(el, 'innerHTML', {
            get(){ return this._innerHTML || ''; },
            set(v){ this._innerHTML = v; if (v === '') this.children = []; },
          });
          Object.defineProperty(el, 'options', { get(){ return this.children; } });
          return el;
        }

        const ids = ['applyIssueQuery','exportIssuesCsv','issueQuery','domainSelect','domainInput','persistedResultSelect','refreshPersistedResults','runIdInput','languageFilter','severityFilter','typeFilter','stateFilter','urlFilter','domainFilter','issuesTable','issueStatus','issueCount','targetLanguageSummary','targetLanguageHeader','issuesBackToCheckLanguages','workflowContextSummary'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        const tbody = makeElement('tbody');
        els.issuesTable.querySelector = () => tbody;

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          Intl,
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
          },
          window: { location: { search: '?domain=domain-a' }, history: { replaceState(){} } },
          safeReadPayload: async (response) => response.json(),
          fetch: async (url) => {
            if (url === '/api/domains') return { ok: true, status: 200, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/issues/results?')) {
              if (url.includes('domain=domain-a')) {
                return { ok: true, status: 200, json: async () => ({ results: [{ run_id: 'a-run', created_at: '2026-03-01T10:00:00Z' }] }) };
              }
              return { ok: true, status: 200, json: async () => ({ results: [] }) };
            }
            if (url.startsWith('/api/issues?')) {
              return { ok: true, status: 200, json: async () => ({ issues: [{ id: '1', message: 'stale', evidence: { url: 'https://example.com' } }], count: 1 }) };
            }
            throw new Error('Unexpected URL: ' + url);
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/index.js', 'utf8'), sandbox);

        setTimeout(() => {
          setTimeout(() => {
            tbody.appendChild(makeElement('stale-row'));
            const hadRowsBefore = tbody.children.length > 0;
            els.domainInput.value = 'domain-empty';
            els.domainInput.dispatch('input');
            setTimeout(() => {
              console.log(JSON.stringify({
                hadRowsBefore,
                rowsAfter: tbody.children.length,
                tableHidden: els.issuesTable.classList.contains('hidden'),
                issueCountHidden: els.issueCount.classList.contains('hidden'),
                issueCountText: els.issueCount.textContent,
                statusText: els.issueStatus.textContent,
              }));
            }, 0);
          }, 0);
        }, 0);
        """
    )
    out = _run_node_json(script)
    assert out["hadRowsBefore"] is True
    assert out["rowsAfter"] == 0
    assert out["tableHidden"] is True
    assert out["issueCountHidden"] is True
    assert out["issueCountText"] == ""
    assert "No persisted issue results found" in out["statusText"]


def test_index_runtime_renders_source_target_issue_and_links():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          const el = {
            id,
            value: '',
            href: '',
            textContent: '',
            _innerHTML: '',
            disabled: false,
            children: [],
            className: '',
            classList: {
              add(name){ classes.add(name); },
              remove(name){ classes.delete(name); },
              toggle(name, force){ if (force === true) classes.add(name); else if (force === false) classes.delete(name); },
              contains(name){ return classes.has(name); },
            },
            appendChild(child){ this.children.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            click(){ if (listeners.click) return listeners.click({ target: this }); },
            querySelector(){ return makeElement('qs'); },
          };
          Object.defineProperty(el, 'innerHTML', {
            get(){ return this._innerHTML; },
            set(value){ this._innerHTML = value; },
          });
          Object.defineProperty(el, 'options', { get(){ return this.children; } });
          return el;
        }

        const ids = ['applyIssueQuery','exportIssuesCsv','issueQuery','domainSelect','domainInput','persistedResultSelect','refreshPersistedResults','runIdInput','languageFilter','severityFilter','typeFilter','stateFilter','urlFilter','domainFilter','issuesTable','issueStatus','issueCount','targetLanguageSummary','targetLanguageHeader','issuesBackToCheckLanguages','workflowContextSummary'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        const tbody = makeElement('tbody');
        els.issuesTable.querySelector = () => tbody;

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          Intl,
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
          },
          window: { location: { search: '?domain=example.com' }, history: { replaceState(){} } },
          safeReadPayload: async (response) => response.json(),
          fetch: async (url) => {
            if (url === '/api/domains') return { ok: true, status: 200, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/issues/results?')) {
              return { ok: true, status: 200, json: async () => ({ results: [{ run_id: 'run-1', created_at: '2026-03-02T10:00:00Z', display_label: 'R1' }] }) };
            }
            if (url.startsWith('/api/issues?')) {
              return { ok: true, status: 200, json: async () => ({ issues: [{
                id: '1',
                message: 'Mismatch',
                language: 'ru',
                confidence: 0.93,
                evidence: { url: 'https://example.com/a', source_text: 'Hello', target_text: 'Привет' },
              }], count: 1 }) };
            }
            throw new Error('Unexpected URL: ' + url);
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/index.js', 'utf8'), sandbox);

        setTimeout(() => {
          const row = tbody.children[0];
          const cellTexts = row ? row.children.map((cell) => cell.textContent || '') : [];
          const linksCell = row && row.children[3] ? row.children[3] : null;
          const linkHrefs = linksCell ? linksCell.children.map((child) => child.href || '').filter(Boolean) : [];
          console.log(JSON.stringify({
            cellTexts,
            linkHrefs,
            targetHeader: els.targetLanguageHeader.textContent,
            targetSummary: els.targetLanguageSummary.textContent,
          }));
        }, 0);
        """
    )
    out = _run_node_json(script)
    assert out["cellTexts"][:3] == ["Hello", "Привет", "Mismatch"]
    assert len(out["linkHrefs"]) == 2
    assert out["linkHrefs"][1] == "https://example.com/a"
    assert out["targetHeader"] == "ru"
    assert out["targetSummary"] == "Target language: RU"


def test_index_runtime_blocks_non_http_external_url_links():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const el = {
            id,
            value: '',
            href: '',
            textContent: '',
            children: [],
            className: '',
            classList: { add(){}, remove(){}, toggle(){}, contains(){ return false; } },
            appendChild(child){ this.children.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            querySelector(){ return makeElement('qs'); },
          };
          Object.defineProperty(el, 'options', { get(){ return this.children; } });
          return el;
        }

        const ids = ['applyIssueQuery','exportIssuesCsv','issueQuery','domainSelect','domainInput','persistedResultSelect','refreshPersistedResults','runIdInput','languageFilter','severityFilter','typeFilter','stateFilter','urlFilter','domainFilter','issuesTable','issueStatus','issueCount','targetLanguageSummary','targetLanguageHeader','issuesBackToCheckLanguages','workflowContextSummary'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        const tbody = makeElement('tbody');
        els.issuesTable.querySelector = () => tbody;

        const sandbox = {
          console,
          URL,
          URLSearchParams,
          Intl,
          document: { getElementById: (id) => els[id], createElement: () => makeElement('created') },
          window: { location: { search: '?domain=example.com' }, history: { replaceState(){} } },
          safeReadPayload: async (response) => response.json(),
          fetch: async (url) => {
            if (url === '/api/domains') return { ok: true, status: 200, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/issues/results?')) return { ok: true, status: 200, json: async () => ({ results: [{ run_id: 'run-1' }] }) };
            if (url.startsWith('/api/issues?')) return { ok: true, status: 200, json: async () => ({ issues: [{ id: '1', message: 'X', language: 'ru', evidence: { url: 'javascript:alert(1)' } }], count: 1 }) };
            throw new Error('Unexpected URL: ' + url);
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/index.js', 'utf8'), sandbox);
        setTimeout(() => {
          const row = tbody.children[0];
          const linksCell = row && row.children[4] ? row.children[4] : null;
          const linksCount = linksCell ? linksCell.children.length : 0;
          const hrefs = linksCell ? linksCell.children.map((node) => node.href || '') : [];
          console.log(JSON.stringify({ linksCount, hrefs }));
        }, 0);
        """
    )
    out = _run_node_json(script)
    assert out["linksCount"] == 1
    assert "/issues/detail?" in out["hrefs"][0]


def test_index_refresh_empty_results_clears_stale_issue_table():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');

        function makeElement(id='') {
          const listeners = {};
          const classes = new Set();
          const el = {
            id,
            value: '',
            textContent: '',
            _innerHTML: '',
            disabled: false,
            children: [],
            className: '',
            classList: {
              add(name){ classes.add(name); },
              remove(name){ classes.delete(name); },
              toggle(name, force){ if (force === true) classes.add(name); else if (force === false) classes.delete(name); },
              contains(name){ return classes.has(name); },
            },
            appendChild(child){ this.children.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            dispatch(type){ if (listeners[type]) return listeners[type]({ target: this }); },
            click(){ if (listeners.click) return listeners.click({ target: this }); },
            querySelector(){ return makeElement('qs'); },
          };
          Object.defineProperty(el, 'innerHTML', {
            get(){ return this._innerHTML || ''; },
            set(v){ this._innerHTML = v; if (v === '') this.children = []; },
          });
          Object.defineProperty(el, 'options', { get(){ return this.children; } });
          return el;
        }

        const ids = ['applyIssueQuery','exportIssuesCsv','issueQuery','domainSelect','domainInput','persistedResultSelect','refreshPersistedResults','runIdInput','languageFilter','severityFilter','typeFilter','stateFilter','urlFilter','domainFilter','issuesTable','issueStatus','issueCount','targetLanguageSummary','targetLanguageHeader','issuesBackToCheckLanguages','workflowContextSummary'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        const tbody = makeElement('tbody');
        els.issuesTable.querySelector = () => tbody;

        let resultsCallCount = 0;
        const sandbox = {
          console,
          URL,
          URLSearchParams,
          Intl,
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
          },
          window: { location: { search: '?domain=domain-a' }, history: { replaceState(){} } },
          safeReadPayload: async (response) => response.json(),
          fetch: async (url) => {
            if (url === '/api/domains') return { ok: true, status: 200, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/issues/results?')) {
              resultsCallCount += 1;
              if (resultsCallCount === 1) {
                return { ok: true, status: 200, json: async () => ({ results: [{ run_id: 'a-run', created_at: '2026-03-01T10:00:00Z' }] }) };
              }
              return { ok: true, status: 200, json: async () => ({ results: [] }) };
            }
            if (url.startsWith('/api/issues?')) {
              return { ok: true, status: 200, json: async () => ({ issues: [{ id: '1', message: 'stale', evidence: { url: 'https://example.com' } }], count: 1 }) };
            }
            throw new Error('Unexpected URL: ' + url);
          },
        };

        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/index.js', 'utf8'), sandbox);

        setTimeout(() => {
          const hadRowsBefore = tbody.children.length > 0;
          els.refreshPersistedResults.click();
          setTimeout(() => {
            console.log(JSON.stringify({
              hadRowsBefore,
              rowsAfter: tbody.children.length,
              tableHidden: els.issuesTable.classList.contains('hidden'),
              issueCountHidden: els.issueCount.classList.contains('hidden'),
              issueCountText: els.issueCount.textContent,
              statusText: els.issueStatus.textContent,
            }));
          }, 0);
        }, 0);
        """
    )
    out = _run_node_json(script)
    assert out["hadRowsBefore"] is True
    assert out["rowsAfter"] == 0
    assert out["tableHidden"] is True
    assert out["issueCountHidden"] is True
    assert out["issueCountText"] == ""
    assert "No persisted issue results found" in out["statusText"]


def test_index_runtime_target_language_header_uses_deterministic_frequency_not_row_order():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');
        function makeElement(id='') {
          const listeners = {};
          const el = {
            id, value: '', href: '', textContent: '', children: [], className: '', disabled: false,
            classList: { add(){}, remove(){}, toggle(){}, contains(){ return false; } },
            appendChild(child){ this.children.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            querySelector(){ return makeElement('qs'); },
          };
          Object.defineProperty(el, 'options', { get(){ return this.children; } });
          return el;
        }
        const ids = ['applyIssueQuery','exportIssuesCsv','issueQuery','domainSelect','domainInput','persistedResultSelect','refreshPersistedResults','runIdInput','languageFilter','severityFilter','typeFilter','stateFilter','urlFilter','domainFilter','issuesTable','issueStatus','issueCount','targetLanguageSummary','targetLanguageHeader','issuesBackToCheckLanguages','workflowContextSummary'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        const tbody = makeElement('tbody');
        els.issuesTable.querySelector = () => tbody;
        const sandbox = {
          console, URL, URLSearchParams, Intl,
          document: { getElementById: (id) => els[id], createElement: () => makeElement('created') },
          window: { location: { search: '?domain=example.com' }, history: { replaceState(){} } },
          safeReadPayload: async (response) => response.json(),
          fetch: async (url) => {
            if (url === '/api/domains') return { ok: true, status: 200, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/issues/results?')) return { ok: true, status: 200, json: async () => ({ results: [{ run_id: 'run-1' }] }) };
            if (url.startsWith('/api/issues?')) return { ok: true, status: 200, json: async () => ({ issues: [
              { id: '1', language: 'es', evidence: { url: 'https://x/a' } },
              { id: '2', language: 'fr', evidence: { url: 'https://x/b' } },
              { id: '3', language: 'fr', evidence: { url: 'https://x/c' } },
            ], count: 3, target_language: '' }) };
            throw new Error('Unexpected URL: ' + url);
          },
        };
        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/index.js', 'utf8'), sandbox);
        setTimeout(() => console.log(JSON.stringify({ targetHeader: els.targetLanguageHeader.textContent })), 0);
        """
    )
    out = _run_node_json(script)
    assert out["targetHeader"] == "fr"


def test_index_runtime_uses_schema_aliases_for_source_target():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');
        function makeElement(id='') {
          const listeners = {};
          const el = {
            id, value: '', href: '', textContent: '', children: [], className: '', disabled: false,
            classList: { add(){}, remove(){}, toggle(){}, contains(){ return false; } },
            appendChild(child){ this.children.push(child); return child; },
            addEventListener(type, cb){ listeners[type] = cb; },
            querySelector(){ return makeElement('qs'); },
          };
          Object.defineProperty(el, 'options', { get(){ return this.children; } });
          return el;
        }
        const ids = ['applyIssueQuery','exportIssuesCsv','issueQuery','domainSelect','domainInput','persistedResultSelect','refreshPersistedResults','runIdInput','languageFilter','severityFilter','typeFilter','stateFilter','urlFilter','domainFilter','issuesTable','issueStatus','issueCount','targetLanguageSummary','targetLanguageHeader','issuesBackToCheckLanguages','workflowContextSummary'];
        const els = Object.fromEntries(ids.map((id) => [id, makeElement(id)]));
        const tbody = makeElement('tbody');
        els.issuesTable.querySelector = () => tbody;
        const sandbox = {
          console, URL, URLSearchParams, Intl,
          document: { getElementById: (id) => els[id], createElement: () => makeElement('created') },
          window: { location: { search: '?domain=example.com' }, history: { replaceState(){} } },
          safeReadPayload: async (response) => response.json(),
          fetch: async (url) => {
            if (url === '/api/domains') return { ok: true, status: 200, json: async () => ({ items: ['example.com'] }) };
            if (url.startsWith('/api/issues/results?')) return { ok: true, status: 200, json: async () => ({ results: [{ run_id: 'run-1' }] }) };
            if (url.startsWith('/api/issues?')) return { ok: true, status: 200, json: async () => ({ issues: [{
              id: '1', message: 'legacy', target_language: 'ru',
              evidence: { url: 'https://example.com', original_text: 'Hello', translation: 'Привет' },
            }], count: 1 }) };
            throw new Error('Unexpected URL: ' + url);
          },
        };
        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/index.js', 'utf8'), sandbox);
        setTimeout(() => {
          const row = tbody.children[0];
          const cells = row ? row.children.map((cell) => cell.textContent || '') : [];
          console.log(JSON.stringify({ cells }));
        }, 0);
        """
    )
    out = _run_node_json(script)
    assert out["cells"][:3] == ["Hello", "Привет", "legacy"]


def test_issue_detail_runtime_escapes_untrusted_fields_and_blocks_unsafe_screenshot_href():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');
        function makeElement(id='') {
          const listeners = {};
          const el = {
            id, value: '', href: '', textContent: '', className: '', children: [],
            appendChild(child){ this.children.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            addEventListener(type, cb){ listeners[type] = cb; },
          };
          return el;
        }
        const els = {
          issueDetailStatus: makeElement('issueDetailStatus'),
          issueCore: makeElement('issueCore'),
          issueEvidence: makeElement('issueEvidence'),
          detailBackToIssues: makeElement('detailBackToIssues'),
          detailOpenContexts: makeElement('detailOpenContexts'),
          detailOpenPulls: makeElement('detailOpenPulls'),
        };
        const sandbox = {
          console, URL, URLSearchParams,
          window: { location: { search: '?domain=example.com&run_id=run-1&id=i1' } },
          document: {
            getElementById: (id) => els[id],
            createElement: () => makeElement('created'),
            createTextNode: (text) => ({ textContent: String(text || '') }),
          },
          safeReadPayload: async (response) => response.json(),
          fetch: async () => ({ ok: true, status: 200, json: async () => ({
            issue: {
              id: 'i1',
              message: '<img src=x onerror=alert(1)>',
              evidence: { url: 'https://example.com/x', source_text: '<b>Hello</b>', target_text: '<script>x</script>' },
            },
            drilldown: {
              screenshot_view_url: 'javascript:alert(1)',
              page: { unsafe: '</pre><script>alert(1)</script>' },
              element: { unsafe: '<img src=x onerror=1>' },
            },
          }) }),
        };
        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('web/static/issues-detail.js', 'utf8'), sandbox);
        setTimeout(() => {
          const evidenceLine = els.issueEvidence.children.find((node) => node.textContent === 'Screenshot: ');
          const hasUnsafeHref = !!(evidenceLine && evidenceLine.children && evidenceLine.children.find((child) => String(child.href || '').startsWith('javascript:')));
          const preNodes = els.issueEvidence.children.filter((node) => String(node.textContent || '').includes('unsafe'));
          console.log(JSON.stringify({
            hasUnsafeHref,
            preNodeCount: preNodes.length,
            status: els.issueDetailStatus.textContent,
          }));
        }, 0);
        """
    )
    out = _run_node_json(script)
    assert out["hasUnsafeHref"] is False
    assert out["preNodeCount"] >= 2
    assert out["status"] == "Issue detail loaded."


def test_issue_detail_runtime_allows_only_https_http_or_single_slash_local_screenshot_links():
    script = textwrap.dedent(
        r"""
        const fs = require('fs');
        const vm = require('vm');
        function makeElement(id='') {
          const listeners = {};
          return {
            id, value: '', href: '', textContent: '', className: '', children: [],
            appendChild(child){ this.children.push(child); return child; },
            append(...nodes){ this.children.push(...nodes); },
            addEventListener(type, cb){ listeners[type] = cb; },
          };
        }
        async function runCase(screenshotHref) {
          const els = {
            issueDetailStatus: makeElement('issueDetailStatus'),
            issueCore: makeElement('issueCore'),
            issueEvidence: makeElement('issueEvidence'),
            detailBackToIssues: makeElement('detailBackToIssues'),
            detailOpenContexts: makeElement('detailOpenContexts'),
            detailOpenPulls: makeElement('detailOpenPulls'),
          };
          const sandbox = {
            console, URL, URLSearchParams,
            window: { location: { search: '?domain=example.com&run_id=run-1&id=i1' } },
            document: {
              getElementById: (id) => els[id],
              createElement: () => makeElement('created'),
              createTextNode: (text) => ({ textContent: String(text || '') }),
            },
            safeReadPayload: async (response) => response.json(),
            fetch: async () => ({ ok: true, status: 200, json: async () => ({
              issue: { id: 'i1', message: 'ok', evidence: { url: 'https://example.com/x' } },
              drilldown: { screenshot_view_url: screenshotHref, page: {}, element: {} },
            }) }),
          };
          vm.createContext(sandbox);
          vm.runInContext(fs.readFileSync('web/static/issues-detail.js', 'utf8'), sandbox);
          await new Promise((resolve) => setTimeout(resolve, 0));
          const line = els.issueEvidence.children.find((node) => node.textContent === 'Screenshot: ');
          const hasLink = !!(line && line.children && line.children.some((child) => !!child.href));
          return hasLink;
        }
        (async () => {
          const localAllowed = await runCase('/api/page-screenshot?domain=example.com&run_id=run-1&page_id=p1');
          const httpsAllowed = await runCase('https://cdn.example.com/shot.png');
          const schemeRelativeBlocked = await runCase('//evil.example/x');
          console.log(JSON.stringify({ localAllowed, httpsAllowed, schemeRelativeBlocked }));
        })().catch((err) => { console.error(err); process.exit(1); });
        """
    )
    out = _run_node_json(script)
    assert out["localAllowed"] is True
    assert out["httpsAllowed"] is True
    assert out["schemeRelativeBlocked"] is False
