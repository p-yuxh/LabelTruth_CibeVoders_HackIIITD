import React, { useEffect, useState } from 'react';
import { X, Clock, RefreshCw, ArrowRight, History } from 'lucide-react';
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
      setError(err.message || 'Failed to fetch audit history');
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <History size={20} color="#ffffff" />
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Audit History
              </h3>
              <p style={{ fontSize: '0.78rem', color: '#a3a3a3' }}>
                Previously analyzed food products and verified claims.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: '#ffffff', cursor: 'pointer' }}
          >
            <X size={22} />
          </button>
        </div>

        <div className="modal-body">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <span style={{ fontSize: '0.8rem', color: '#a3a3a3', fontWeight: 600, textTransform: 'uppercase' }}>
              {logs.length} Audited Products
            </span>
            <button
              onClick={loadLogs}
              className="btn-icon"
              style={{ padding: '6px 12px', fontSize: '0.75rem' }}
              disabled={loading}
            >
              <RefreshCw size={12} className={loading ? 'spinner' : ''} />
              <span>Refresh</span>
            </button>
          </div>

          {error && (
            <div style={{ color: '#ffffff', fontSize: '0.85rem', padding: '10px 14px', background: '#1c1c1c', border: '1px solid #ffffff' }}>
              {error}
            </div>
          )}

          {logs.length === 0 && !loading && (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: '#666666', fontSize: '0.9rem' }}>
              No previous audits found. Search for a product to begin auditing.
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
              <div>
                <div style={{ fontWeight: 800, fontSize: '0.95rem', color: '#ffffff' }}>
                  {log.product_name || log.query}
                </div>
                <div style={{ fontSize: '0.78rem', color: '#888888', display: 'flex', gap: '8px', alignItems: 'center', marginTop: '3px' }}>
                  <span>Query: "{log.query}"</span>
                  <span>•</span>
                  <span>{log.brand || 'Brand'}</span>
                  <span>•</span>
                  <span>{log.source_urls?.length || 0} Sources</span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <span style={{ fontSize: '0.75rem', color: '#666666', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Clock size={12} />
                  {new Date(log.created_at).toLocaleDateString()}
                </span>
                <span style={{ color: '#ffffff', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase' }}>
                  View <ArrowRight size={13} />
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
