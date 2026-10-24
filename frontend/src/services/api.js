const API_BASE = '/api';

export async function auditProduct(query, forceRefresh = false, profile = 'general_health', strictPalmOil = false, goals = [], shareOfDaily = 0.15) {
  try {
    const response = await fetch(`${API_BASE}/audit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        force_refresh: forceRefresh,
        profile,
        strict_palm_oil: strictPalmOil,
        goals,
        share_of_daily: shareOfDaily,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Audit request failed with status ${response.status}`);
    }

    return await response.json();
  } catch (err) {
    if (err.name === 'TypeError' || err.message?.includes('NetworkError') || err.message?.includes('Failed to fetch')) {
      throw new Error('Cannot connect to backend server. Please ensure FastAPI is running on port 8000 (uvicorn app.main:app --app-dir backend --port 8000).');
    }
    throw err;
  }
}

export async function auditWithImage(imageFile, forceRefresh = false) {
  try {
    const formData = new FormData();
    formData.append('file', imageFile);
    formData.append('force_refresh', forceRefresh);

    const response = await fetch(`${API_BASE}/audit-image`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Image audit failed with status ${response.status}`);
    }

    return await response.json();
  } catch (err) {
    if (err.name === 'TypeError' || err.message?.includes('NetworkError') || err.message?.includes('Failed to fetch')) {
      throw new Error('Cannot connect to backend server. Please ensure FastAPI is running on port 8000.');
    }
    throw err;
  }
}

export async function detectProductFromImage(imageFile) {
  try {
    const formData = new FormData();
    formData.append('file', imageFile);

    const response = await fetch(`${API_BASE}/detect-image`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Could not recognize product from image.');
    }

    return await response.json();
  } catch (err) {
    if (err.name === 'TypeError' || err.message?.includes('NetworkError') || err.message?.includes('Failed to fetch')) {
      throw new Error('Cannot connect to backend server. Please ensure FastAPI is running on port 8000.');
    }
    throw err;
  }
}

export async function fetchEvidenceLogs(limit = 30, offset = 0) {
  try {
    const response = await fetch(`${API_BASE}/evidence-logs?limit=${limit}&offset=${offset}`);
    if (!response.ok) {
      throw new Error('Failed to retrieve evidence logs');
    }
    return await response.json();
  } catch (err) {
    if (err.name === 'TypeError' || err.message?.includes('NetworkError') || err.message?.includes('Failed to fetch')) {
      throw new Error('Cannot connect to backend server. Please ensure FastAPI is running on port 8000.');
    }
    throw err;
  }
}

export async function calculatePersonalizedScore(
  productData,
  conditions = ['general_health'],
  userAllergens = [],
  preferences = [],
  avoidedIngredients = [],
  preferredIngredients = []
) {
  try {
    // If first argument is an options object
    const payload = productData && typeof productData === 'object' && productData.product_data
      ? productData
      : {
          product_data: productData,
          conditions: Array.isArray(conditions) ? conditions : [conditions || 'general_health'],
          user_allergens: userAllergens,
          preferences,
          avoided_ingredients: avoidedIngredients,
          preferred_ingredients: preferredIngredients,
        };

    const response = await fetch(`${API_BASE}/score-personal`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Failed to compute personalized rating and match score.');
    }

    return await response.json();
  } catch (err) {
    console.error('Error in calculatePersonalizedScore:', err);
    throw err;
  }
}

export async function fetchReferenceStandards(shareOfDaily = 0.15) {
  try {
    const response = await fetch(`${API_BASE}/reference-standards?share_of_daily=${shareOfDaily}`);
    if (!response.ok) {
      throw new Error('Failed to fetch reference standards');
    }
    return await response.json();
  } catch (err) {
    console.error('Error fetching reference standards:', err);
    throw err;
  }
}

export async function checkBackendHealth() {
  try {
    const response = await fetch(`${API_BASE}/health`);
    if (!response.ok) {
      throw new Error('Backend health check failed');
    }
    return await response.json();
  } catch (err) {
    if (err.name === 'TypeError' || err.message?.includes('NetworkError') || err.message?.includes('Failed to fetch')) {
      throw new Error('Cannot connect to backend server. Please ensure FastAPI is running on port 8000.');
    }
    throw err;
  }
}
