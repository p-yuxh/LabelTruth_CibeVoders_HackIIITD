const API_BASE = '/api';

export async function auditProduct(query, forceRefresh = false) {
  const response = await fetch(`${API_BASE}/audit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      force_refresh: forceRefresh,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Audit request failed with status ${response.status}`);
  }

  return response.json();
}

export async function fetchEvidenceLogs(limit = 15, offset = 0) {
  const response = await fetch(`${API_BASE}/evidence-logs?limit=${limit}&offset=${offset}`);
  if (!response.ok) {
    throw new Error('Failed to retrieve evidence logs');
  }
  return response.json();
}

export async function checkBackendHealth() {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error('Backend health check failed');
  }
  return response.json();
}

