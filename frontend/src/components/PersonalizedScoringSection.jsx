import React, { useState, useEffect } from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle, ExternalLink, ChevronDown, ChevronUp, AlertOctagon } from 'lucide-react';
import { calculatePersonalizedScore, fetchProductAlternatives } from '../services/api';
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
  const [alternativesData, setAlternativesData] = useState(() => {
    if (productData?.alternatives && productData.alternatives.status) {
      return productData.alternatives;
    }
    if (productData?.recommendations && productData.recommendations.status) {
      return productData.recommendations;
    }
    return null;
  });
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

  useEffect(() => {
    let isMounted = true;
    const fetchAlts = async () => {
      try {
        const productId = productData?.id || productData?.evidence_log_id || 0;
        const res = await fetchProductAlternatives(productId, selectedConditions, selectedAllergens, productData);
        if (isMounted && res) {
          setAlternativesData(res);
        }
      } catch (e) {
        console.error('Failed to load alternatives', e);
      }
    };
    fetchAlts();
    return () => { isMounted = false; };
  }, [productData, selectedConditions, selectedAllergens]);

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
  const triggers = alternativesData?.trigger || [];
  const triggerReason = alternativesData?.trigger_reason;
  const isRatingTrigger = triggers.includes('high_rating') || triggerReason === 'rating_threshold' || triggerReason === 'both';
  const isAllergenTrigger = triggers.includes('allergen_conflict') || triggerReason === 'allergen_conflict' || triggerReason === 'both';

  const searchedRating = alternativesData?.searched_product?.personalised_rating ?? productRating;
  const conflictingAllergensList = alternativesData?.searched_product?.conflicting_allergens || allergy?.found_allergens || [];
  const allergenNames = conflictingAllergensList.length > 0 ? conflictingAllergensList.join(', ') : (selectedAllergens.length > 0 ? selectedAllergens.join(', ') : 'allergen');
  const displayedAlternatives = (alternativesData?.alternatives || []).slice(0, 5);

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

      {/* 4. BETTER OPTIONS FOR YOU (Gated strictly on status === 'ok' || status === 'none_found') */}
      {alternativesData && (alternativesData.status === 'ok' || alternativesData.status === 'none_found') && (
        <div className="recommendations-box">
          <div className="recommendations-header">
            <div>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.04em', color: '#ffffff' }}>
                Better options for you
              </h3>
              <div style={{ marginTop: '6px', fontSize: '0.8rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                {isRatingTrigger && searchedRating != null && (
                  <div>• Rating {searchedRating}/10 for your profile (higher is worse)</div>
                )}
                {isAllergenTrigger && (
                  <div>• Contains an allergen on your list: {allergenNames}</div>
                )}
              </div>
            </div>
            <span style={{ fontSize: '0.75rem', color: '#a3a3a3', textTransform: 'uppercase' }}>
              Lower rating is healthier (Scale 1–10)
            </span>
          </div>

          {alternativesData.status === 'none_found' ? (
            <div style={{ padding: '16px', background: '#111111', border: '1px solid #333333', color: '#a3a3a3', fontSize: '0.85rem' }}>
              {alternativesData.message || 'No better alternatives found in this category that meet your allergen and dietary criteria.'}
            </div>
          ) : (
            <div className="recommendations-list">
              {displayedAlternatives.map((rec, idx) => {
                const recStyle = getRatingStyle(rec.personalised_rating);
                const reasonsList = rec.data_reasons || rec.reasons || [];
                const improvement = rec.rating_improvement ?? rec.rating_delta;
                return (
                  <div key={rec.product_id || idx} className="recommendation-item">
                    <div className="rec-header">
                      <div>
                        <span className="rec-rank">Option #{idx + 1}</span>
                        <h4 className="rec-title">{rec.name || rec.product_name}</h4>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '2px' }}>
                          <span className="rec-brand">{rec.brand}</span>
                          {(rec.variant || rec.pack_size) && (
                            <span style={{ fontSize: '0.75rem', color: '#737373' }}>
                              • {[rec.variant, rec.pack_size].filter(Boolean).join(' | ')}
                            </span>
                          )}
                        </div>
                      </div>

                      <div style={{ textAlign: 'right' }}>
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
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#a3a3a3', marginTop: '3px' }}>
                          Personalised Rating (lower is better)
                        </div>
                      </div>
                    </div>

                    {improvement != null && improvement > 0 && (
                      <div style={{ fontSize: '0.78rem', color: '#4ade80', fontWeight: 600 }}>
                        {improvement} points better for your profile
                      </div>
                    )}

                    {reasonsList.length > 0 && (
                      <ul style={{ margin: '4px 0 6px 18px', padding: 0, fontSize: '0.8rem', color: '#e2e8f0', lineHeight: 1.45 }}>
                        {reasonsList.map((reason, rIdx) => (
                          <li key={rIdx}>{reason}</li>
                        ))}
                      </ul>
                    )}

                    {isAllergenTrigger && (
                      <div style={{ fontSize: '0.75rem', color: '#fbbf24', fontStyle: 'italic', marginTop: '2px' }}>
                        {rec.disclaimer || rec.allergen_statement || `No listed ${allergenNames} in the ingredients. Always check the pack.`}
                      </div>
                    )}

                    {rec.source_url && (
                      <a href={rec.source_url} target="_blank" rel="noreferrer" className="citation-link" style={{ marginTop: '4px', alignSelf: 'flex-start' }}>
                        <ExternalLink size={11} /> View Source
                      </a>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
