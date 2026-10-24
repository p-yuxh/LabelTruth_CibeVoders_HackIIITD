import React, { useState, useEffect } from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle, ExternalLink, Sliders, ChevronDown, ChevronUp, AlertOctagon } from 'lucide-react';
import { calculatePersonalizedScore } from '../services/api';

const AVAILABLE_PROFILES = [
  { key: 'general_health', label: 'General Health-Aware', desc: 'ICMR-NIN 2024 everyday nutritional guidelines.' },
  { key: 'diabetes', label: 'Diabetes-Aware', desc: 'ADA 2026 / RSSDI strict carbohydrate and free sugar limits.' },
  { key: 'hypertension', label: 'Hypertension-Aware', desc: 'WHO / ICMR-NIN strict sodium cap (<=200mg/serve) and healthy fats.' },
  { key: 'protein_conscious', label: 'Protein-Conscious', desc: 'Fitness profile with controlled sugars and saturated fat.' },
];

const COMMON_ALLERGENS = [
  'Gluten / Wheat',
  'Milk / Dairy',
  'Peanuts',
  'Tree Nuts',
  'Soy',
  'Mustard',
];

const PREFERENCE_OPTIONS = [
  { id: 'avoid_palm_oil', label: 'Avoid Palm Oil' },
  { id: 'avoid_undisclosed_oil', label: 'Avoid Undisclosed Oil' },
  { id: 'avoid_artificial_sweeteners', label: 'Avoid Artificial Sweeteners' },
  { id: 'prefer_whole_grains', label: 'Prefer Whole Grains' },
];

