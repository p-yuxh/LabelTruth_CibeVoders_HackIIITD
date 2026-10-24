import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import SearchSection from './components/SearchSection';
import CacheStatusBanner from './components/CacheStatusBanner';
import ProductCard from './components/ProductCard';
import EvidenceModal from './components/EvidenceModal';
import { auditProduct } from './services/api';
import { AlertCircle } from 'lucide-react';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState('');
  const [error, setError] = useState(null);
  const [auditResult, setAuditResult] = useState(null);
  const [evidenceModalOpen, setEvidenceModalOpen] = useState(false);

  // Empty state until user searches or attaches image
  // (No automatic search on mount)

  const handleSearch = async (query, forceRefresh) => {
    setLoading(true);
    setError(null);
    setLoadingStep('Locating product records...');

    try {
      const t1 = setTimeout(() => {
        if (!forceRefresh) setLoadingStep('Retrieving verified product data...');
        else setLoadingStep('Gathering label disclosures from live brand sources...');
      }, 300);

      const t2 = setTimeout(() => {
        setLoadingStep('Extracting nutritional table and ingredients statement...');
      }, 700);

      const t3 = setTimeout(() => {
        setLoadingStep('Verifying marketing claims against nutrient thresholds...');
      }, 1200);

      const res = await auditProduct(query, forceRefresh);
      
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);

      setAuditResult(res);
    } catch (err) {
      setError(err.message || 'An error occurred while auditing the product.');
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
      {/* Header */}
      <Header onOpenEvidenceLogs={() => setEvidenceModalOpen(true)} />

      {/* Product Search Bar */}
      <SearchSection onSearch={handleSearch} loading={loading} />

      {/* Loading Progress State */}
      {loading && (
        <div className="content-card" style={{ alignItems: 'center', textAlign: 'center', padding: '48px 24px' }}>
          <div className="spinner" style={{ width: '28px', height: '28px' }} />
          <div style={{ fontWeight: 800, fontSize: '0.98rem', color: '#ffffff', marginTop: '18px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            {loadingStep || 'Auditing packaged food claims...'}
          </div>
          <div style={{ fontSize: '0.8rem', color: '#888888', marginTop: '6px' }}>
            Cross-referencing packaging claims against actual nutrition facts and ingredient statements
          </div>
        </div>
      )}

      {/* Empty State before search */}
      {!auditResult && !loading && !error && (
        <div className="content-card" style={{ textAlign: 'center', padding: '60px 20px', border: '1px dashed #2a2a2a' }}>
          <div style={{ fontSize: '0.9rem', fontWeight: 800, color: '#ffffff', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            No Product Selected
          </div>
          <p style={{ fontSize: '0.82rem', color: '#737373', marginTop: '6px', maxWidth: '440px', margin: '6px auto 0 auto' }}>
            Search for an Indian packaged food item or select a suggestion above to audit front-of-pack claims and personalized suitability.
          </p>
        </div>
      )}

      {/* Error Banner */}
      {error && !loading && (
        <div className="warning-callout alert">
          <AlertCircle size={20} style={{ flexShrink: 0, color: '#ffffff' }} />
          <div>
            <strong style={{ fontSize: '0.9rem', color: '#ffffff' }}>Audit Notice: </strong>
            <span style={{ color: '#cccccc' }}>{error}</span>
          </div>
        </div>
      )}

      {/* Audit Results Dossier */}
      {auditResult && !loading && (
        <>
          {/* Status Banner */}
          <CacheStatusBanner result={auditResult} />

          {/* Product & Claims Dossier Card */}
          <ProductCard data={auditResult.data} />
        </>
      )}

      {/* Audit History Modal */}
      <EvidenceModal
        isOpen={evidenceModalOpen}
        onClose={() => setEvidenceModalOpen(false)}
        onSelectLog={handleSelectCachedLog}
      />
    </div>
  );
}
