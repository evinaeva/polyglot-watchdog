function buildCaptureReviewPayload(domain, runId, row, statusValue) {
  return {
    domain,
    run_id: runId,
    capture_context_id: row.capture_context_id,
    language: row.language || 'en',
    status: statusValue,
    reviewer: 'operator',
    timestamp: new Date().toISOString(),
  };
}

async function postCaptureReview(domain, runId, row, statusValue) {
  const payload = buildCaptureReviewPayload(domain, runId, row, statusValue);
  const response = await fetch('/api/capture/reviews', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await safeReadPayload(response);
  if (!response.ok) throw new Error(data.error || 'Failed to save review');
}
