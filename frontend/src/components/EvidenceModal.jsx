import React, { useEffect, useState } from 'react';
import { X, Database, Clock, ExternalLink, RefreshCw, ArrowRight } from 'lucide-react';
import { fetchEvidenceLogs } from '../services/api';

export default function EvidenceModal({ isOpen, onClose, onSelectLog }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEvidenceLogs(30, 0);
      setLogs(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch evidence logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadLogs();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Database size={20} color="#10b981" />
            <div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 800 }}>PostgreSQL Evidence Logs Cache</h3>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                Cached audit records stored in table <code>evidence_logs</code> for instantaneous resolution.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
          >
            <X size={22} />
          </button>
        </div>

        <div className="modal-body">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <span style={{ fontSize: '0.82rem', color: '#cbd5e1', fontWeight: 600 }}>
              {logs.length} Cached Product Entries Found
            </span>
            <button
              onClick={loadLogs}
              className="btn-icon"
              style={{ padding: '6px 12px', fontSize: '0.78rem' }}
              disabled={loading}
            >
              <RefreshCw size={14} className={loading ? 'spinner' : ''} />
              <span>Refresh Cache</span>
            </button>
          </div>

          {error && (
            <div style={{ color: '#f43f5e', fontSize: '0.85rem', padding: '10px 14px', background: 'rgba(244,63,94,0.1)', borderRadius: '8px' }}>
              {error}
            </div>
          )}

          {logs.length === 0 && !loading && (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: '#64748b', fontSize: '0.9rem' }}>
              No evidence logs cached in PostgreSQL yet. Run an audit from the search bar to populate the cache!
            </div>
          )}

          {logs.map((log) => (
            <div
              key={log.id}
              className="log-item-row"
              onClick={() => {
                onSelectLog(log);
                onClose();
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <span className="badge-pill hit" style={{ fontSize: '0.7rem' }}>
                  #{log.id}
                </span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#f8fafc' }}>
                    {log.product_name || log.query}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: '#94a3b8', display: 'flex', gap: '8px', alignItems: 'center', marginTop: '2px' }}>
                    <span>Search query: "{log.query}"</span>
                    <span>•</span>
                    <span>{log.brand || 'Indian Brand'}</span>
                    <span>•</span>
                    <span>{log.source_urls?.length || 0} crawled sources</span>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Clock size={12} />
                  {new Date(log.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                </span>
                <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.8rem', fontWeight: 600 }}>
                  View Dossier <ArrowRight size={14} />
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
