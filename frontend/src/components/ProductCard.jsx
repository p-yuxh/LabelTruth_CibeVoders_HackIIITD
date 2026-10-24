import React from 'react';
import { ExternalLink, AlertTriangle, CheckCircle, ShieldAlert, FlaskConical, Award, Tag } from 'lucide-react';

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
    summary,
    claim_integrity_score = 50,
  } = data;

  const isPalmOil = oil_listed?.is_palm_oil || false;

  const getScoreClass = (score) => {
    if (score >= 70) return 'high';
    if (score >= 45) return 'mid';
    return 'low';
  };

  const getVerdictClass = (verdict) => {
    const v = (verdict || '').toLowerCase();
    if (v.includes('contradicted') || v.includes('misleading')) return 'contradicted';
    if (v.includes('verified')) return 'verified';
    return 'unsubstantiated';
  };

  return (
    <div className="desktop-grid">
      {/* =========================================
          LEFT COLUMN: Product Dossier & Nutrition
         ========================================= */}
      <div className="content-card">
        {/* Product Hero Header */}
        <div className="product-hero">
          <div className="product-meta">
            <h2>{product_name?.value || 'Audited Product'}</h2>
            <div className="product-brand">
              <strong>Brand:</strong> {brand?.value} {category?.value ? `• ${category?.value}` : ''}
            </div>
            {product_name?.source_url && (
              <a
                href={product_name.source_url}
                target="_blank"
                rel="noreferrer"
                className="citation-link"
                style={{ marginTop: '6px' }}
              >
                <ExternalLink size={13} />
                <span>Verified Retailer Source URL</span>
              </a>
            )}
          </div>

          {/* Claim Integrity Score Dial */}
          <div className={`score-badge-circle ${getScoreClass(claim_integrity_score)}`}>
            <span className="score-number">{claim_integrity_score}</span>
            <span className="score-label">Integrity</span>
          </div>
        </div>

        {/* Palm Oil & Edible Fat Warning Callout */}
        <div className={`warning-callout ${isPalmOil ? 'danger' : 'safe'}`}>
          {isPalmOil ? (
            <>
              <ShieldAlert size={24} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong style={{ fontSize: '0.95rem' }}>Palm Oil Warning: </strong>
                <span>
                  {oil_listed?.value || 'Palm oil / Palmolein'} detected. Contributes higher saturated fatty acids and lower lipid quality.
                </span>
                {oil_listed?.source_url && (
                  <div style={{ marginTop: '4px' }}>
                    <a href={oil_listed.source_url} target="_blank" rel="noreferrer" className="citation-link">
                      <ExternalLink size={12} /> Cited from ingredient disclosure
                    </a>
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <CheckCircle size={24} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong style={{ fontSize: '0.95rem' }}>Edible Oil Profile: </strong>
                <span>{oil_listed?.value || 'No palm oil detected.'}</span>
                {oil_listed?.source_url && (
                  <div style={{ marginTop: '4px' }}>
                    <a href={oil_listed.source_url} target="_blank" rel="noreferrer" className="citation-link">
                      <ExternalLink size={12} /> Cited from ingredients statement
                    </a>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Audit Summary Box */}
        {summary && (
          <div style={{ fontSize: '0.9rem', color: '#e2e8f0', background: 'rgba(255,255,255,0.03)', padding: '14px 18px', borderRadius: '10px', borderLeft: '4px solid #10b981' }}>
            <strong style={{ color: '#10b981' }}>Claims Audit Summary: </strong> {summary}
          </div>
        )}

        {/* Nutrition Facts Table */}
        {nutrition && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8' }}>
                Nutrition Facts ({nutrition.serving_size?.value || 'Per Serving'})
              </h3>
              {nutrition.serving_size?.source_url && (
                <a href={nutrition.serving_size.source_url} target="_blank" rel="noreferrer" className="citation-link">
                  <ExternalLink size={13} /> Serving Source
                </a>
              )}
            </div>

            <div className="nutrition-grid">
              {nutrition.kcal && (
                <div className="nutri-box">
                  <span className="nutri-label">Calories</span>
                  <span className="nutri-val">{nutrition.kcal.value} <span style={{ fontSize: '0.8rem', fontWeight: 500 }}>{nutrition.kcal.unit}</span></span>
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
                <div className="nutri-box" style={{ borderColor: nutrition.sugars_g.value > 5 ? 'rgba(245, 158, 11, 0.45)' : undefined }}>
                  <span className="nutri-label" style={{ color: nutrition.sugars_g.value > 5 ? '#f59e0b' : undefined }}>
                    Total Sugars
                  </span>
                  <span className="nutri-val" style={{ color: nutrition.sugars_g.value > 5 ? '#f59e0b' : undefined }}>
                    {nutrition.sugars_g.value}g
                  </span>
                  <a href={nutrition.sugars_g.source_url} target="_blank" rel="noreferrer" className="nutri-source">
                    <ExternalLink size={10} /> source
                  </a>
                </div>
              )}

              {nutrition.added_sugars_g && (
                <div className="nutri-box" style={{ borderColor: nutrition.added_sugars_g.value > 3 ? 'rgba(244, 63, 94, 0.45)' : undefined }}>
                  <span className="nutri-label" style={{ color: nutrition.added_sugars_g.value > 3 ? '#f43f5e' : undefined }}>
                    Added Sugars
                  </span>
                  <span className="nutri-val" style={{ color: nutrition.added_sugars_g.value > 3 ? '#f43f5e' : undefined }}>
                    {nutrition.added_sugars_g.value}g
                  </span>
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
                <div className="nutri-box" style={{ borderColor: nutrition.sodium_mg.value > 500 ? 'rgba(244, 63, 94, 0.45)' : undefined }}>
                  <span className="nutri-label">Sodium</span>
                  <span className="nutri-val" style={{ color: nutrition.sodium_mg.value > 500 ? '#f43f5e' : undefined }}>
                    {nutrition.sodium_mg.value}mg
                  </span>
                  <a href={nutrition.sodium_mg.source_url} target="_blank" rel="noreferrer" className="nutri-source">
                    <ExternalLink size={10} /> source
                  </a>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* =========================================
          RIGHT COLUMN: Claims Audit & Ingredients
         ========================================= */}
      <div className="content-card">
        {/* Front Pack Claims Audit */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8' }}>
              Front-Of-Pack Marketing Claims ({front_pack_claims.length})
            </h3>
            <span style={{ fontSize: '0.78rem', color: '#64748b' }}>Audited against FSSAI Guidelines</span>
          </div>

          <div className="claims-list">
            {front_pack_claims.map((item, idx) => (
              <div key={idx} className="claim-item">
                <div className="claim-header">
                  <span className="claim-text">"{item.claim}"</span>
                  <span className={`verdict-tag ${getVerdictClass(item.audit_verdict)}`}>
                    {item.audit_verdict}
                  </span>
                </div>
                <div className="claim-reason">{item.verdict_reason}</div>
                {item.source_url && (
                  <a href={item.source_url} target="_blank" rel="noreferrer" className="citation-link">
                    <ExternalLink size={12} /> Claim Source Citation
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Ingredients & Additives Audit */}
        {ingredients.length > 0 && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8' }}>
                Ingredients & Additives ({ingredients.length})
              </h3>
              <div style={{ display: 'flex', gap: '8px', fontSize: '0.72rem' }}>
                <span style={{ color: '#fca5a5' }}>● Palm</span>
                <span style={{ color: '#fcd34d' }}>● Allergen</span>
                <span style={{ color: '#a5b4fc' }}>● Additive</span>
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
                    {ing.is_palm_oil_or_derivative && <span style={{ fontSize: '0.7rem', color: '#fca5a5' }}>(Palm)</span>}
                    {ing.is_allergen && <span style={{ fontSize: '0.7rem', color: '#fcd34d' }}>(Allergen)</span>}
                    {ing.is_additive && <span style={{ fontSize: '0.7rem', color: '#a5b4fc' }}>(Additive)</span>}
                    {ing.source_url && (
                      <a href={ing.source_url} target="_blank" rel="noreferrer" style={{ color: 'inherit', opacity: 0.6 }} title="View source citation">
                        <ExternalLink size={11} />
                      </a>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Consumer Lab Test Coverage */}
        {lab_test_coverage && (
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '10px', padding: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#38bdf8', marginBottom: '6px' }}>
              <FlaskConical size={18} />
              <strong style={{ fontSize: '0.92rem' }}>Consumer Lab & Regulatory Testing Coverage</strong>
            </div>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', lineHeight: 1.5 }}>
              {lab_test_coverage.summary || 'No adverse regulatory orders found in the national testing repository.'}
            </p>
            {lab_test_coverage.source_url && (
              <div style={{ marginTop: '6px' }}>
                <a href={lab_test_coverage.source_url} target="_blank" rel="noreferrer" className="citation-link">
                  <ExternalLink size={12} /> Consumer Voice / FSSAI Reference
                </a>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
