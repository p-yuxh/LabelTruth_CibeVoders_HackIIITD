import React from 'react';
import { X, Shield, FileText } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function LegalModal() {
  const { legalModalOpen, setLegalModalOpen, legalModalType, setLegalModalType } = useAuth();

  if (!legalModalOpen) return null;

  return (
    <div
      className="auth-modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="legal-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) setLegalModalOpen(false);
      }}
    >
      <div className="account-modal-window" style={{ maxWidth: '640px' }}>
        {/* Header */}
        <div className="personalize-modal-header" style={{ padding: '24px 28px 18px 28px' }}>
          <div>
            <div className="personalize-eyebrow">TRANSPARENCY &amp; TRUST</div>
            <h2 id="legal-modal-title" className="personalize-title">
              {legalModalType === 'privacy' ? 'Privacy Policy & Data Sovereignty' : 'Terms of Service'}
            </h2>
          </div>
          <button
            type="button"
            className="auth-close-btn"
            aria-label="Close legal modal"
            onClick={() => setLegalModalOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="personalize-path-switcher" style={{ margin: '0 28px 16px 28px' }}>
          <button
            type="button"
            className={`personalize-path-tab ${legalModalType === 'terms' ? 'active' : ''}`}
            onClick={() => setLegalModalType('terms')}
          >
            Terms of Service
          </button>
          <button
            type="button"
            className={`personalize-path-tab ${legalModalType === 'privacy' ? 'active' : ''}`}
            onClick={() => setLegalModalType('privacy')}
          >
            Privacy Policy
          </button>
        </div>

        {/* Body Text */}
        <div className="account-modal-body" style={{ maxHeight: '60vh', overflowY: 'auto', fontSize: '0.84rem', lineHeight: 1.6, color: '#374151' }}>
          {legalModalType === 'privacy' ? (
            <div>
              <h4 style={{ fontWeight: 800, color: '#111827', marginBottom: '6px' }}>1. Health Data Protection &amp; Consent</h4>
              <p style={{ marginBottom: '14px' }}>
                LabelTruth treats dietary conditions and allergy declarations as sensitive health data. We store your conditions and allergies only to personalise ratings and safety checks. We never use them for profiling, ad targeting, or commercial resale.
              </p>

              <h4 style={{ fontWeight: 800, color: '#111827', marginBottom: '6px' }}>2. Isolation from Extraction Pipeline</h4>
              <p style={{ marginBottom: '14px' }}>
                Food product evidence is collected per product, not per user. Your profile is strictly isolated and never transmitted to TinyFish scraping agents, web crawler APIs, or third-party LLMs.
              </p>

              <h4 style={{ fontWeight: 800, color: '#111827', marginBottom: '6px' }}>3. Guest Session Option</h4>
              <p style={{ marginBottom: '14px' }}>
                You may use LabelTruth completely anonymously as a guest. When using guest mode, all preference selections remain in your browser session only and are never saved on our servers.
              </p>

              <h4 style={{ fontWeight: 800, color: '#111827', marginBottom: '6px' }}>4. Data Portability &amp; Hard Deletion</h4>
              <p style={{ marginBottom: '14px' }}>
                You have the absolute right to export your complete data package in JSON format or trigger an immediate hard delete of your account and personal records at any time.
              </p>
            </div>
          ) : (
            <div>
              <h4 style={{ fontWeight: 800, color: '#111827', marginBottom: '6px' }}>1. Information Only, Not Medical Advice</h4>
              <p style={{ marginBottom: '14px' }}>
                LabelTruth cross-references packaged food claims against official statutory thresholds (FSSAI, ICMR-NIN, ADA). It provides nutritional transparency for consumer education and is not a substitute for clinical medical diagnosis, prescription, or professional dietitian advice.
              </p>

              <h4 style={{ fontWeight: 800, color: '#111827', marginBottom: '6px' }}>2. Age Requirement</h4>
              <p style={{ marginBottom: '14px' }}>
                You must be 18 years of age or older to register an account with LabelTruth.
              </p>

              <h4 style={{ fontWeight: 800, color: '#111827', marginBottom: '6px' }}>3. Evidence Integrity</h4>
              <p style={{ marginBottom: '14px' }}>
                Independent laboratory findings reflect the specific tested batch and date reported. Formulations and manufacturing specifications may change over time.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

