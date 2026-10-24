import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import SearchSection from './components/SearchSection';
import CacheStatusBanner from './components/CacheStatusBanner';
import ProductCard from './components/ProductCard';
import RawJsonViewer from './components/RawJsonViewer';
import EvidenceModal from './components/EvidenceModal';
import { auditProduct } from './services/api';
import { LayoutDashboard, Code2, AlertCircle, Sparkles } from 'lucide-react';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState('');
  const [error, setError] = useState(null);
  const [auditResult, setAuditResult] = useState(null);
  const [activeTab, setActiveTab] = useState('audit'); // 'audit' | 'json'
  const [evidenceModalOpen, setEvidenceModalOpen] = useState(false);

  // Initial search on mount
  useEffect(() => {
    handleSearch('Cadbury Bournvita', false);
  }, []);

  const handleSearch = async (query, forceRefresh) => {
    setLoading(true);
    setError(null);
    setLoadingStep('Checking PostgreSQL evidence log cache...');

    try {
      const t1 = setTimeout(() => {
        if (!forceRefresh) setLoadingStep('Querying PostgreSQL Evidence Log cache...');
        else setLoadingStep('Bypassing cache. Calling TinyFish Search & Fetch APIs...');
      }, 300);

      const t2 = setTimeout(() => {
        setLoadingStep('Dispatching TinyFish Agent to extract retailer nutrition DOM...');
      }, 700);

      const t3 = setTimeout(() => {
        setLoadingStep('Auditing marketing claims & checking palm oil thresholds...');
      }, 1200);

      const res = await auditProduct(query, forceRefresh);
      
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);

      setAuditResult(res);
    } catch (err) {
      setError(err.message || 'An error occurred during product audit.');
    } finally {
      setLoading(false);
      setLoadingStep('');
    }
  };

  const handleSelectCachedLog = (log) => {
    setAuditResult({
      query: log.query,
      is_cached: true,
      evidence_log_id: log.id,
      created_at: log.created_at,
      source_urls: log.source_urls || [],
      data: log.product_data,
      tinyfish_agent_raw: log.product_data?.tinyfish_agent_raw || null,
    });
  };

  return (
    <div className="desktop-container">
      {/* Desktop Dashboard Header */}
      <Header onOpenEvidenceLogs={() => setEvidenceModalOpen(true)} />

      {/* Product Search & Filters Card */}
      <SearchSection onSearch={handleSearch} loading={loading} />

      {/* Loading Progress State */}
      {loading && (
        <div className="content-card" style={{ alignItems: 'center', textAlign: 'center', padding: '40px 20px' }}>
          <div className="spinner" style={{ width: '32px', height: '32px', borderColor: 'rgba(16, 185, 129, 0.2)', borderTopColor: '#10b981' }} />
          <div style={{ fontWeight: 700, fontSize: '1rem', color: '#10b981', marginTop: '16px' }}>
            {loadingStep || 'Auditing packaged food claims...'}
          </div>
          <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '6px' }}>
            TinyFish Web Agent (DOM Extraction) ➔ LabelTruth Claims Auditor (FSSAI Benchmark) ➔ PostgreSQL Cache
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && !loading && (
        <div className="warning-callout danger" style={{ animation: 'fadeIn 0.3s' }}>
          <AlertCircle size={22} style={{ flexShrink: 0 }} />
          <div>
            <strong style={{ fontSize: '0.95rem' }}>Audit Error: </strong>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Audit Results Dashboard */}
      {auditResult && !loading && (
        <>
          {/* Cache Status Banner */}
          <CacheStatusBanner result={auditResult} />

          {/* Desktop Navigation Tabs */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
            <div className="view-tabs">
              <button
                className={`tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
                onClick={() => setActiveTab('audit')}
              >
                <LayoutDashboard size={17} />
                <span>Nutrition & Claims Dossier</span>
              </button>
              <button
                className={`tab-btn ${activeTab === 'json' ? 'active' : ''}`}
                onClick={() => setActiveTab('json')}
              >
                <Code2 size={17} />
                <span>Raw Pipeline & Agent Inspector</span>
              </button>
            </div>

            <div style={{ fontSize: '0.82rem', color: '#64748b' }}>
              Showing audit results for: <strong style={{ color: '#cbd5e1' }}>"{auditResult.query}"</strong>
            </div>
          </div>

          {/* Tab 1: Desktop 2-Column Product & Claims Dossier */}
          {activeTab === 'audit' && (
            <ProductCard data={auditResult.data} />
          )}

          {/* Tab 2: Desktop Dual-Pane Raw JSON & TinyFish Inspector */}
          {activeTab === 'json' && (
            <RawJsonViewer auditResponse={auditResult} />
          )}
        </>
      )}

      {/* PostgreSQL Evidence Logs Modal */}
      <EvidenceModal
        isOpen={evidenceModalOpen}
        onClose={() => setEvidenceModalOpen(false)}
        onSelectLog={handleSelectCachedLog}
      />
    </div>
  );
}
