from pathlib import Path


def test_check_languages_no_open_issues_api_button():
    template = Path('web/templates/check-languages.html').read_text(encoding='utf-8')
    assert 'Open issues API' not in template


def test_workflow_page_removed_controls_and_sections():
    template = Path('web/templates/workflow.html').read_text(encoding='utf-8')
    assert 'Refresh runs' not in template
    assert 'Technical details' not in template
    assert 'Advanced: dataset generation' not in template
    assert 'Prepare captured data' not in template


def test_workflow_script_no_removed_feature_handlers():
    script = Path('web/static/workflow.js').read_text(encoding='utf-8')
    assert 'wfRefreshRuns' not in script
    assert 'wfGenerateDataset' not in script
    assert 'wfPayload' not in script
    assert 'wfTransition' not in script


def test_check_languages_server_no_issues_api_link_placeholder():
    server = Path('app/skeleton_server.py').read_text(encoding='utf-8')
    assert 'issues_api_link' not in server


def test_pulls_page_no_manual_prepare_captured_data_control():
    template = Path('web/templates/pulls.html').read_text(encoding='utf-8')
    assert ('pullsPrepare' + 'CapturedData') not in template
    assert ('pullsPrepare' + 'CapturedDataStatus') not in template
    assert 'Prepare captured data' not in template


def test_pulls_script_no_manual_prepare_captured_data_wiring():
    script = Path('web/static/pulls.js').read_text(encoding='utf-8')
    assert ('pullsPrepare' + 'CapturedData') not in script
    assert ('pullsPrepare' + 'CapturedDataStatus') not in script
    assert ('triggerEligible' + 'DatasetGeneration') not in script
    assert 'Captured data prepared successfully' not in script
