const API_BASE = '/api';

export async function auditProduct(
  query,
  forceRefresh = false,
  profile = 'general_health',
  shareOfDaily = 0.15,
  conditions = null,
  userAllergens = null,
  avoidIngredients = null,
  dietaryPattern = 'none',
  nutritionGoals = null
) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

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
        share_of_daily: shareOfDaily,
        conditions: conditions || (profile ? [profile] : ['general_health']),
        user_allergens: userAllergens || [],
        avoid_ingredients: avoidIngredients || [],
        dietary_pattern: dietaryPattern || 'none',
        nutrition_goals: nutritionGoals || [],
      }),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Audit request failed with status ${response.status}`);
    }

    return await response.json();
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Audit request timed out after 30 seconds. Please retry or check connection.');
    }
    if (err.name === 'TypeError' || err.message?.includes('NetworkError') || err.message?.includes('Failed to fetch')) {
      throw new Error('Cannot connect to backend server. Please ensure FastAPI is running on port 8000 (uvicorn app.main:app --app-dir backend --port 8000).');
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function auditWithImage(imageFile, forceRefresh = false) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 35000);

  try {
    const formData = new FormData();
    formData.append('file', imageFile);
    formData.append('force_refresh', forceRefresh);

    const response = await fetch(`${API_BASE}/audit-image`, {
      method: 'POST',
      body: formData,
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Image audit failed with status ${response.status}`);
    }

    return await response.json();
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Image audit timed out after 35 seconds. Please retry.');
    }
    if (err.name === 'TypeError' || err.message?.includes('NetworkError') || err.message?.includes('Failed to fetch')) {
      throw new Error('Cannot connect to backend server. Please ensure FastAPI is running on port 8000.');
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function detectProductFromImage(imageFile) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 20000);

  try {
    const formData = new FormData();
    formData.append('file', imageFile);

    const response = await fetch(`${API_BASE}/detect-image`, {
      method: 'POST',
      body: formData,
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Could not recognize product from image.');
    }

    return await response.json();
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Image detection timed out after 20 seconds.');
    }
    if (err.name === 'TypeError' || err.message?.includes('NetworkError') || err.message?.includes('Failed to fetch')) {
      throw new Error('Cannot connect to backend server. Please ensure FastAPI is running on port 8000.');
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function fetchEvidenceLogs(limit = 30, offset = 0) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(`${API_BASE}/evidence-logs?limit=${limit}&offset=${offset}`, {
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error('Failed to retrieve evidence logs');
    }
    return await response.json();
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Retrieving evidence logs timed out.');
    }
    if (err.name === 'TypeError' || err.message?.includes('NetworkError') || err.message?.includes('Failed to fetch')) {
      throw new Error('Cannot connect to backend server. Please ensure FastAPI is running on port 8000.');
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function apiGetIndependentEvidence(query = '', productName = '', brand = '', category = '') {
  try {
    const params = new URLSearchParams();
    if (query) params.append('query', query);
    if (productName) params.append('product_name', productName);
    if (brand) params.append('brand', brand);
    if (category) params.append('category', category);

    const response = await fetch(`${API_BASE}/independent-evidence?${params.toString()}`);
    if (!response.ok) {
      throw new Error('Failed to retrieve independent evidence.');
    }
    return await response.json();
  } catch (err) {
    console.warn('apiGetIndependentEvidence error:', err);
    return null;
  }
}

export async function calculatePersonalizedScore(
  productData,
  conditions = ['general_health'],
  userAllergens = [],
  avoidIngredients = [],
  dietaryPattern = 'none',
  nutritionGoals = []
) {
  try {
    const payload = productData && typeof productData === 'object' && productData.product_data
      ? {
          product_data: productData.product_data,
          conditions: productData.conditions || ['general_health'],
          user_allergens: productData.user_allergens || [],
          avoid_ingredients: productData.avoid_ingredients || avoidIngredients || [],
          dietary_pattern: productData.dietary_pattern || dietaryPattern || 'none',
          nutrition_goals: productData.nutrition_goals || nutritionGoals || [],
        }
      : {
          product_data: productData,
          conditions: Array.isArray(conditions) ? conditions : [conditions || 'general_health'],
          user_allergens: userAllergens || [],
          avoid_ingredients: avoidIngredients || [],
          dietary_pattern: dietaryPattern || 'none',
          nutrition_goals: nutritionGoals || [],
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
      throw new Error(errorData.detail || 'Failed to compute personalised rating.');
    }

    return await response.json();
  } catch (err) {
    console.error('Error in calculatePersonalizedScore:', err);
    throw err;
  }
}

export async function fetchProductAlternatives(
  productId,
  conditions = ['general_health'],
  userAllergens = [],
  productData = null
) {
  try {
    const payload = {
      conditions: Array.isArray(conditions) ? conditions : [conditions || 'general_health'],
      user_allergens: userAllergens || [],
      product_data: productData,
    };
    const response = await fetch(`${API_BASE}/products/${productId}/alternatives`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch alternatives');
    }
    return await response.json();
  } catch (err) {
    console.error('Error fetching product alternatives:', err);
    return null;
  }
}

export async function fetchReferenceStandards(shareOfDaily = 0.15) {
  try {
    const response = await fetch(`${API_BASE}/reference-standards?share_of_daily=${shareOfDaily}`);
    if (!response.ok) {
      throw new Error('Failed to load reference standards knowledge base');
    }
    return await response.json();
  } catch (err) {
    console.error('Error fetching reference standards:', err);
    throw err;
  }
}

// ============================================================================
// Auth & Personalisation APIs
// ============================================================================

export async function fetchProfileOptions() {
  try {
    const res = await fetch(`${API_BASE}/profile-options`);
    if (!res.ok) throw new Error('Failed to load profile options');
    return await res.json();
  } catch (err) {
    console.error('Error loading profile options:', err);
    throw err;
  }
}

export async function apiSignUp(userData) {
  const res = await fetch(`${API_BASE}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Sign up failed.');
  }
  return await res.json();
}

export async function apiLogIn(credentials) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Invalid email or password.');
  }
  return await res.json();
}

export async function apiGetMe(token) {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Session invalid');
  return await res.json();
}

export async function apiUpdateUser(data, token) {
  const res = await fetch(`${API_BASE}/auth/profile`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update profile.');
  }
  return await res.json();
}

export async function apiVerifyEmail(token) {
  const res = await fetch(`${API_BASE}/auth/verify-email`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to verify email');
  return await res.json();
}

export async function apiForgotPassword(email) {
  const res = await fetch(`${API_BASE}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  return await res.json();
}

export async function apiResetPassword(data) {
  const res = await fetch(`${API_BASE}/auth/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to reset password.');
  }
  return await res.json();
}

export async function apiSaveProfile(profileData, token = null) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/profile/save`, {
    method: 'POST',
    headers,
    body: JSON.stringify(profileData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to save profile.');
  }
  return await res.json();
}

export async function apiExportData(token) {
  const res = await fetch(`${API_BASE}/auth/export-data`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to export data');
  return await res.json();
}

export async function apiDeleteAccount(password, token) {
  const res = await fetch(`${API_BASE}/auth/account`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete account.');
  }
  return await res.json();
}

export async function apiGetSavedComparisons(token) {
  const res = await fetch(`${API_BASE}/saved-comparisons`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to fetch saved comparisons');
  return await res.json();
}

export async function apiCreateSavedComparison(data, token) {
  const res = await fetch(`${API_BASE}/saved-comparisons`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to save comparison');
  return await res.json();
}

export async function apiDeleteSavedComparison(id, token) {
  const res = await fetch(`${API_BASE}/saved-comparisons/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to delete comparison');
  return await res.json();
}
