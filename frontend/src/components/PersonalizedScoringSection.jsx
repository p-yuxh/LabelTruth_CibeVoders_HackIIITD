import React, { useState, useEffect } from 'react';
import { UserCheck, ShieldAlert, Sliders, CheckSquare, Square, Info, Activity, AlertCircle } from 'lucide-react';
import { calculatePersonalizedScore } from '../services/api';

const PROFILES = [
  {
    key: 'general_health',
    name: 'General Health-Aware',
    tagline: 'Balanced everyday nutrition; no specific medical dietary needs.',
  },
  {
    key: 'diabetes_aware',
    name: 'Diabetes-Aware',
    tagline: 'Places more emphasis on carbohydrate suitability, serving size and fibre.',
  },
  {
    key: 'protein_conscious',
    name: 'Protein-Conscious',
    tagline: 'Prioritizes protein intake and evaluates against high-protein targets.',
  },
];

const GOAL_OPTIONS = [
  { id: 'lower_sugar', label: 'Lower Sugar' },
  { id: 'higher_protein', label: 'Higher Protein' },
  { id: 'low_sodium', label: 'Low Sodium' },
  { id: 'low_saturated_fat', label: 'Low Saturated Fat' },
];

export default function PersonalizedScoringSection({ productData, initialScoring }) {
  const [activeProfile, setActiveProfile] = useState(
    initialScoring?.profile_key || 'general_health'
  );
  const [strictPalmOil, setStrictPalmOil] = useState(
    initialScoring?.is_hard_excluded || false
  );
  const [selectedGoals, setSelectedGoals] = useState([]);
  const [shareOfDaily, setShareOfDaily] = useState(0.15);
  const [scoreData, setScoreData] = useState(initialScoring || null);
  const [loading, setLoading] = useState(false);

  // When initialScoring updates from parent, synchronize
  useEffect(() => {
    if (initialScoring) {
      setScoreData(initialScoring);
    }
  }, [initialScoring]);

  // Recalculate score dynamically when profile or goals change
  const handleRecalculate = async (newProfile, newStrictPalm, newGoals, newShare) => {
    // If precomputed all_profiles exist and no custom goals are toggled, update instantly
    if (
      scoreData?.all_profiles?.[newProfile] &&
      newGoals.length === 0 &&
      newShare === 0.15
    ) {
      const precomputed = scoreData.all_profiles[newProfile];
      // Check hard exclusion
      const isExcluded = newStrictPalm && precomputed.palm_oil_status === 'confirmed';
      setScoreData({
        ...precomputed,
        all_profiles: scoreData.all_profiles,
        is_hard_excluded: isExcluded,
        personal_match_score: isExcluded ? 0 : precomputed.personal_match_score,
        status: isExcluded ? 'EXCLUDED' : 'MATCHED',
        hard_exclusion_reason: isExcluded
          ? 'Strict Palm Oil Avoidance: Product confirmed to contain Palm Oil / Palmolein. Hard exclusion overrides other nutritional scores.'
          : null,
      });
      return;
    }

    setLoading(true);
    try {
      const res = await calculatePersonalizedScore(
        productData,
        newProfile,
        newStrictPalm,
        newGoals,
        newShare
      );
      setScoreData(res);
    } catch (err) {
      console.error('Failed to compute personalized score:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleProfileSelect = (profKey) => {
    setActiveProfile(profKey);
    handleRecalculate(profKey, strictPalmOil, selectedGoals, shareOfDaily);
  };

  const handleStrictPalmToggle = () => {
    const nextStrict = !strictPalmOil;
    setStrictPalmOil(nextStrict);
    handleRecalculate(activeProfile, nextStrict, selectedGoals, shareOfDaily);
  };

  const handleGoalToggle = (goalId) => {
    const nextGoals = selectedGoals.includes(goalId)
      ? selectedGoals.filter((g) => g !== goalId)
      : [...selectedGoals, goalId];
    setSelectedGoals(nextGoals);
    handleRecalculate(activeProfile, strictPalmOil, nextGoals, shareOfDaily);
  };

  const handleShareChange = (shareVal) => {
    setShareOfDaily(shareVal);
    handleRecalculate(activeProfile, strictPalmOil, selectedGoals, shareVal);
  };

  if (!scoreData) return null;

  const isExcluded = scoreData.is_hard_excluded;
  const matchScore = scoreData.personal_match_score;
  const profileFit = scoreData.profile_suitability;
  const prefFit = scoreData.preference_match;

  return (
    <div className="personalized-section" style={{ background: '#0a0a0a', border: '1px solid #2a2a2a', padding: '24px', marginBottom: '24px' }}>
      {/* Section Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #222222', paddingBottom: '16px', marginBottom: '18px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <UserCheck size={18} style={{ color: '#ffffff' }} />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#ffffff' }}>
              Personalized Product Scoring
            </h3>
          </div>
          <p style={{ fontSize: '0.8rem', color: '#888888', marginTop: '4px' }}>
            One product record, different user-specific scores. Assesses nutritional fit for a selected profile, then adjusts for personal goals.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', color: '#888888' }}>
          <span>Serving Share:</span>
          {[0.10, 0.15, 0.20].map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => handleShareChange(s)}
              style={{
                background: shareOfDaily === s ? '#ffffff' : '#141414',
                color: shareOfDaily === s ? '#000000' : '#888888',
                border: '1px solid #333333',
                padding: '2px 8px',
                fontSize: '0.72rem',
                cursor: 'pointer',
                fontWeight: shareOfDaily === s ? 700 : 400,
              }}
            >
              {Math.round(s * 100)}%
            </button>
          ))}
        </div>
      </div>

      {/* Profile Selector Tabs */}
      <div style={{ marginBottom: '18px' }}>
        <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: '#a3a3a3', letterSpacing: '0.05em', marginBottom: '8px' }}>
          Select Health Profile:
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
          {PROFILES.map((p) => {
            const isActive = activeProfile === p.key;
            const profileScore = scoreData?.all_profiles?.[p.key]?.personal_match_score;
            return (
              <button
                key={p.key}
                type="button"
                onClick={() => handleProfileSelect(p.key)}
                style={{
                  background: isActive ? '#ffffff' : '#141414',
                  color: isActive ? '#000000' : '#cccccc',
                  border: isActive ? '1px solid #ffffff' : '1px solid #2a2a2a',
                  padding: '12px 14px',
                  textAlign: 'left',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  position: 'relative',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong style={{ fontSize: '0.84rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    {p.name}
                  </strong>
                  {profileScore !== undefined && (
                    <span style={{ fontSize: '0.78rem', fontWeight: 800, padding: '2px 6px', background: isActive ? '#000000' : '#222222', color: isActive ? '#ffffff' : '#ffffff' }}>
                      {strictPalmOil && scoreData?.palm_oil_status === 'confirmed' ? 'EXC' : profileScore}
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '0.72rem', marginTop: '4px', opacity: isActive ? 0.8 : 0.6, lineHeight: 1.3 }}>
                  {p.tagline}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Preference Toggles Bar */}
      <div style={{ background: '#121212', border: '1px solid #222222', padding: '14px 16px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '18px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: '#a3a3a3', letterSpacing: '0.05em' }}>
              Preferences:
            </span>

            {/* Strict Palm Oil Avoidance Toggle */}
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '0.8rem',
                color: strictPalmOil ? '#ffffff' : '#a3a3a3',
                cursor: 'pointer',
                fontWeight: strictPalmOil ? 700 : 400,
                border: strictPalmOil ? '1px solid #ffffff' : '1px solid transparent',
                padding: '4px 8px',
                background: strictPalmOil ? '#222222' : 'transparent',
              }}
            >
              <input
                type="checkbox"
                checked={strictPalmOil}
                onChange={handleStrictPalmToggle}
                style={{ display: 'none' }}
              />
              {strictPalmOil ? <CheckSquare size={15} color="#ffffff" /> : <Square size={15} color="#666666" />}
              <span>Strict Palm-Oil Avoidance (Hard Exclusion)</span>
            </label>

            {/* Configurable Goals */}
            {GOAL_OPTIONS.map((g) => {
              const isChecked = selectedGoals.includes(g.id);
              return (
                <label
                  key={g.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '0.78rem',
                    color: isChecked ? '#ffffff' : '#888888',
                    cursor: 'pointer',
                    fontWeight: isChecked ? 600 : 400,
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => handleGoalToggle(g.id)}
                    style={{ display: 'none' }}
                  />
                  {isChecked ? <CheckSquare size={14} color="#ffffff" /> : <Square size={14} color="#555555" />}
                  <span>{g.label}</span>
                </label>
              );
            })}
          </div>
        </div>
      </div>

      {/* Hard Exclusion Banner */}
      {isExcluded && (
        <div style={{ background: '#000000', border: '2px solid #ffffff', padding: '16px', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <ShieldAlert size={28} style={{ color: '#ffffff', flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: '0.88rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#ffffff' }}>
              Hard Exclusion Triggered: Strict Palm Oil Avoidance
            </div>
            <p style={{ fontSize: '0.82rem', color: '#cccccc', marginTop: '4px', lineHeight: 1.4 }}>
              {scoreData.hard_exclusion_reason || 'Product confirmed to contain Palm Oil / Palmolein. Per LabelTruth specification, high protein or low sugar cannot compensate for strict palm-oil avoidance.'}
            </p>
          </div>
        </div>
      )}

      {/* Primary Score Showcase */}
      <div style={{ display: 'grid', gridTemplateColumns: '170px 1fr', gap: '24px', alignItems: 'center', background: '#000000', border: '1px solid #222222', padding: '20px' }}>
        {/* Left: Square Match Badge */}
        <div style={{ background: isExcluded ? '#1a1a1a' : '#ffffff', color: isExcluded ? '#ffffff' : '#000000', border: '1px solid #ffffff', padding: '18px 12px', textAlign: 'center' }}>
          <div style={{ fontSize: '2.5rem', fontWeight: 900, lineHeight: 1, letterSpacing: '-0.04em' }}>
            {isExcluded ? 'EXC' : matchScore}
          </div>
          <div style={{ fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: '6px' }}>
            {isExcluded ? 'Hard Excluded' : 'Personal Match'}
          </div>
        </div>

        {/* Right: Formula Breakdown & Interpretation */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', color: '#a3a3a3', letterSpacing: '0.06em' }}>
              Formula:
            </span>
            <code style={{ fontSize: '0.82rem', color: '#ffffff', background: '#141414', padding: '3px 8px', border: '1px solid #2a2a2a' }}>
              {scoreData.formula_breakdown}
            </code>
          </div>

          <div style={{ fontSize: '0.78rem', color: '#a3a3a3', marginBottom: '10px' }}>
            Calculation: <span style={{ color: '#ffffff' }}>{scoreData.calculation_detail}</span>
          </div>

          {/* Interpretation matching the PDF */}
          <div style={{ borderLeft: '3px solid #ffffff', paddingLeft: '12px', marginTop: '10px' }}>
            <strong style={{ fontSize: '0.78rem', textTransform: 'uppercase', color: '#ffffff', letterSpacing: '0.04em' }}>
              Interpretation:{' '}
            </strong>
            <span style={{ fontSize: '0.84rem', color: '#cccccc' }}>
              {scoreData.interpretation}
            </span>
          </div>
        </div>
      </div>

      {/* Profiles Side-by-Side Context Bar (from PDF: 3 illustrative examples) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginTop: '18px', paddingTop: '16px', borderTop: '1px solid #222222' }}>
        {PROFILES.map((p) => {
          const item = scoreData?.all_profiles?.[p.key];
          if (!item) return null;
          const isCurrent = activeProfile === p.key;
          return (
            <div
              key={p.key}
              style={{
                background: isCurrent ? '#161616' : '#0d0d0d',
                border: isCurrent ? '1px solid #ffffff' : '1px solid #222222',
                padding: '12px',
                fontSize: '0.75rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#ffffff', fontWeight: 700, marginBottom: '4px' }}>
                <span>{p.name}</span>
                <span style={{ fontWeight: 900 }}>MATCH {strictPalmOil && scoreData?.palm_oil_status === 'confirmed' ? '0 (EXC)' : item.personal_match_score}</span>
              </div>
              <div style={{ color: '#888888', fontSize: '0.7rem' }}>
                Profile Fit: {item.profile_suitability} • Pref Fit: {item.preference_match}
              </div>
            </div>
          );
        })}
      </div>

      {/* Guardrail Disclaimer */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.72rem', color: '#666666', marginTop: '14px' }}>
        <Info size={13} style={{ flexShrink: 0 }} />
        <span>{scoreData.guardrail_note || 'Scores illustrate personalization logic; they are not clinical assessments or validated product ratings.'}</span>
      </div>
    </div>
  );
}

