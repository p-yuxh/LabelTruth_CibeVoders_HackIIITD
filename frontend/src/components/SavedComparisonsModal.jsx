import React, { useState, useEffect } from 'react';
import { X, Bookmark, ExternalLink, Trash2, Clock, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { apiGetSavedComparisons, apiDeleteSavedComparison } from '../services/api';

export default function SavedComparisonsModal({ onSelectComparison }) {
  const { savedModalOpen, setSavedModalOpen, token, isLoggedIn, openAuth } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (savedModalOpen && token) {
      setLoading(true);
      setErrorMsg('');
      apiGetSavedComparisons(token)
        .then((res) => setItems(res || []))
        .catch((err) => setErrorMsg(err.message || 'Failed to load saved comparisons.'))
        .finally(() => setLoading(false));
    }
  }, [savedModalOpen, token]);

  if (!savedModalOpen) return null;

  const handleDelete = async (id) => {
    try {
      await apiDeleteSavedComparison(id, token);
      setItems((prev) => prev.filter((item) => item.id !== id));
    } catch (err) {
      setErrorMsg('Failed to delete comparison.');
    }
  };

  const handleAuditItem = (query) => {
    setSavedModalOpen(false);
    if (onSelectComparison) {
      onSelectComparison(query);
    }
  };

  return (
    <div
      className="auth-modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="saved-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) setSavedModalOpen(false);
      }}
    >
      <div className="account-modal-window">
        {/* Header */}
        <div className="personalize-modal-header" style={{ padding: '24px 28px 18px 28px' }}>
          <div>
            <div className="personalize-eyebrow">YOUR LIBRARY</div>
            <h2 id="saved-modal-title" className="personalize-title">
              Saved Comparisons
            </h2>
            <p className="personalize-subtitle">
              Comparisons are re-evaluated in real time against your CURRENT health profile.
            </p>
          </div>
          <button
            type="button"
            className="auth-close-btn"
            aria-label="Close saved comparisons modal"
            onClick={() => setSavedModalOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        {errorMsg && (
          <div className="auth-inline-error" style={{ margin: '0 28px 16px 28px' }}>
            <AlertCircle size={15} />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="account-modal-body">
          {!isLoggedIn ? (
            <div style={{ textAlign: 'center', padding: '36px 16px' }}>
              <Bookmark size={32} style={{ color: '#047857', margin: '0 auto 12px auto' }} />
              <h3 style={{ fontSize: '1rem', fontWeight: 800, color: '#111827' }}>
                Sign In to Access Saved Comparisons
              </h3>
              <p style={{ fontSize: '0.82rem', color: '#6b7280', maxWidth: '340px', margin: '6px auto 16px auto' }}>
                Create a free account or log in to revisit products and audit evidence across devices.
              </p>
              <button
                type="button"
                className="auth-primary-btn"
                style={{ width: 'auto', padding: '10px 24px', margin: '0 auto' }}
                onClick={() => {
                  setSavedModalOpen(false);
                  openAuth('login');
                }}
              >
                Log in / Sign up
              </button>
            </div>
          ) : loading ? (
            <div style={{ textAlign: 'center', padding: '36px 0', color: '#6b7280' }}>
              Loading saved comparisons...
            </div>
          ) : items.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '36px 16px', color: '#6b7280' }}>
              <Bookmark size={28} style={{ color: '#9ca3af', margin: '0 auto 8px auto' }} />
              <div style={{ fontWeight: 600, color: '#374151' }}>No saved comparisons yet</div>
              <p style={{ fontSize: '0.8rem', marginTop: '4px' }}>
                When auditing any food item, click "Save to Comparisons" to keep it here.
              </p>
            </div>
          ) : (
            <div className="saved-items-list">
              {items.map((item) => (
                <div key={item.id} className="saved-item-card">
                  <div style={{ flex: 1 }}>
                    <div className="saved-item-name">{item.product_name || item.query}</div>
                    <div className="saved-item-meta">
                      <Clock size={12} />
                      <span>Saved: {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'Recent'}</span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button
                      type="button"
                      className="saved-audit-btn"
                      onClick={() => handleAuditItem(item.query)}
                      title="Run audit with current profile"
                    >
                      <ExternalLink size={13} /> Re-Audit
                    </button>
                    <button
                      type="button"
                      className="saved-del-btn"
                      onClick={() => handleDelete(item.id)}
                      title="Remove comparison"
                      aria-label="Delete saved comparison"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

