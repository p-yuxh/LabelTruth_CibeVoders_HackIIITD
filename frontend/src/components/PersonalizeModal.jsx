import React, { useState, useEffect } from 'react';
import {
  X,
  Check,
  Plus,
  ShieldCheck,
  AlertCircle,
  HelpCircle,
  Lock,
  ArrowRight,
  Info,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function PersonalizeModal({ onProfileSaved }) {
  const {
    personalizeModalOpen,
    setPersonalizeModalOpen,
    personalizePath,
    setPersonalizePath,
    profile,
    profileOptions,
    isLoggedIn,
    saveUserProfile,
    openAuth,
  } = useAuth();

  // Local state for selections
  const [selectedConditions, setSelectedConditions] = useState([]);
  const [selectedAllergies, setSelectedAllergies] = useState([]);
  const [selectedGoals, setSelectedGoals] = useState([]);
  const [selectedAvoids, setSelectedAvoids] = useState([]);
  const [selectedPattern, setSelectedPattern] = useState('none');
  const [healthConsentGiven, setHealthConsentGiven] = useState(false);

  // Consent gate display state (for Path B before showing 01/02)
  const [consentGateApproved, setConsentGateApproved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Sync with current profile on open
  useEffect(() => {
    if (personalizeModalOpen && profile) {
      setSelectedConditions(profile.dietary_conditions || []);
      setSelectedAllergies(profile.allergies || []);
      setSelectedGoals(profile.nutrition_goals || []);
      setSelectedAvoids(profile.avoid_ingredients || []);
      setSelectedPattern(profile.dietary_pattern || 'none');
      setHealthConsentGiven(Boolean(profile.health_data_consent));
      setConsentGateApproved(Boolean(profile.health_data_consent));
      setErrorMsg('');
      setSuccessMsg('');
    }
  }, [personalizeModalOpen, profile]);

  if (!personalizeModalOpen) return null;

  const sections = profileOptions?.sections || [];

  // Categorize sections
  const secConditions = sections.find((s) => s.id === 'dietary_conditions');
  const secAllergies = sections.find((s) => s.id === 'allergies');
  const secGoals = sections.find((s) => s.id === 'nutrition_goals');
  const secAvoids = sections.find((s) => s.id === 'avoid_ingredients');
  const secPattern = sections.find((s) => s.id === 'dietary_pattern');

  // Toggle helpers
  const toggleItem = (list, setList, id) => {
    if (list.includes(id)) {
      setList(list.filter((x) => x !== id));
    } else {
      setList([...list, id]);
    }
  };

  const handleConsentApprove = () => {
    setHealthConsentGiven(true);
    setConsentGateApproved(true);
  };

  const handleSave = async () => {
    setLoading(true);
    setErrorMsg('');
    setSuccessMsg('');

    // If in Path A, clear out conditions & allergies
    const conditionsToSave = personalizePath === 'complete' ? selectedConditions : [];
    const allergiesToSave = personalizePath === 'complete' ? selectedAllergies : [];
    const consentToSave = personalizePath === 'complete' ? healthConsentGiven : false;

    // Check: Saving health data requires consent
    if ((conditionsToSave.length > 0 || allergiesToSave.length > 0) && !consentToSave) {
      setErrorMsg('Explicit user consent is required before saving dietary conditions or allergies.');
      setLoading(false);
      return;
    }

    try {
      const payload = {
        dietary_conditions: conditionsToSave,
        allergies: allergiesToSave,
        nutrition_goals: selectedGoals,
        avoid_ingredients: selectedAvoids,
        dietary_pattern: selectedPattern,
        health_data_consent: consentToSave,
        consent_version: '1.0',
        path_taken: personalizePath,
      };

      const res = await saveUserProfile(payload);
      setSuccessMsg(res.message || 'Profile saved successfully!');
      if (onProfileSaved) {
        onProfileSaved(res.profile || payload);
      }
      setTimeout(() => {
        setPersonalizeModalOpen(false);
      }, 700);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to save profile choices.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="personalize-modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="personalise-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) setPersonalizeModalOpen(false);
      }}
    >
      <div className="personalize-modal-window">
        {/* Header with Title & Close button */}
        <div className="personalize-modal-header">
          <div>
            <div className="personalize-eyebrow">
              {personalizePath === 'basic'
                ? 'PATH A • BASIC PREFERENCES'
                : 'PATH B • COMPLETE PERSONALISATION'}
            </div>
            <h2 id="personalise-title" className="personalize-title">
              Make LabelTruth yours
            </h2>
            <p className="personalize-subtitle">
              Select everything that applies. You can change these choices later.
            </p>
          </div>

          <button
            type="button"
            className="auth-close-btn"
            aria-label="Close personalisation modal"
            onClick={() => setPersonalizeModalOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        {/* Guest Banner */}
        {!isLoggedIn && (
          <div className="personalize-guest-banner">
            <Info size={16} style={{ color: '#047857', flexShrink: 0 }} />
            <div style={{ flex: 1, fontSize: '0.82rem', color: '#166534' }}>
              <strong>Browsing as guest:</strong> Choices apply to your current session.
              <button
                type="button"
                className="personalize-create-acc-link"
                onClick={() => {
                  setPersonalizeModalOpen(false);
                  openAuth('signup');
                }}
              >
                Create account to save this
              </button>
            </div>
          </div>
        )}

        {/* Path Switcher Tabs */}
        <div className="personalize-path-switcher">
          <button
            type="button"
            className={`personalize-path-tab ${personalizePath === 'basic' ? 'active' : ''}`}
            onClick={() => setPersonalizePath('basic')}
          >
            Basic Preferences (Goals &amp; Avoids)
          </button>
          <button
            type="button"
            className={`personalize-path-tab ${personalizePath === 'complete' ? 'active' : ''}`}
            onClick={() => setPersonalizePath('complete')}
          >
            Complete Profile (Includes Conditions &amp; Allergies)
          </button>
        </div>

        {/* Error / Success Messages */}
        {errorMsg && (
          <div className="auth-inline-error" role="alert" style={{ margin: '16px 28px 0 28px' }}>
            <AlertCircle size={16} />
            <span>{errorMsg}</span>
          </div>
        )}
        {successMsg && (
          <div className="auth-inline-success" role="status" style={{ margin: '16px 28px 0 28px' }}>
            <Check size={16} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Modal Scrollable Body */}
        <div className="personalize-modal-body">
          {/* =============================================================
              PATH B: CONSENT GATE FOR SECTIONS 01 & 02
             ============================================================= */}
          {personalizePath === 'complete' && !consentGateApproved ? (
            <div className="health-consent-card">
              <div className="health-consent-icon-box">
                <ShieldCheck size={28} color="#047857" />
              </div>
              <h3 className="health-consent-title">Consent to Store Health &amp; Allergy Data</h3>
              <p className="health-consent-text">
                "We store your conditions and allergies only to personalise ratings and safety checks. You can delete them anytime."
              </p>

              <div className="health-consent-bullets">
                <div className="health-bullet">
                  <Check size={14} color="#047857" />
                  <span>Never shared with advertisers, TinyFish scraping agents, or third parties.</span>
                </div>
                <div className="health-bullet">
                  <Check size={14} color="#047857" />
                  <span>Evidence is collected per product, not per user. Profile contents are never logged.</span>
                </div>
                <div className="health-bullet">
                  <Check size={14} color="#047857" />
                  <span>Hard-delete all your data anytime with one click in Account Settings.</span>
                </div>
              </div>

              <div className="health-consent-actions">
                <button
                  type="button"
                  className="auth-primary-btn"
                  onClick={handleConsentApprove}
                >
                  I Consent &amp; Continue
                </button>
                <button
                  type="button"
                  className="personalize-secondary-btn"
                  onClick={() => setPersonalizePath('basic')}
                >
                  Continue with Basic Preferences (No Health Data)
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* =============================================================
                  PATH B ONLY: SECTIONS 01 & 02 (HEALTH DATA)
                 ============================================================= */}
              {personalizePath === 'complete' && (
                <>
                  {/* Section 01: Dietary Conditions */}
                  {secConditions && (
                    <section className="personalize-section-block" aria-labelledby="sec-title-01">
                      <div className="personalize-section-header">
                        <span className="personalize-section-num">{secConditions.number}</span>
                        <div>
                          <h3 id="sec-title-01" className="personalize-section-title">
                            {secConditions.title}
                          </h3>
                          <span className="personalize-health-badge">Clinical Health Data</span>
                        </div>
                      </div>

                      <div className="personalize-chips-grid">
                        {secConditions.chips.map((chip) => {
                          const checked = selectedConditions.includes(chip.id);
                          return (
                            <button
                              key={chip.id}
                              type="button"
                              className={`pill-chip ${checked ? 'selected' : ''}`}
                              onClick={() => toggleItem(selectedConditions, setSelectedConditions, chip.id)}
                              aria-pressed={checked}
                            >
                              <span className="chip-icon-box" aria-hidden="true">
                                {checked ? <Check size={13} strokeWidth={3} /> : <Plus size={13} strokeWidth={2.5} />}
                              </span>
                              <span className="chip-label">{chip.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    </section>
                  )}

                  {/* Section 02: Allergies */}
                  {secAllergies && (
                    <section className="personalize-section-block" aria-labelledby="sec-title-02">
                      <div className="personalize-section-header">
                        <span className="personalize-section-num">{secAllergies.number}</span>
                        <div>
                          <h3 id="sec-title-02" className="personalize-section-title">
                            {secAllergies.title}
                          </h3>
                          <span className="personalize-health-badge danger">Hard-Stop Safety Gate</span>
                        </div>
                      </div>

                      <div className="personalize-chips-grid">
                        {secAllergies.chips.map((chip) => {
                          const checked = selectedAllergies.includes(chip.id);
                          return (
                            <button
                              key={chip.id}
                              type="button"
                              className={`pill-chip ${checked ? 'selected' : ''}`}
                              onClick={() => toggleItem(selectedAllergies, setSelectedAllergies, chip.id)}
                              aria-pressed={checked}
                            >
                              <span className="chip-icon-box" aria-hidden="true">
                                {checked ? <Check size={13} strokeWidth={3} /> : <Plus size={13} strokeWidth={2.5} />}
                              </span>
                              <span className="chip-label">{chip.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    </section>
                  )}
                </>
              )}

              {/* =============================================================
                  SECTIONS 03, 04, 05 (COMMON TO PATH A & PATH B)
                 ============================================================= */}
              {/* Section 03: Nutrition Goals */}
              {secGoals && (
                <section className="personalize-section-block" aria-labelledby="sec-title-03">
                  <div className="personalize-section-header">
                    <span className="personalize-section-num">{secGoals.number}</span>
                    <h3 id="sec-title-03" className="personalize-section-title">
                      {secGoals.title}
                    </h3>
                  </div>

                  <div className="personalize-chips-grid">
                    {secGoals.chips.map((chip) => {
                      const checked = selectedGoals.includes(chip.id);
                      return (
                        <button
                          key={chip.id}
                          type="button"
                          className={`pill-chip ${checked ? 'selected' : ''}`}
                          onClick={() => toggleItem(selectedGoals, setSelectedGoals, chip.id)}
                          aria-pressed={checked}
                        >
                          <span className="chip-icon-box" aria-hidden="true">
                            {checked ? <Check size={13} strokeWidth={3} /> : <Plus size={13} strokeWidth={2.5} />}
                          </span>
                          <span className="chip-label">{chip.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </section>
              )}

              {/* Section 04: Ingredients to Avoid */}
              {secAvoids && (
                <section className="personalize-section-block" aria-labelledby="sec-title-04">
                  <div className="personalize-section-header">
                    <span className="personalize-section-num">{secAvoids.number}</span>
                    <h3 id="sec-title-04" className="personalize-section-title">
                      {secAvoids.title}
                    </h3>
                  </div>

                  <div className="personalize-chips-grid">
                    {secAvoids.chips.map((chip) => {
                      const checked = selectedAvoids.includes(chip.id);
                      return (
                        <button
                          key={chip.id}
                          type="button"
                          className={`pill-chip ${checked ? 'selected' : ''}`}
                          onClick={() => toggleItem(selectedAvoids, setSelectedAvoids, chip.id)}
                          aria-pressed={checked}
                        >
                          <span className="chip-icon-box" aria-hidden="true">
                            {checked ? <Check size={13} strokeWidth={3} /> : <Plus size={13} strokeWidth={2.5} />}
                          </span>
                          <span className="chip-label">{chip.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </section>
              )}

              {/* Section 05: Dietary Pattern (Single Select) */}
              {secPattern && (
                <section className="personalize-section-block" aria-labelledby="sec-title-05">
                  <div className="personalize-section-header">
                    <span className="personalize-section-num">{secPattern.number}</span>
                    <div>
                      <h3 id="sec-title-05" className="personalize-section-title">
                        {secPattern.title}
                      </h3>
                      <span style={{ fontSize: '0.72rem', color: '#6b7280' }}>Single select</span>
                    </div>
                  </div>

                  <div className="personalize-chips-grid">
                    {secPattern.chips.map((chip) => {
                      const checked = selectedPattern === chip.id;
                      return (
                        <button
                          key={chip.id}
                          type="button"
                          className={`pill-chip ${checked ? 'selected' : ''}`}
                          onClick={() => setSelectedPattern(chip.id)}
                          aria-pressed={checked}
                        >
                          <span className="chip-icon-box" aria-hidden="true">
                            {checked ? <Check size={13} strokeWidth={3} /> : <Plus size={13} strokeWidth={2.5} />}
                          </span>
                          <span className="chip-label">{chip.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </section>
              )}
            </>
          )}

          {/* Medical Disclaimer Banner at Bottom */}
          <div className="personalize-medical-disclaimer">
            <Info size={16} style={{ color: '#047857', flexShrink: 0 }} />
            <span>
              General information, not medical advice. Follow your doctor's or dietitian's advice.
            </span>
          </div>
        </div>

        {/* Modal Footer Actions */}
        <div className="personalize-modal-footer">
          <button
            type="button"
            className="personalize-secondary-btn"
            onClick={() => setPersonalizeModalOpen(false)}
          >
            Skip for now
          </button>
          <button
            type="button"
            className="auth-primary-btn"
            style={{ width: 'auto', padding: '10px 24px' }}
            disabled={loading}
            onClick={handleSave}
          >
            {loading ? 'Saving...' : 'Save profile'}
          </button>
        </div>
      </div>
    </div>
  );
}

