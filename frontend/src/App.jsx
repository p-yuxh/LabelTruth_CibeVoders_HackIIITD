import React, { useState } from 'react';
import FigmaLandingPage from './components/FigmaLandingPage';
import FigmaAuditPage from './components/FigmaAuditPage';
import EvidenceModal from './components/EvidenceModal';
import AuthModal from './components/AuthModal';
import PersonalizeModal from './components/PersonalizeModal';
import AccountModal from './components/AccountModal';
import SavedComparisonsModal from './components/SavedComparisonsModal';
import LegalModal from './components/LegalModal';
import { AuthProvider, useAuth } from './context/AuthContext';
import { auditProduct, calculatePersonalizedScore, apiGetIndependentEvidence } from './services/api';
import { adaptAuditData } from './utils/figmaAdapter';
import { AlertCircle } from 'lucide-react';

function MainApp() {
  const {
    user,
    profile,
    isLoggedIn,
    openAuth,
    setAccountModalOpen,
    openLegal,
  } = useAuth();

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
      const activeAvoids = profile?.avoid_ingredients || [];
      const activePattern = profile?.dietary_pattern || 'none';
      const activeGoals = profile?.nutrition_goals || [];

      const res = await auditProduct(
        query,
        forceRefresh,
        'general_health',
        0.15,
        activeConditions,
        activeAllergens,
        activeAvoids,
        activePattern,
        activeGoals
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
          pData.brand?.value || log.brand || '',
          pData.category?.value || log.category || ''
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
    setEvidenceModalOpen(false);
  };

  const handleProfileSaved = async (newProfile) => {
    // If a product is currently viewed, dynamically re-evaluate scoring with updated profile choices
    if (auditResult && auditResult.data) {
      try {
        const conditions = (newProfile.dietary_conditions && newProfile.dietary_conditions.length > 0)
          ? newProfile.dietary_conditions
          : ['general_health'];
        const allergens = newProfile.allergies || [];
        const avoids = newProfile.avoid_ingredients || [];
        const pattern = newProfile.dietary_pattern || 'none';
        const goals = newProfile.nutrition_goals || [];

        const newScores = await calculatePersonalizedScore({
          product_data: auditResult.data,
          conditions,
          user_allergens: allergens,
          avoid_ingredients: avoids,
          dietary_pattern: pattern,
          nutrition_goals: goals,
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

  const adaptedAuditData = auditResult ? adaptAuditData(auditResult, profile?.allergies) : null;

  return (
    <>
      {/* Loading Modal / Overlay */}
      {loading && (
        <div
          style={{
            position: 'fixed',
            zIndex: 999,
            inset: 0,
            background: 'rgba(11, 26, 12, 0.7)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
          }}
        >
          <div
            style={{
              background: '#fbfdf9',
              border: '1px solid #cfe3c3',
              borderRadius: '20px',
              padding: '36px 32px',
              maxWidth: '480px',
              width: '100%',
              textAlign: 'center',
              boxShadow: '0 25px 60px rgba(4, 22, 6, 0.3)',
            }}
          >
            <div className="spinner" style={{ width: '36px', height: '36px' }} />
            <div
              style={{
                fontWeight: 800,
                fontSize: '1rem',
                color: '#132015',
                marginTop: '18px',
                letterSpacing: '-0.3px',
              }}
            >
              {loadingStep || 'Auditing packaged food claims...'}
            </div>
            <p
              style={{
                fontSize: '0.82rem',
                color: '#687565',
                marginTop: '8px',
                lineHeight: 1.5,
              }}
            >
              Cross-referencing packaging claims against actual nutrition facts and ingredient statements
            </p>
          </div>
        </div>
      )}

      {/* Global Error Banner */}
      {error && !loading && (
        <div
          style={{
            position: 'fixed',
            zIndex: 900,
            bottom: '24px',
            left: '50%',
            transform: 'translateX(-50%)',
            width: 'min(640px, calc(100% - 32px))',
          }}
        >
          <div
            className="warning-callout alert"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              boxShadow: '0 10px 30px rgba(0,0,0,0.15)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <AlertCircle size={20} style={{ color: '#b42318', flexShrink: 0 }} />
              <div>
                <b style={{ fontSize: '0.85rem' }}>Audit Notice: </b>
                <span style={{ fontSize: '0.85rem' }}>{error}</span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setError(null)}
              style={{
                background: 'none',
                border: '0',
                fontSize: '18px',
                cursor: 'pointer',
                color: '#666',
                padding: '0 6px',
                lineHeight: 1,
              }}
              aria-label="Dismiss notice"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Screen Views: Audit View vs Landing Page */}
      {adaptedAuditData ? (
        <FigmaAuditPage
          auditData={adaptedAuditData}
          onSearch={handleSearch}
          onBack={() => setAuditResult(null)}
          onOpenEvidenceLogs={() => setEvidenceModalOpen(true)}
          loading={loading}
        />
      ) : (
        <FigmaLandingPage
          onSearch={handleSearch}
          onOpenAuth={openAuth}
          onOpenAccount={() => setAccountModalOpen(true)}
          onOpenEvidenceLogs={() => setEvidenceModalOpen(true)}
          onOpenLegal={openLegal}
          isLoggedIn={isLoggedIn}
          user={user}
          loading={loading}
        />
      )}

      {/* Modals */}
      <AuthModal />
      <PersonalizeModal onProfileSaved={handleProfileSaved} />
      <AccountModal />
      <SavedComparisonsModal onSelectComparison={(q) => handleSearch(q, false)} />
      <LegalModal />
      <EvidenceModal
        isOpen={evidenceModalOpen}
        onClose={() => setEvidenceModalOpen(false)}
        onSelectLog={handleSelectCachedLog}
      />
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
