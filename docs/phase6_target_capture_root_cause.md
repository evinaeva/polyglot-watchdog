# Phase 6 check-languages target capture timeout audit

This document captures a code-level audit of the `failed_before_llm / running_target_capture_failed` path and explains why increasing timeout in other areas does not change the failing `page.screenshot(full_page=True)` call.

Key conclusion: the replay path reaches `page.screenshot(full_page=True)` without any explicit screenshot timeout and without any page/context default timeout override, so Playwright's default action timeout (30s) applies to screenshot regardless of navigation timeout changes.
