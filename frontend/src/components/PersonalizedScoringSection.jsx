import React, { useState, useEffect } from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle, ExternalLink, ChevronDown, ChevronUp, AlertOctagon, ThumbsUp } from 'lucide-react';
import { calculatePersonalizedScore } from '../services/api';
import { getRatingStyle } from '../utils/themeHelpers';
import PersonalizedRatingBar from './PersonalizedRatingBar';

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

export default function PersonalizedScoringSection({ productData, initialScoring }) {
  const [selectedConditions, setSelectedConditions] = useState(['general_health']);
  const [selectedAllergens, setSelectedAllergens] = useState([]);
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

  const handleRecalculate = async (conditions, allergens) => {
    setLoading(true);
    try {
      const res = await calculatePersonalizedScore({
        product_data: productData,
        conditions,
        user_allergens: allergens,
      });
      setScoreData(res);
    } catch (err) {
      console.error('Error recalculating personalised rating:', err);
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
    handleRecalculate(next, selectedAllergens);
  };

  const toggleAllergen = (item) => {
    const next = selectedAllergens.includes(item)
      ? selectedAllergens.filter((a) => a !== item)
      : [...selectedAllergens, item];
    setSelectedAllergens(next);
    handleRecalculate(selectedConditions, next);
  };

  if (!scoreData) return null;

  const allergy = scoreData.allergy_check || { allergy_status: 'NONE FOUND', is_safe: true };
  const isNotSafe = allergy.allergy_status === 'NOT SAFE FOR YOU';
  const showRating = scoreData.show_scores && !isNotSafe;

  const productRating = scoreData.product_rating;
  const nutrientRating = scoreData.nutrient_rating;
  const ingredientRating = scoreData.ingredient_rating;

  const productRatingStyle = getRatingStyle(productRating);
  const nutrientRatingStyle = getRatingStyle(nutrientRating);
  const ingredientRatingStyle = getRatingStyle(ingredientRating);
  const recommendations = productData?.recommendations || [];

  return (
    <div className="content-card personalized-card">
      {/* 1. Header & Condition Selector */}
      <div className="personalized-header">
        <div>
          <div className="section-eyebrow">Evidence-Based Personalization</div>
          <h2 className="personalized-title">Personalised Nutrition Evaluation</h2>
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

      {/* 2. ALLERGY CHECK (Hard Rule: If NOT SAFE, show no rating) */}
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

      {/* IF ALLERGY FAILS: SHOW NO RATING */}
      {isNotSafe && (
        <div className="safety-suppression-notice">
          <ShieldAlert size={28} style={{ color: '#ffffff', flexShrink: 0 }} />
          <div>
            <h3>NUTRITIONAL RATINGS SUPPRESSED FOR SAFETY</h3>
            <p>
              This product contains confirmed ingredients declared in your allergen restrictions.
              Per clinical safety protocols, nutritional ratings are withheld to prevent consumption.
            </p>
          </div>
        </div>
      )}

      {/* 3. PERSONALISED RATING (1-10, lower = better) */}
      {showRating && (
        <div className="single-score-panel">
          <div className="score-panel rating-panel">
            <div className="score-panel-top">
              <div>
                <span className="panel-kicker">CLINICALLY GUARDED EVALUATION</span>
                <h3 className="panel-title">Personalised Rating</h3>
                <span className="scale-hint">(Scale: 1 – 10 • Lower is Better)</span>
              </div>
              <div
                className="score-box-large"
                style={{
                  backgroundColor: productRatingStyle.bg,
                  color: productRatingStyle.text,
                  padding: '8px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-end',
                  justifyContent: 'center',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
                  <span className="score-value-big" style={{ color: productRatingStyle.text }}>
                    {productRating ?? '—'}
                  </span>
                  <span className="score-denom" style={{ color: productRatingStyle.text, opacity: 0.85 }}>
                    / 10
                  </span>
                </div>
                <span style={{ fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: productRatingStyle.text }}>
                  {productRatingStyle.label}
                </span>
              </div>
            </div>

            <div className="rating-badge-row">
              <span
                className="status-badge-solid"
                style={{
                  backgroundColor: productRatingStyle.bg,
                  color: productRatingStyle.text,
                }}
              >
                {productRating !== null && productRating !== undefined ? `${productRating} / 10 ${productRatingStyle.label}` : productRatingStyle.label}
              </span>
              {scoreData.is_partial_data && (
                <span className="partial-data-badge" title={scoreData.partial_data_note}>
                  [PARTIAL DATA]
                </span>
              )}
            </div>

            <PersonalizedRatingBar rating={productRating} />

            <div className="component-breakdown-row">
              <div className="sub-component-box">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div className="sub-val">{nutrientRating ?? '—'}<span className="sub-denom">/10</span></div>
                  <span
                    style={{
                      backgroundColor: nutrientRatingStyle.bg,
                      color: nutrientRatingStyle.text,
                      padding: '2px 8px',
                      fontSize: '0.72rem',
                      fontWeight: 800,
                      textTransform: 'uppercase',
                    }}
                  >
                    {nutrientRating ?? '—'} / 10 {nutrientRatingStyle.label}
                  </span>
                </div>
                <div className="sub-label">Nutrient Rating (60%)</div>
                <div className="sub-desc">Weighted r_k with clinical worst-case safety floor</div>
              </div>
              <div className="sub-component-box">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div className="sub-val">{ingredientRating ?? '—'}<span className="sub-denom">/10</span></div>
                  <span
                    style={{
                      backgroundColor: ingredientRatingStyle.bg,
                      color: ingredientRatingStyle.text,
                      padding: '2px 8px',
                      fontSize: '0.72rem',
                      fontWeight: 800,
                      textTransform: 'uppercase',
                    }}
                  >
                    {ingredientRating ?? '—'} / 10 {ingredientRatingStyle.label}
                  </span>
                </div>
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
                    {scoreData.nutrient_breakdown?.map((n) => {
                      const rkStyle = getRatingStyle(n.r_k);
                      return (
                        <tr key={n.nutrient_key} className={n.r_k > 1 ? 'row-excess' : ''}>
                          <td><strong>{n.name}</strong></td>
                          <td>{n.actual}{n.unit}</td>
                          <td>{n.limit}{n.unit}</td>
                          <td>{n.excess_pct > 0 ? `+${n.excess_pct}%` : '0%'}</td>
                          <td>
                            <span
                              className="rk-badge"
                              style={{
                                backgroundColor: rkStyle.bg,
                                color: rkStyle.text,
                              }}
                            >
                              {n.r_k}/10 {rkStyle.label}
                            </span>
                          </td>
                          <td>{n.weight}</td>
                          <td className="basis-cell">{n.basis}</td>
                          <td>
                            <a href={n.source_url} target="_blank" rel="noreferrer" className="citation-anchor">
                              {n.source_name} <ExternalLink size={10} />
                            </a>
                          </td>
                        </tr>
                      );
                    })}
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
                    {scoreData.top_ingredients?.map((ing, idx) => {
                      const ingRiskStyle = getRatingStyle(ing.risk_score);
                      return (
                        <tr key={idx} className={ing.is_flagged ? 'row-excess' : ''}>
                          <td><strong>{ing.name}</strong></td>
                          <td>#{ing.position}</td>
                          <td>{ing.position_weight}</td>
                          <td>
                            <span
                              className="rk-badge"
                              style={{
                                backgroundColor: ingRiskStyle.bg,
                                color: ingRiskStyle.text,
                              }}
                            >
                              {ing.risk_score}/10 {ingRiskStyle.label}
                            </span>
                          </td>
                          <td style={{ fontSize: '0.78rem' }}>{ing.flag_reason}</td>
                          <td>
                            <a href={ing.source_url} target="_blank" rel="noreferrer" className="citation-anchor">
                              {ing.source_name} <ExternalLink size={10} />
                            </a>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 4. RECOMMENDATIONS (Same category, safe only, ranked lowest rating first) */}
      {showRating && recommendations && recommendations.length > 0 && (
        <div className="recommendations-box">
          <div className="recommendations-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ThumbsUp size={18} style={{ color: '#ffffff' }} />
              <h3 style={{ fontSize: '0.9rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.04em', color: '#ffffff' }}>
                Healthier Category Alternatives
              </h3>
            </div>
            <span style={{ fontSize: '0.75rem', color: '#888888', textTransform: 'uppercase' }}>
              Ranked by Personalised Rating (Lowest First)
            </span>
          </div>

          <div className="recommendations-list">
            {recommendations.slice(0, 3).map((rec, idx) => (
              <div key={idx} className="recommendation-item">
                <div className="rec-header">
                  <div>
                    <span className="rec-rank">#{idx + 1} Alternative</span>
                    <h4 className="rec-title">{rec.product_name}</h4>
                    <span className="rec-brand">{rec.brand}</span>
                  </div>
                  {(() => {
                    const recStyle = getRatingStyle(rec.personalised_rating);
                    return (
                      <div
                        className="rec-score-box"
                        style={{
                          backgroundColor: recStyle.bg,
                          color: recStyle.text,
                        }}
                      >
                        <span className="rec-score-val" style={{ color: recStyle.text }}>
                          {rec.personalised_rating}
                        </span>
                        <span className="rec-score-denom" style={{ color: recStyle.text, opacity: 0.85 }}>
                          /10
                        </span>
                        <span style={{ fontSize: '0.7rem', fontWeight: 800, textTransform: 'uppercase', marginLeft: '6px', color: recStyle.text }}>
                          {recStyle.label}
                        </span>
                      </div>
                    );
                  })()}
                </div>
                <p className="rec-reason">{rec.recommendation_reason}</p>
                {rec.source_url && (
                  <a href={rec.source_url} target="_blank" rel="noreferrer" className="citation-link" style={{ marginTop: '6px' }}>
                    <ExternalLink size={11} /> View Alternative Listing
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
