import React from 'react';
import { ExternalLink, AlertTriangle, CheckCircle, ShieldAlert, FileText, Scale } from 'lucide-react';
import PersonalizedScoringSection from './PersonalizedScoringSection';
import ClaimVerdictTag from './ClaimVerdictTag';
import ReferenceStandardsSection from './ReferenceStandardsSection';
import IndependentEvidenceSection from './IndependentEvidenceSection';

export default function ProductCard({ data }) {
  if (!data) return null;

  const {
    product_name,
    brand,
    category,
    nutrition,
    ingredients = [],
    oil_listed,
    front_pack_claims = [],
    lab_test_coverage,
    independent_evidence,
    summary,
    personalized_scoring,
    reference_standards = [],
  } = data;

  const isPalmOil = oil_listed?.is_palm_oil || false;



  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* =========================================
          TOP: Personalised Rating Engine
         ========================================= */}
      <PersonalizedScoringSection
        productData={data}
        initialScoring={personalized_scoring}
      />

      {/* =========================================
          CORE DOSSIER: Two-Column Desktop Grid
         ========================================= */}
      <div className="desktop-grid">
        {/* LEFT COLUMN: Product Overview & Nutrition */}
        <div className="content-card">
          {/* Product Hero Header */}
          <div className="product-hero">
            <div className="product-meta">
              <h2>{product_name?.value || 'Audited Product'}</h2>
              <div className="product-brand">
                {brand?.value} {category?.value ? `• ${category?.value}` : ''}
              </div>
              {product_name?.source_url && (
                <a
                  href={product_name.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="citation-link"
                  style={{ marginTop: '8px' }}
                >
                  <ExternalLink size={13} />
                  <span>View Product Listing</span>
                </a>
              )}
            </div>
          </div>

          {/* Palm Oil & Cooking Fat Callout */}
          <div className={`warning-callout ${isPalmOil ? 'alert' : ''}`}>
            {isPalmOil ? (
              <>
                <ShieldAlert size={22} style={{ flexShrink: 0, marginTop: '2px', color: '#ffffff' }} />
                <div>
                  <strong style={{ fontSize: '0.92rem', color: '#ffffff' }}>Palm Oil Detected: </strong>
                  <span style={{ color: '#d4d4d4' }}>
                    {oil_listed?.value || 'Palm oil / Palmolein'} is listed as the cooking oil. Palm oil carries higher saturated fats.
                  </span>
                  {oil_listed?.source_url && (
                    <div style={{ marginTop: '6px' }}>
                      <a href={oil_listed.source_url} target="_blank" rel="noreferrer" className="citation-link">
                        <ExternalLink size={11} /> View Ingredients Statement
                      </a>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <>
                <CheckCircle size={22} style={{ flexShrink: 0, marginTop: '2px', color: '#ffffff' }} />
                <div>
                  <strong style={{ fontSize: '0.92rem', color: '#ffffff' }}>Oil Declaration: </strong>
                  <span style={{ color: '#d4d4d4' }}>{oil_listed?.value || 'No palm oil detected.'}</span>
                  {oil_listed?.source_url && (
                    <div style={{ marginTop: '6px' }}>
                      <a href={oil_listed.source_url} target="_blank" rel="noreferrer" className="citation-link">
                        <ExternalLink size={11} /> View Ingredients Statement
                      </a>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Audit Summary Box */}
          {summary && (
            <div style={{ fontSize: '0.9rem', color: '#e5e5e5', background: '#000000', padding: '16px', border: '1px solid #2a2a2a', borderLeft: '4px solid #ffffff' }}>
              <strong style={{ color: '#ffffff', textTransform: 'uppercase', fontSize: '0.8rem', letterSpacing: '0.04em' }}>Audit Summary: </strong>
              <p style={{ marginTop: '4px', lineHeight: 1.5, color: '#cccccc' }}>{summary}</p>
            </div>
          )}

          {/* Nutrition Facts Table */}
          {nutrition && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h3 style={{ fontSize: '0.85rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#a3a3a3' }}>
                  Nutrition Facts ({nutrition.serving_size?.value || 'Per Serving'})
                </h3>
                {nutrition.serving_size?.source_url && (
                  <a href={nutrition.serving_size.source_url} target="_blank" rel="noreferrer" className="citation-link">
                    <ExternalLink size={12} /> Serving Source
                  </a>
                )}
              </div>

              <div className="nutrition-grid">
                {nutrition.kcal && (
                  <div className="nutri-box">
                    <span className="nutri-label">Calories</span>
                    <span className="nutri-val">{nutrition.kcal.value} <span style={{ fontSize: '0.75rem', fontWeight: 500, color: '#a3a3a3' }}>{nutrition.kcal.unit}</span></span>
                    <a href={nutrition.kcal.source_url} target="_blank" rel="noreferrer" className="nutri-source">
                      <ExternalLink size={10} /> source
                    </a>
                  </div>
                )}

                {nutrition.carbs_g && (
                  <div className="nutri-box">
                    <span className="nutri-label">Carbohydrates</span>
                    <span className="nutri-val">{nutrition.carbs_g.value}g</span>
                    <a href={nutrition.carbs_g.source_url} target="_blank" rel="noreferrer" className="nutri-source">
                      <ExternalLink size={10} /> source
                    </a>
                  </div>
                )}

                {nutrition.sugars_g && (
                  <div className={`nutri-box ${nutrition.sugars_g.value > 5 ? 'flagged' : ''}`}>
                    <span className="nutri-label">Total Sugars</span>
                    <span className="nutri-val">{nutrition.sugars_g.value}g</span>
                    <a href={nutrition.sugars_g.source_url} target="_blank" rel="noreferrer" className="nutri-source">
                      <ExternalLink size={10} /> source
                    </a>
                  </div>
                )}

                {nutrition.added_sugars_g && (
                  <div className={`nutri-box ${nutrition.added_sugars_g.value > 3 ? 'flagged' : ''}`}>
                    <span className="nutri-label">Added Sugars</span>
                    <span className="nutri-val">{nutrition.added_sugars_g.value}g</span>
                    <a href={nutrition.added_sugars_g.source_url} target="_blank" rel="noreferrer" className="nutri-source">
                      <ExternalLink size={10} /> source
                    </a>
                  </div>
                )}

                {nutrition.protein_g && (
                  <div className="nutri-box">
                    <span className="nutri-label">Protein</span>
                    <span className="nutri-val">{nutrition.protein_g.value}g</span>
                    <a href={nutrition.protein_g.source_url} target="_blank" rel="noreferrer" className="nutri-source">
                      <ExternalLink size={10} /> source
                    </a>
                  </div>
                )}

                {nutrition.fat_g && (
                  <div className="nutri-box">
                    <span className="nutri-label">Total Fat</span>
                    <span className="nutri-val">{nutrition.fat_g.value}g</span>
                    <a href={nutrition.fat_g.source_url} target="_blank" rel="noreferrer" className="nutri-source">
                      <ExternalLink size={10} /> source
                    </a>
                  </div>
                )}

                {nutrition.saturated_fat_g && (
                  <div className="nutri-box">
                    <span className="nutri-label">Saturated Fat</span>
                    <span className="nutri-val">{nutrition.saturated_fat_g.value}g</span>
                    <a href={nutrition.saturated_fat_g.source_url} target="_blank" rel="noreferrer" className="nutri-source">
                      <ExternalLink size={10} /> source
                    </a>
                  </div>
                )}

                {nutrition.sodium_mg && (
                  <div className={`nutri-box ${nutrition.sodium_mg.value > 500 ? 'flagged' : ''}`}>
                    <span className="nutri-label">Sodium</span>
                    <span className="nutri-val">{nutrition.sodium_mg.value}mg</span>
                    <a href={nutrition.sodium_mg.source_url} target="_blank" rel="noreferrer" className="nutri-source">
                      <ExternalLink size={10} /> source
                    </a>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: Claims Verification & Ingredients */}
        <div className="content-card">
          {/* Front Pack Claims Audit */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <h3 style={{ fontSize: '0.85rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#a3a3a3' }}>
                Claims Verification ({front_pack_claims.length})
              </h3>
              <span style={{ fontSize: '0.75rem', color: '#666666', textTransform: 'uppercase' }}>Cross-Referenced Against Label</span>
            </div>

            <div className="claims-list">
              {front_pack_claims.length === 0 ? (
                <div style={{ padding: '16px', background: '#000000', border: '1px solid #222222', color: '#888888', fontSize: '0.85rem' }}>
                  No front-pack marketing claims detected on label.
                </div>
              ) : (
                front_pack_claims.map((item, idx) => (
                  <div key={idx} className="claim-item">
                    <div className="claim-header">
                      <span className="claim-text">"{item.claim}"</span>
                      <ClaimVerdictTag verdict={item.audit_verdict} />
                    </div>
                    <div className="claim-reason">{item.verdict_reason}</div>
                    {item.source_url && (
                      <a href={item.source_url} target="_blank" rel="noreferrer" className="citation-link">
                        <ExternalLink size={11} /> Cited from claim source
                      </a>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Ingredients & Additives Audit */}
          {ingredients.length > 0 && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h3 style={{ fontSize: '0.85rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#a3a3a3' }}>
                  Ingredients ({ingredients.length})
                </h3>
                <div style={{ display: 'flex', gap: '10px', fontSize: '0.72rem', color: '#a3a3a3' }}>
                  <span>[■ Palm Oil]</span>
                  <span>[□ Allergen]</span>
                  <span>[· Additive]</span>
                </div>
              </div>

              <div className="ingredients-wrap">
                {ingredients.map((ing, idx) => {
                  let badgeType = '';
                  if (ing.is_palm_oil_or_derivative) badgeType = 'palm-oil';
                  else if (ing.is_allergen) badgeType = 'allergen';
                  else if (ing.is_additive) badgeType = 'additive';

                  return (
                    <div key={idx} className={`ingredient-badge ${badgeType}`}>
                      <span>{ing.name}</span>
                      {ing.is_palm_oil_or_derivative && <span style={{ fontSize: '0.7rem' }}>[PALM]</span>}
                      {ing.is_allergen && <span style={{ fontSize: '0.7rem' }}>[ALLERGEN]</span>}
                      {ing.is_additive && <span style={{ fontSize: '0.7rem' }}>[ADDITIVE]</span>}
                      {ing.source_url && (
                        <a href={ing.source_url} target="_blank" rel="noreferrer" style={{ color: 'inherit', opacity: 0.6 }} title="View source citation">
                          <ExternalLink size={10} />
                        </a>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

        </div>
      </div>

      {/* =========================================
          MIDDLE: Independent Evidence (Section 1: Lab & Section 2: Social)
         ========================================= */}
      <IndependentEvidenceSection evidence={independent_evidence} />

      {/* =========================================
          BOTTOM: Statutory Standards & Provenance Citations
         ========================================= */}
      <ReferenceStandardsSection
        citations={reference_standards}
        shareOfDaily={personalized_scoring?.share_of_daily_applied || 0.15}
      />
    </div>
  );
}
