# /urls Button Feedback UX Update

## Updated buttons and files
- Updated top action buttons on `/urls`: **Load**, **Replace list**, **Add to list**, **Clear** in `web/static/urls.js`.
- Updated per-row action buttons on `/urls`: **Save**, **Delete** in `web/static/urls.js`.
- Added visual and accessibility support styles for interaction/active/focus/error/success states in `web/static/styles.css`.
- Added a non-color success/error confirmation region (`#statusBox`) with live-region semantics in `web/templates/urls.html`.
- Added localized labels/messages for loading/success/error feedback in `web/static/locales/en.json` and `web/static/locales/ru.json`.

## Save behavior: success/failure and timing
- Save now enters a loading state immediately on click (`Saving...`, disabled, `aria-busy=true`).
- On successful save response from `/api/seed-urls/row-upsert`, Save switches to a green success state and text becomes `Saved`.
- `Saved` persists for **2000 ms** (`SAVE_SUCCESS_TIMEOUT_MS = 2000`) and can also reset earlier if the row is edited (dirty-like reset on URL/recipe/active changes).
- If save fails, the Save button shows a temporary error state (`Failed`), `Saved` is not shown, and a clear error message is surfaced in the error box/status region.

## Feedback added for other buttons
- **Immediate click feedback** for `/urls` action buttons via `.ui-action-button:active` press animation (slight scale-down).
- **Async feedback** for non-save actions:
  - Loading state labels (e.g., `Loading...`, `Applying...`, `Deleting...`).
  - Temporary success labels (e.g., `Loaded`, `Applied`, `Added`, `Cleared`) after completion.
  - Error labels (`Failed`) and error/status messages on request failure.
- Added a status line (`#statusBox`) so feedback is not color-only and is announced to assistive tech (`role="status"`, `aria-live="polite"`).

## Manual test steps
1. Open `/urls`.
2. Click **Load**:
   - Verify button text changes to `Loading...` and then `Loaded`, then resets.
   - Verify status message appears (`URLs loaded.`).
3. Make/edit a row and click **Save**:
   - Verify `Saving...` appears during request.
   - Verify green `Saved` state on success.
   - Verify `Saved` remains visible ~2 seconds.
4. While `Saved` is shown, edit URL/recipe/active in that row:
   - Verify Save returns to default `Save` immediately.
5. Click **Replace list**, **Add to list**, **Clear**, and row **Delete**:
   - Verify immediate press animation on click.
   - Verify loading labels during request.
   - Verify temporary completion state + status message on success.
6. Failure case (simulate bad request/domain or unavailable backend):
   - Verify button shows `Failed` (not success label), and error text is shown in error/status regions.
7. Keyboard accessibility:
   - Tab to each button and verify visible `:focus-visible` outline.
   - Activate buttons via keyboard (Enter/Space) and verify the same feedback states.
8. Reduced motion:
   - Enable `prefers-reduced-motion: reduce` in OS/devtools.
   - Verify press/transition animation is removed/simplified while state text/status feedback remains.
