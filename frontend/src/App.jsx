import React, { useState } from 'react';
import Header from './components/Header';
import SearchSection from './components/SearchSection';
import CacheStatusBanner from './components/CacheStatusBanner';
import ProductCard from './components/ProductCard';
import EvidenceModal from './components/EvidenceModal';
import AuthModal from './components/AuthModal';
import PersonalizeModal from './components/PersonalizeModal';
import AccountModal from './components/AccountModal';
import SavedComparisonsModal from './components/SavedComparisonsModal';
import LegalModal from './components/LegalModal';
import { AuthProvider, useAuth } from './context/AuthContext';
import { auditProduct, calculatePersonalizedScore, apiGetIndependentEvidence } from './services/api';
import { AlertCircle } from 'lucide-react';

function MainApp() {
  const { profile } = useAuth();
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState('');
  const [error, setError] = useState(null);
  const [auditResult, setAuditResult] = useState(null);
  const [evidenceModalOpen, setEvidenceModalOpen] = useState(false);

  const handleSearch = async (query, forceRefresh = false) => {
    setLoading(true);
    setError(null);
    setLoadingStep('Locating product records in evidence registry...');

    const timers = [
      setTimeout(() => {
        if (!forceRefresh) setLoadingStep('Retrieving verified product data from evidence log...');
        else setLoadingStep('Querying live Indian retail and brand sources...');
      }, 400),
      setTimeout(() => {
        setLoadingStep('Extracting nutritional table and ingredients statement...');
      }, 1200),
      setTimeout(() => {
        setLoadingStep('Verifying marketing claims against statutory guidelines (FSSAI & ICMR-NIN)...');
      }, 2500),
      setTimeout(() => {
        setLoadingStep('Evaluating statutory condition limits & flagged ingredient risks...');
      }, 4500),
      setTimeout(() => {
        setLoadingStep('Computing Personalised Rating & searching healthier category alternatives...');
      }, 7500),
      setTimeout(() => {
        setLoadingStep('Awaiting final disclosures from live scraping agent...');
      }, 12000),
    ];

    try {
      const activeConditions = (profile?.dietary_conditions && profile.dietary_conditions.length > 0)
        ? profile.dietary_conditions
        : ['general_health'];
      const activeAllergens = profile?.allergies || [];

      const res = await auditProduct(
        query,
        forceRefresh,
        'general_health',
        0.15,
        activeConditions,
        activeAllergens
      );
      timers.forEach(clearTimeout);
      setAuditResult(res);
    } catch (err) {
      timers.forEach(clearTimeout);
      setError(err.message || 'An error occurred while auditing the product.');
    } finally {
      timers.forEach(clearTimeout);
      setLoading(false);
      setLoadingStep('');
    }
  };

  const handleSelectCachedLog = async (log) => {
    let pData = log.product_data ? { ...log.product_data } : {};

    // If independent_evidence is missing or incomplete in cached log, load dynamically
    if (!pData.independent_evidence || !pData.independent_evidence.section_1) {
      try {
        const ev = await apiGetIndependentEvidence(
          log.query,
          pData.product_name?.value || log.product_name || log.query,
          pData.brand?.value || log.brand || ''
        );
        if (ev) {
          pData.independent_evidence = ev;
        }
      } catch (err) {
        console.warn('Could not populate independent evidence:', err);
      }
    }

    setAuditResult({
      query: log.query,
      is_cached: true,
      evidence_log_id: log.id,
      created_at: log.created_at,
      source_urls: log.source_urls || [],
      data: pData,
      tinyfish_agent_raw: pData?.tinyfish_agent_raw || null,
    });
  };

  const handleProfileSaved = async (newProfile) => {
    // If a product is currently viewed, dynamically re-evaluate the scoring with new profile choices
    if (auditResult && auditResult.data) {
      try {
        const conditions = (newProfile.dietary_conditions && newProfile.dietary_conditions.length > 0)
          ? newProfile.dietary_conditions
          : ['general_health'];
        const allergens = newProfile.allergies || [];

        const newScores = await calculatePersonalizedScore({
          product_data: auditResult.data,
          conditions,
          user_allergens: allergens,
        });

        setAuditResult((prev) => ({
          ...prev,
          data: {
            ...prev.data,
            personalized_scoring: newScores,
          },
        }));
      } catch (err) {
        console.error('Error re-rating with updated profile:', err);
      }
    }
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

      {/* Authentication & Profile Modals */}
      <AuthModal />
      <PersonalizeModal onProfileSaved={handleProfileSaved} />
      <AccountModal />
      <SavedComparisonsModal onSelectComparison={(q) => handleSearch(q, false)} />
      <LegalModal />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