export default function PersonalizedScoringSection({ productData, initialScoring }) {
  const [selectedConditions, setSelectedConditions] = useState(['general_health']);
  const [selectedAllergens, setSelectedAllergens] = useState([]);
  const [selectedPreferences, setSelectedPreferences] = useState([]);
  const [scoreData, setScoreData] = useState(initialScoring || null);
  const [loading, setLoading] = useState(false);
  const [showNutrientTable, setShowNutrientTable] = useState(false);
  const [showIngredientTable, setShowIngredientTable] = useState(false);

  // Synchronize when initialScoring updates
  useEffect(() => {
    if (initialScoring) {
      setScoreData(initialScoring);
      if (initialScoring.selected_conditions) {
        setSelectedConditions(initialScoring.selected_conditions);
      }
    }
  }, [initialScoring]);

  const handleRecalculate = async (conditions, allergens, preferences) => {
    setLoading(true);
    try {
      const avoided = [];
      const preferred = [];

      if (preferences.includes('avoid_palm_oil')) avoided.push('palm oil');
      if (preferences.includes('avoid_artificial_sweeteners')) avoided.push('aspartame', 'acesulfame', 'sucralose');
      if (preferences.includes('prefer_whole_grains')) preferred.push('whole wheat', 'oats', 'multigrain');

      const res = await calculatePersonalizedScore({
        product_data: productData,
        conditions,
        user_allergens: allergens,
        preferences,
        avoided_ingredients: avoided,
        preferred_ingredients: preferred,
      });
      setScoreData(res);
    } catch (err) {
      console.error('Error recalculating personalized scores:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleCondition = (key) => {
    let next;
    if (selectedConditions.includes(key)) {
      next = selectedConditions.filter((k) => k !== key);
      if (next.length === 0) next = ['general_health'];
    } else {
      next = [...selectedConditions, key];
    }
    setSelectedConditions(next);
    handleRecalculate(next, selectedAllergens, selectedPreferences);
  };

  const toggleAllergen = (item) => {
    const next = selectedAllergens.includes(item)
      ? selectedAllergens.filter((a) => a !== item)
      : [...selectedAllergens, item];
    setSelectedAllergens(next);
    handleRecalculate(selectedConditions, next, selectedPreferences);
  };

  const togglePreference = (prefId) => {
    const next = selectedPreferences.includes(prefId)
      ? selectedPreferences.filter((p) => p !== prefId)
      : [...selectedPreferences, prefId];
    setSelectedPreferences(next);
    handleRecalculate(selectedConditions, selectedAllergens, next);
  };

  if (!scoreData) return null;

  const allergy = scoreData.allergy_check || { allergy_status: 'NONE FOUND', is_safe: true };
  const isNotSafe = allergy.allergy_status === 'NOT SAFE FOR YOU';
  const showScores = scoreData.show_scores && !isNotSafe;

  const productRating = scoreData.product_rating;
  const nutrientRating = scoreData.nutrient_rating;
  const ingredientRating = scoreData.ingredient_rating;
  const matchScore = scoreData.personal_match_score;
  const matchDetails = scoreData.match_details || {};

  const getRatingBadge = (val) => {
    if (val === null || val === undefined) return { label: 'N/A', cls: 'badge-muted' };
    if (val <= 3.5) return { label: 'FAVORABLE (LOW RISK)', cls: 'badge-good' };
    if (val <= 6.5) return { label: 'MODERATE RISK', cls: 'badge-warning' };
    return { label: 'HIGH RISK / EXCEEDS LIMITS', cls: 'badge-bad' };
  };

  const ratingBadge = getRatingBadge(productRating);

  return (
    <div className="content-card personalized-card">
      {/* 1. Header & Profile Selector */}
      <div className="personalized-header">
        <div>
          <div className="section-eyebrow">Evidence-Based Personalization</div>
          <h2 className="personalized-title">Health Profile & Preference Evaluation</h2>
          <div className="personalized-subtitle">
            {scoreData.conditions_title || 'General Health-Aware'}
            {selectedConditions.length > 1 && (
              <span className="multi-condition-tag">
                [Multiple Conditions Active: Strictest Limit & Highest Weight Applied]
              </span>
            )}
          </div>
        </div>

        {/* Condition Selection Pills */}
        <div className="condition-pills-row">
          {AVAILABLE_PROFILES.map((p) => {
            const active = selectedConditions.includes(p.key);
            return (
              <button
                key={p.key}
                type="button"
                className={`condition-pill ${active ? 'active' : ''}`}
                onClick={() => toggleCondition(p.key)}
                title={p.desc}
              >
                {active ? '✓ ' : '+ '}
                {p.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* 2. ALLERGY CHECK (Hard Rule: If NOT SAFE, show no scores) */}
      <div className={`allergy-bar ${isNotSafe ? 'alert-danger' : allergy.allergy_status === 'CANNOT CONFIRM' ? 'alert-warning' : 'alert-safe'}`}>
        <div className="allergy-bar-content">
          {isNotSafe ? (
            <AlertOctagon size={20} className="allergy-icon danger" />
          ) : allergy.allergy_status === 'CANNOT CONFIRM' ? (
            <AlertTriangle size={20} className="allergy-icon warning" />
          ) : (
            <CheckCircle size={20} className="allergy-icon safe" />
          )}
          <div>
            <div className="allergy-status-heading">
              ALLERGY STATUS: <strong>{allergy.allergy_status}</strong>
            </div>
            <div className="allergy-status-msg">{allergy.message}</div>
          </div>
        </div>

        {/* Allergen Filters */}
        <div className="allergen-picker">
          <span className="picker-label">Your Allergens:</span>
          {COMMON_ALLERGENS.map((al) => {
            const checked = selectedAllergens.includes(al);
            return (
              <button
                key={al}
                type="button"
                className={`picker-chip ${checked ? 'selected' : ''}`}
                onClick={() => toggleAllergen(al)}
              >
                {checked ? '☒' : '☐'} {al}
              </button>
            );
          })}
        </div>
      </div>

      {/* IF ALLERGY FAILS: SHOW NO SCORES */}
      {isNotSafe && (
        <div className="safety-suppression-notice">
          <ShieldAlert size={28} style={{ color: '#ffffff', flexShrink: 0 }} />
          <div>
            <h3>NUTRITIONAL RATINGS SUPPRESSED FOR SAFETY</h3>
            <p>
              This product contains confirmed ingredients matching your declared allergens.
              Per clinical safety protocols, nutritional fit scores and match ratings are withheld to prevent consumption.
            </p>
          </div>
        </div>
      )}

      {/* 3. SHOW THE TWO DISTINCT SEPARATE SCORES (DO NOT BLEND) */}
      {showScores && (
        <div className="two-scores-grid">
          {/* OUTPUT 1: PERSONALISED RATING (1-10, lower = better) */}
          <div className="score-panel rating-panel">
            <div className="score-panel-top">
              <div>
                <span className="panel-kicker">OUTPUT 1</span>
                <h3 className="panel-title">Personalised Rating</h3>
                <span className="scale-hint">(Scale: 1 – 10 • Lower is Better)</span>
              </div>
              <div className="score-box-large">
                <span className="score-value-big">{productRating ?? '—'}</span>
                <span className="score-denom">/ 10</span>
              </div>
            </div>

            <div className="rating-badge-row">
              <span className={`status-badge-solid ${ratingBadge.cls}`}>{ratingBadge.label}</span>
              {scoreData.is_partial_data && (
                <span className="partial-data-badge" title={scoreData.partial_data_note}>
                  [PARTIAL DATA]
                </span>
              )}
            </div>

            <div className="component-breakdown-row">
              <div className="sub-component-box">
                <div className="sub-val">{nutrientRating ?? '—'}<span className="sub-denom">/10</span></div>
                <div className="sub-label">Nutrient Rating (60%)</div>
                <div className="sub-desc">Weighted r_k with clinical worst-case safety floor</div>
              </div>
              <div className="sub-component-box">
                <div className="sub-val">{ingredientRating ?? '—'}<span className="sub-denom">/10</span></div>
                <div className="sub-label">Ingredient Rating (40%)</div>
                <div className="sub-desc">Position-weighted (first=n, last=1) with flagged override</div>
              </div>
            </div>

            {/* Toggle Expandable Nutrient Rating Table */}
            <div className="expand-strip">
              <button
                type="button"
                className="btn-text-toggle"
                onClick={() => setShowNutrientTable(!showNutrientTable)}
              >
                <span>{showNutrientTable ? 'Hide' : 'View'} Nutrient Breakdown & Citations ({scoreData.nutrient_breakdown?.length || 0})</span>
                {showNutrientTable ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
            </div>

            {showNutrientTable && (
              <div className="table-wrapper">
                <table className="breakdown-table">
                  <thead>
                    <tr>
                      <th>Nutrient</th>
                      <th>Actual</th>
                      <th>Limit</th>
                      <th>Excess %</th>
                      <th>Score (r_k)</th>
                      <th>Weight</th>
                      <th>Basis</th>
                      <th>Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scoreData.nutrient_breakdown?.map((n) => (
                      <tr key={n.nutrient_key} className={n.r_k > 1 ? 'row-excess' : ''}>
                        <td><strong>{n.name}</strong></td>
                        <td>{n.actual}{n.unit}</td>
                        <td>{n.limit}{n.unit}</td>
                        <td>{n.excess_pct > 0 ? `+${n.excess_pct}%` : '0%'}</td>
                        <td><span className={`rk-badge rk-${n.r_k}`}>{n.r_k}/10</span></td>
                        <td>{n.weight}</td>
                        <td className="basis-cell">{n.basis}</td>
                        <td>
                          <a href={n.source_url} target="_blank" rel="noreferrer" className="citation-anchor">
                            {n.source_name} <ExternalLink size={10} />
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Toggle Expandable Top Ingredients Breakdown */}
            <div className="expand-strip">
              <button
                type="button"
                className="btn-text-toggle"
                onClick={() => setShowIngredientTable(!showIngredientTable)}
              >
                <span>{showIngredientTable ? 'Hide' : 'View'} Top Contributing Ingredients ({scoreData.top_ingredients?.length || 0})</span>
                {showIngredientTable ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
            </div>

            {showIngredientTable && (
              <div className="table-wrapper">
                <table className="breakdown-table">
                  <thead>
                    <tr>
                      <th>Ingredient</th>
                      <th>Position</th>
                      <th>Weight</th>
                      <th>Risk Score</th>
                      <th>Reason / Finding</th>
                      <th>Statutory Citation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scoreData.top_ingredients?.map((ing, idx) => (
                      <tr key={idx} className={ing.is_flagged ? 'row-excess' : ''}>
                        <td><strong>{ing.name}</strong></td>
                        <td>#{ing.position}</td>
                        <td>{ing.position_weight}</td>
                        <td><span className={`rk-badge rk-${ing.risk_score}`}>{ing.risk_score}/10</span></td>
                        <td style={{ fontSize: '0.78rem' }}>{ing.flag_reason}</td>
                        <td>
                          <a href={ing.source_url} target="_blank" rel="noreferrer" className="citation-anchor">
                            {ing.source_name} <ExternalLink size={10} />
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* OUTPUT 2: PERSONAL MATCH SCORE (0-100, higher = better, preferences only) */}
          <div className="score-panel match-panel">
            <div className="score-panel-top">
              <div>
                <span className="panel-kicker">OUTPUT 2</span>
                <h3 className="panel-title">Personal Match Score</h3>
                <span className="scale-hint">(Scale: 0 – 100 • Higher is Better • Preferences Only)</span>
              </div>
              <div className="score-box-large">
                <span className="score-value-big">{matchScore ?? '—'}</span>
                <span className="score-denom">/ 100</span>
              </div>
            </div>

            <div className="preferences-status-tag">
              Status: <strong>{matchDetails.preferences_label || 'No preferences selected'}</strong>
            </div>

            {/* Preferences Checkboxes */}
            <div className="preferences-toggles-box">
              <span className="picker-label">Your Preferences:</span>
              <div className="prefs-wrap">
                {PREFERENCE_OPTIONS.map((opt) => {
                  const checked = selectedPreferences.includes(opt.id);
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      className={`pref-checkbox-btn ${checked ? 'checked' : ''}`}
                      onClick={() => togglePreference(opt.id)}
                    >
                      {checked ? '☑ ' : '☐ '}
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Itemized Audit Ledger behind Personal Match Score */}
            <div className="ledger-box">
              <div className="ledger-heading">CALCULATION BREAKDOWN (START: 100)</div>
              {matchDetails.deductions && matchDetails.deductions.length > 0 ? (
                <div className="ledger-list">
                  {matchDetails.deductions.map((d, idx) => (
                    <div key={idx} className="ledger-row">
                      <span className="ledger-desc">{d.description}</span>
                      <span className={`ledger-pts ${d.points < 0 ? 'neg' : 'pos'}`}>
                        {d.points > 0 ? `+${d.points}` : d.points}
                      </span>
                    </div>
                  ))}
                  <div className="ledger-row ledger-total">
                    <strong>Final Clamped Match Score</strong>
                    <strong>{matchScore} / 100</strong>
                  </div>
                </div>
              ) : (
                <div className="no-prefs-note">
                  {matchDetails.has_preferences
                    ? 'All stated ingredient and quality preferences satisfied. No deductions applied.'
                    : 'No preferences selected. Rating reflects baseline claim and nutrient penalties only.'}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
