import React, { useState, useEffect } from 'react';
import FigmaFormulaInfo from './FigmaFormulaInfo';
import { calculatePersonalizedScore } from '../services/api';

const AVAILABLE_CONDITIONS = [
  { id: 'general_health', label: 'General Health', desc: 'Standard balanced limits (ICMR-NIN 2024)' },
  { id: 'diabetes', label: 'Diabetes', desc: 'Strict added sugar and carb limits' },
  { id: 'prediabetes', label: 'Prediabetes', desc: 'Strict free sugars restriction' },
  { id: 'high_blood_pressure', label: 'High Blood Pressure', desc: 'Strict sodium (<200mg/serving) limit' },
  { id: 'high_cholesterol', label: 'High Cholesterol', desc: 'Strict saturated fat (<2g/serving) and palm oil limits' },
  { id: 'coeliac_disease', label: 'Coeliac Disease', desc: 'Medically required zero gluten avoidance' },
  { id: 'lactose_intolerance', label: 'Lactose Intolerance', desc: 'Zero milk and dairy protein gate' },
];

export default function FigmaAuditPage({
  auditData,
  rawProductData,
  onSearch,
  onBack,
  onOpenEvidenceLogs,
  onOpenAuth,
  onOpenAccount,
  onOpenPersonalize,
  onUpdateScoring,
  isLoggedIn,
  user,
  profile,
  loading = false,
}) {
  const [query, setQuery] = useState(auditData?.productName || auditData?.query || '');
  const [forceRefresh, setForceRefresh] = useState(false);

  // Active conditions state
  const [activeConditions, setActiveConditions] = useState(() => {
    return (profile?.dietary_conditions && profile.dietary_conditions.length > 0)
      ? profile.dietary_conditions
      : ['general_health'];
  });
  const [recalculating, setRecalculating] = useState(false);

  useEffect(() => {
    if (profile?.dietary_conditions && profile.dietary_conditions.length > 0) {
      setActiveConditions(profile.dietary_conditions);
    }
  }, [profile]);

  const activeCount =
    (profile?.dietary_conditions?.filter((c) => c !== 'general_health')?.length || 0) +
    (profile?.allergies?.length || 0) +
    (profile?.avoid_ingredients?.length || 0);

  const handleToggleCondition = async (condId) => {
    let next;
    if (condId === 'general_health') {
      next = ['general_health'];
    } else {
      const withoutGeneral = activeConditions.filter((c) => c !== 'general_health');
      if (withoutGeneral.includes(condId)) {
        next = withoutGeneral.filter((c) => c !== condId);
        if (next.length === 0) next = ['general_health'];
      } else {
        next = [...withoutGeneral, condId];
      }
    }
    setActiveConditions(next);

    if (rawProductData && onUpdateScoring) {
      setRecalculating(true);
      try {
        const activeAllergens = profile?.allergies || [];
        const avoids = profile?.avoid_ingredients || [];
        const pattern = profile?.dietary_pattern || 'none';
        const goals = profile?.nutrition_goals || [];

        const newScores = await calculatePersonalizedScore({
          product_data: rawProductData,
          conditions: next,
          user_allergens: activeAllergens,
          avoid_ingredients: avoids,
          dietary_pattern: pattern,
          nutrition_goals: goals,
        });
        onUpdateScoring(newScores);
      } catch (err) {
        console.error('Error updating personalized scoring:', err);
      } finally {
        setRecalculating(false);
      }
    }
  };

  // Accordion toggle states
  const [claimsOpen, setClaimsOpen] = useState(true);
  const [nutrientsOpen, setNutrientsOpen] = useState(false);
  const [ingredientsOpen, setIngredientsOpen] = useState(false);
  const [productOpen, setProductOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [advisoriesOpen, setAdvisoriesOpen] = useState(false);
  const [standardsOpen, setStandardsOpen] = useState(false);

  if (!auditData) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim(), forceRefresh);
    }
  };

  const handleSuggestionClick = (item) => {
    setQuery(item);
    onSearch(item, forceRefresh);
  };

  const suggestions = [
    'Maggi 2-Minute Noodles',
    'Cadbury Bournvita',
    'Lays Potato Chips India',
    'Coca-Cola Zero Sugar Diet Coke',
    'Yoga Bar Dark Chocolate Oats',
    'Amul Butter',
  ];

  const ratingVal = auditData.personalisedRating != null ? auditData.personalisedRating : 5.0;

  return (
    <main className="audit-page">
      {/* Header */}
      <header className="audit-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <button className="audit-brand" onClick={onBack} aria-label="Back to home">
          <b>LT</b>
          <span>
            LabelTruth
            <small>Packaged food claims &amp; ingredients auditor</small>
          </span>
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            type="button"
            className="personalize-nav-btn"
            onClick={() => onOpenPersonalize && onOpenPersonalize('complete')}
            title="Personalise your health conditions and dietary preferences"
          >
            Personalise
            {activeCount > 0 && <span className="header-badge">{activeCount}</span>}
          </button>
          <button
            className="audit-history"
            onClick={onOpenEvidenceLogs}
            type="button"
          >
            Search history
          </button>
          {isLoggedIn ? (
            <button
              className="audit-history"
              type="button"
              onClick={onOpenAccount}
              style={{ background: '#e4f3da', color: '#2f6120', borderColor: '#8fbb73' }}
            >
              {user?.full_name ? user.full_name.split(' ')[0] : 'Account'}
            </button>
          ) : (
            <button
              className="audit-history"
              type="button"
              onClick={() => onOpenAuth && onOpenAuth('login')}
              style={{ background: '#173018', color: '#ffffff', borderColor: '#173018' }}
            >
              Log in
            </button>
          )}
        </div>
      </header>

      <div className="audit-wrap">
        {/* Search Bar */}
        <form className="audit-search" onSubmit={handleSubmit}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search a packaged food or brand..."
            aria-label="Product name"
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Auditing...' : 'Search product'} <span>→</span>
          </button>
          <div className="audit-suggestions">
            <b>Suggestions:</b>
            {suggestions.map((item) => (
              <button
                type="button"
                onClick={() => handleSuggestionClick(item)}
                key={item}
              >
                {item}
              </button>
            ))}
          </div>
          <div style={{ gridColumn: '1 / -1', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: '#576752' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={forceRefresh}
                onChange={(e) => setForceRefresh(e.target.checked)}
                style={{ accentColor: '#4f9c22' }}
              />
              Force fresh verification from live sources
            </label>
          </div>
        </form>

        {/* Live / Cache Status Strip */}
        <div className="live-strip">
          <span>
            <i /> {auditData.isCached ? 'Verified evidence registry' : 'Live verified audit'}
          </span>
          <b>{auditData.verifiedSourcesCount} verified sources</b>
        </div>

        {/* Personalisation Profile Panel */}
        <section className="profile-panel" style={{ marginTop: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
            <span>YOUR DIETARY CONDITIONS &amp; PREFERENCES <FigmaFormulaInfo ids={[4, 12]} /></span>
            <button
              type="button"
              className="personalize-quick-btn"
              onClick={() => onOpenPersonalize && onOpenPersonalize('complete')}
            >
              Customise full profile →
            </button>
          </div>
          <h1 style={{ margin: '6px 0 14px', fontSize: '18px', textTransform: 'uppercase', letterSpacing: '-0.3px' }}>
            {activeConditions.length > 0 && !activeConditions.includes('general_health')
              ? `Personalised for ${activeConditions.map((c) => AVAILABLE_CONDITIONS.find((x) => x.id === c)?.label || c).join(' + ')}`
              : 'Standard Balanced Guidelines (ICMR-NIN 2024)'}
          </h1>

          <div className="profile-tags">
            {AVAILABLE_CONDITIONS.map((cond) => {
              const active = activeConditions.includes(cond.id);
              return (
                <button
                  key={cond.id}
                  type="button"
                  className={`profile-condition-pill ${active ? 'active' : ''}`}
                  onClick={() => handleToggleCondition(cond.id)}
                  title={cond.desc}
                  disabled={recalculating}
                >
                  <i>{active ? '✓' : '+'}</i>
                  <span>{cond.label}</span>
                </button>
              );
            })}
          </div>

          {/* Quick Active Preferences Summary */}
          {((profile?.allergies && profile.allergies.length > 0) || (profile?.dietary_pattern && profile.dietary_pattern !== 'none') || (profile?.avoid_ingredients && profile.avoid_ingredients.length > 0)) && (
            <div className="profile-meta-row" style={{ marginTop: '12px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {profile?.allergies && profile.allergies.length > 0 && (
                <span className="profile-meta-tag alert">
                  Allergies: <b>{profile.allergies.join(', ')}</b>
                </span>
              )}
              {profile?.dietary_pattern && profile.dietary_pattern !== 'none' && (
                <span className="profile-meta-tag">
                  Pattern: <b>{profile.dietary_pattern}</b>
                </span>
              )}
              {profile?.avoid_ingredients && profile.avoid_ingredients.length > 0 && (
                <span className="profile-meta-tag">
                  Avoids: <b>{profile.avoid_ingredients.join(', ')}</b>
                </span>
              )}
            </div>
          )}
        </section>

        {/* Allergy Status Strip */}
        <div className="allergy-strip standalone">
          <b>
            Allergy status: {auditData.hasAllergyConflict ? 'Review required' : 'None found'}{' '}
            <FigmaFormulaInfo ids={[12]} />
          </b>
          <span>
            Your allergens:{' '}
            {auditData.detectedAllergens.length > 0
              ? auditData.detectedAllergens.join(', ')
              : 'None detected in product'}
          </span>
        </div>

        {/* Main 2-Column Detail Grid */}
        <section className="audit-detail-grid">
          {/* Left Column: Claims, Ingredients, Coverage, Technical Reports */}
          <div className="report-left">
            {/* Claims Verification Card */}
            <article className="claims-card">
              <button
                className="card-toggle"
                onClick={() => setClaimsOpen(!claimsOpen)}
                type="button"
              >
                <span>
                  Claims verification ({auditData.claims.length}) <FigmaFormulaInfo ids={[9]} />
                </span>
                <b>{claimsOpen ? '−' : '+'}</b>
              </button>

              <div className="claim-legend">
                <i className="verified">Verified</i>
                <i className="misleading">Misleading</i>
                <i className="contradicted">Contradicted</i>
                <i className="no-evidence">No evidence</i>
              </div>

              {claimsOpen && (
                <div className="claim-list">
                  {auditData.claims.length === 0 ? (
                    <div style={{ color: '#7a8676', fontSize: '11px', padding: '8px' }}>
                      No front-of-pack marketing claims detected on packaging.
                    </div>
                  ) : (
                    auditData.claims.map((claim, idx) => (
                      <div key={`${claim.claim}-${idx}`}>
                        <b>“{claim.claim}”</b>
                        <em className={claim.verdictClass}>{claim.verdictLabel}</em>
                        <p>{claim.reason}</p>
                        {claim.sourceUrl && (
                          <a
                            href={claim.sourceUrl.startsWith('http') ? claim.sourceUrl : '#sources'}
                            target={claim.sourceUrl.startsWith('http') ? '_blank' : '_self'}
                            rel="noopener noreferrer"
                          >
                            Cited from verified source →
                          </a>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </article>

            {/* Ingredients Card */}
            <article className="ingredients-card">
              <span>Ingredients</span>
              <p style={{ marginTop: '6px' }}>{auditData.ingredientsStatement}</p>
              <div className="ingredient-flags" style={{ marginTop: '12px' }}>
                {auditData.hasPalmOil && <i>Palm oil</i>}
                {auditData.hasAllergen && <i>Allergen</i>}
                {auditData.hasAdditive && <i>Additive</i>}
                {!auditData.hasPalmOil && !auditData.hasAllergen && !auditData.hasAdditive && (
                  <i>No flagged additives</i>
                )}
              </div>
            </article>

            {/* Coverage Card */}
            <article className="coverage-card">
              <b>
                Independent lab &amp; regulatory coverage <FigmaFormulaInfo ids={[10]} />
              </b>
              <p>
                {auditData.labCoverage?.findings_summary ||
                  'Cross-checked against package details, nutrition guidance, and independent laboratory evidence.'}
              </p>
              <a href="#sources">View reference report →</a>
            </article>

            {/* Technical Risk Reports */}
            <div className="technical-report">
              <article className="technical-card">
                <div className="technical-head">
                  <b>Risk &amp; regulatory audit</b>
                  <div>
                    <i className={ratingVal > 7 ? 'critical' : 'caution'}>
                      {ratingVal > 7 ? 'Fail / critical' : 'Benchmark review'}
                    </i>
                    <i className="evidence">Evidence-backed</i>
                  </div>
                  <a href="#standards">View full report</a>
                </div>
                <h3>FSSAI &amp; ICMR-NIN risk-level finding</h3>
                <p>
                  Serving-level nutrient and ingredient findings assessed against applicable Indian
                  dietary and claim standards.
                </p>
                <div className="technical-metrics">
                  <div>
                    <span>Regulatory status</span>
                    <b>{ratingVal > 5 ? 'Limit exceeded' : 'Compliant'}</b>
                  </div>
                  <div>
                    <span>Evidence confidence</span>
                    <b>High confidence</b>
                  </div>
                  <div>
                    <span>Citations checked</span>
                    <b>{auditData.verifiedSourcesCount} sources</b>
                  </div>
                  <div>
                    <span>Market assessed</span>
                    <b>India</b>
                  </div>
                </div>
                <dl>
                  <div>
                    <dt>Product status</dt>
                    <dd>{auditData.summary}</dd>
                  </div>
                  <div>
                    <dt>Clinical rationale</dt>
                    <dd>
                      Frequent intake may conflict with sodium, saturated-fat, or dietary sugar limits.
                    </dd>
                  </div>
                  <div>
                    <dt>Regulatory basis</dt>
                    <dd>Benchmarked against FSSAI claim rules and ICMR-NIN 2024 guidance.</dd>
                  </div>
                </dl>
              </article>

              <article className="technical-card">
                <div className="technical-head">
                  <b>Risk &amp; consumer-use note</b>
                  <div>
                    <i className="caution">Caution</i>
                    <i className="evidence">Evidence-backed</i>
                  </div>
                  <a href="#sources">View source report</a>
                </div>
                <h3>Consumer-use &amp; intake-frequency note</h3>
                <p>Risk interpretation based on the declared serving and available package information.</p>
                <div className="technical-metrics five">
                  <div>
                    <span>Product type</span>
                    <b>{auditData.category}</b>
                  </div>
                  <div>
                    <span>Primary concern</span>
                    <b>{auditData.hasPalmOil ? 'Palmolein / fat' : 'Sodium / sugar'}</b>
                  </div>
                  <div>
                    <span>Serving basis</span>
                    <b>{auditData.servingSize}</b>
                  </div>
                  <div>
                    <span>HFSS signal</span>
                    <b className="high-signal">{ratingVal > 7 ? 'High' : (ratingVal > 4 ? 'Moderate' : 'Low')}</b>
                  </div>
                  <div>
                    <span>Recommended use</span>
                    <b>{ratingVal > 7 ? 'Occasional' : 'Regular'}</b>
                  </div>
                </div>
                <dl>
                  <div>
                    <dt>Practical note</dt>
                    <dd>
                      Compare serving sizes and frequency; pair with minimally processed whole foods.
                    </dd>
                  </div>
                  <div>
                    <dt>Evidence context</dt>
                    <dd>
                      Assessment does not replace professional medical advice and may change with reformulation.
                    </dd>
                  </div>
                </dl>
              </article>
            </div>
          </div>

          {/* Right Column: Score Panel, Alternatives, Tables, Product Summary */}
          <div className="report-right">
            {/* Score Panel */}
            <article className="score-panel risk">
              <div className="score-title">
                <span>
                  Personalised rating <FigmaFormulaInfo ids={[4, 8, 11]} />
                </span>
                <div
                  className="rating-result"
                  style={{ '--severity-red': auditData.severityColor }}
                >
                  <strong>
                    {ratingVal.toFixed(2)}
                    <small>/10</small>
                  </strong>
                  <div
                    className="rating-gauge"
                    role="meter"
                    aria-label={`Rating severity: ${ratingVal.toFixed(2)}`}
                    aria-valuemin={0}
                    aria-valuemax={10}
                    aria-valuenow={ratingVal}
                    style={{
                      '--severity-red': auditData.severityColor,
                      '--needle-angle': `${auditData.needleAngle}deg`,
                    }}
                  >
                    <i />
                    <b>{auditData.gaugeShortLabel || 'Score'}</b>
                  </div>
                </div>
              </div>
              <b
                className="risk-label"
                style={{
                  borderColor: auditData.severityColor,
                  color: auditData.severityColor,
                }}
              >
                {auditData.riskLabel}
              </b>
              <div className="subscores">
                <div>
                  <strong>{auditData.nutrientRating}</strong>
                  <span>Nutrient rating</span>
                </div>
                <div>
                  <strong>{auditData.ingredientRating}</strong>
                  <span>Ingredient rating</span>
                </div>
              </div>
            </article>

            {/* Alternatives Card ("Smarter Swaps") */}
            <article className="alternatives-card">
              <div className="alternatives-heading">
                <div>
                  <span>Smarter swaps</span>
                  <h2>Suggested alternatives</h2>
                </div>
                <p>Compare the full label before choosing.</p>
              </div>
              <div className="alternative-list">
                {auditData.alternatives.length === 0 ? (
                  <div style={{ color: '#71806d', fontSize: '11px', padding: '12px', textAlign: 'center' }}>
                    {auditData.alternativesStatus === 'not_needed'
                      ? 'Your selected product already rates well for your profile. No alternative needed.'
                      : 'Searching for healthier alternatives in this category...'}
                  </div>
                ) : (
                  auditData.alternatives.map((alternative) => (
                    <div
                      className="alternative-product"
                      key={alternative.name}
                      onClick={() => handleSuggestionClick(alternative.name)}
                      style={{ cursor: 'pointer' }}
                    >
                      <img src={alternative.image} alt={alternative.name} />
                      <div>
                        <b>{alternative.name}</b>
                        <span>{alternative.reason}</span>
                      </div>
                      <strong>
                        {alternative.score}
                        <small>/10</small>
                      </strong>
                    </div>
                  ))
                )}
              </div>
            </article>

            {/* Nutrient Breakdown Table Accordion */}
            <section className="breakdown" id="nutrients">
              <button
                onClick={() => setNutrientsOpen(!nutrientsOpen)}
                type="button"
              >
                <span>
                  Nutrient breakdown &amp; citations <FigmaFormulaInfo ids={[1, 2, 3, 5]} />
                </span>
                <b>{nutrientsOpen ? '−' : '+'}</b>
              </button>
              {nutrientsOpen && (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Nutrient</th>
                        <th>Actual</th>
                        <th>Limit</th>
                        <th>Excess</th>
                        <th>Risk score</th>
                        <th>Weight</th>
                        <th>Basis</th>
                        <th>Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditData.nutrientBreakdownRows.map((row) => (
                        <tr key={row[0]}>
                          {row.map((cell, index) => (
                            <td key={`${cell}-${index}`}>
                              {index === 4 ? <b>{cell}</b> : cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {/* Top Contributing Ingredients Accordion */}
            <section className="breakdown">
              <button
                onClick={() => setIngredientsOpen(!ingredientsOpen)}
                type="button"
              >
                <span>
                  Top contributing ingredients <FigmaFormulaInfo ids={[6, 7]} />
                </span>
                <b>{ingredientsOpen ? '−' : '+'}</b>
              </button>
              {ingredientsOpen && (
                <div className="ingredient-table">
                  <div className="ingredient-head">
                    <span>Ingredient</span>
                    <span>Position</span>
                    <span>Weight</span>
                    <span>Risk</span>
                    <span>Reason / finding</span>
                    <span>Citation</span>
                  </div>
                  {auditData.topIngredientsRows.map((ing, idx) => (
                    <article key={idx}>
                      <b>{ing.name}</b>
                      <span>{ing.position || `#${idx + 1}`}</span>
                      <span>{ing.weight || '1'}</span>
                      <strong>{ing.risk || '3/10'}</strong>
                      <p>{ing.reason || 'Ingredient assessed for processing and health fit.'}</p>
                      <a href="#standards">{ing.citation || 'ICMR-NIN 2024'}</a>
                    </article>
                  ))}
                </div>
              )}
            </section>

            {/* Analysed Product Summary Accordion */}
            <section className="breakdown analysed-dropdown">
              <button
                onClick={() => setProductOpen(!productOpen)}
                type="button"
              >
                <span>Analysed product</span>
                <b>{productOpen ? '−' : '+'}</b>
              </button>
              {productOpen && (
                <article className="product-summary">
                  <div className="product-title">
                    <div>
                      <span>Product overview</span>
                      <h2>{auditData.productName}</h2>
                      <p>
                        {auditData.brand ? `${auditData.brand} · ` : ''}
                        {auditData.category} · India
                      </p>
                    </div>
                    <img src={auditData.productImage} alt={auditData.productName} />
                  </div>
                  {auditData.hasPalmOil && (
                    <div className="warning-box">
                      <b>Palm oil detected</b>
                      <p>Listed as an edible oil and associated with elevated saturated fat.</p>
                    </div>
                  )}
                  <div className="summary-box">
                    <b>Audit summary</b>
                    <p>{auditData.summary}</p>
                  </div>
                  <h3>
                    Nutrition facts <small>({auditData.servingSize})</small>
                  </h3>
                  <div className="fact-grid">
                    {auditData.nutritionFacts.map(([label, value]) => (
                      <div key={label}>
                        <span>{label}</span>
                        <b>{value}</b>
                      </div>
                    ))}
                  </div>
                </article>
              )}
            </section>
          </div>
        </section>

        {/* Lower Accordion: Evidence & Source Traceability */}
        <section className="breakdown report-section" id="sources">
          <button
            onClick={() => setSourcesOpen(!sourcesOpen)}
            type="button"
          >
            <span>
              Audit evidence &amp; source traceability <FigmaFormulaInfo ids={[10, 11]} />
            </span>
            <b>{sourcesOpen ? '−' : '+'}</b>
          </button>
          {sourcesOpen && (
            <div className="source-content">
              <div className="source-status">
                <span>Source verification status</span>
                <b>{auditData.verifiedSourcesCount} verified sources</b>
                <i>{auditData.isCached ? 'Cached verified' : 'Live audit'}</i>
              </div>

              {/* Real URL Links */}
              <div className="source-grid">
                <article>
                  <span>Primary product label</span>
                  <b>Nutrition panel &amp; ingredient list</b>
                  <p>Serving size, nutrient values, allergen declaration, additives, and pack claims.</p>
                  <i>Verified</i>
                </article>
                <article>
                  <span>Official brand listing</span>
                  <b>Product description &amp; claims</b>
                  <p>Cross-checked against manufacturer product disclosures.</p>
                  <i>Verified</i>
                </article>
                <article>
                  <span>Retailer listing</span>
                  <b>Pack imagery &amp; availability</b>
                  <p>Used to corroborate visible front-of-pack claim wording.</p>
                  <i>Corroborated</i>
                </article>
                <article>
                  <span>Regulatory references</span>
                  <b>FSSAI, ICMR-NIN &amp; WHO</b>
                  <p>Statutory benchmarks and health guidelines applied in audit.</p>
                  <i>Verified</i>
                </article>
              </div>

              {/* Section 1 & Section 2 Lab Evidence if present */}
              {auditData.independentEvidence?.section_1?.items?.length > 0 && (
                <div style={{ marginTop: '16px', padding: '14px', borderRadius: '10px', background: '#f5faf1', border: '1px solid #dcebd2' }}>
                  <span style={{ fontSize: '9px', fontWeight: 800, color: '#387325', textTransform: 'uppercase' }}>
                    Independent lab &amp; regulatory evidence
                  </span>
                  <div style={{ fontSize: '10px', color: '#576752', margin: '4px 0 10px' }}>
                    Reported evidence for the tested batch, not proof of wrongdoing. Results apply to the batch tested; the product may have changed since.
                  </div>
                  {auditData.independentEvidence.section_1.items.map((item, i) => (
                    <div key={i} style={{ padding: '8px 0', borderTop: '1px solid #e1ecdb' }}>
                      <b style={{ fontSize: '11px' }}>{item.lab_name || item.title}</b>
                      <p style={{ margin: '3px 0 0', fontSize: '9px', color: '#687763' }}>{item.findings_summary}</p>
                      {item.source_url && (
                        <a href={item.source_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '8px', color: '#447d28', textDecoration: 'underline' }}>
                          View lab report document →
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div className="extraction-row">
                <b>Extraction basis</b>
                <span>Per serving · India market · Current visible packaging · FSSAI compliance review</span>
              </div>
            </div>
          )}
        </section>

        {/* Lower Accordion: Scientific & Compliance Advisories */}
        <section className="breakdown report-section">
          <button
            onClick={() => setAdvisoriesOpen(!advisoriesOpen)}
            type="button"
          >
            <span>Scientific &amp; compliance citations (advisories)</span>
            <b>{advisoriesOpen ? '−' : '+'}</b>
          </button>
          {advisoriesOpen && (
            <div className="advisory-list">
              <article>
                <b>Palmolein &amp; saturated fat</b>
                <span>Nutrition advisory</span>
                <p>
                  Frequent high saturated-fat intake may contribute to elevated cardiovascular risk.
                  Assessment depends on total daily diet and serving frequency.
                </p>
                <a href="#standards">ICMR-NIN Dietary Guidelines for Indians, 2024</a>
              </article>
              <article>
                <b>Sodium &amp; hypertension</b>
                <span>Clinical advisory</span>
                <p>
                  Elevated sodium intake is associated with increased blood pressure risk.
                  This product exceeds the per-serving snack benchmark.
                </p>
                <a href="#standards">WHO Sodium Intake Guideline</a>
              </article>
              <article>
                <b>Food additives &amp; flavour enhancers</b>
                <span>Compliance note</span>
                <p>
                  Permitted additives must remain within regulatory thresholds and be declared using
                  applicable class names or INS numbers.
                </p>
                <a href="#standards">FSSAI Food Product Standards and Additives Regulations</a>
              </article>
            </div>
          )}
        </section>

        {/* Lower Accordion: Statutory Standards Knowledge Base */}
        <section className="breakdown standards" id="standards">
          <button
            onClick={() => setStandardsOpen(!standardsOpen)}
            type="button"
          >
            <span>
              Statutory standards &amp; reference citations <FigmaFormulaInfo ids={[2, 3, 9]} />
            </span>
            <b>{standardsOpen ? '−' : '+'}</b>
          </button>
          {standardsOpen && (
            <div className="standards-content">
              <h3>FSSAI statutory claim standards</h3>
              <div className="standards-grid">
                <article>
                  <b>High Protein / Rich in Protein</b>
                  <span>Statutory standard</span>
                  <p>Threshold: 10.8g / 100g or 20% of adult daily RDA.</p>
                  <a href="#sources">Food Safety and Standards Regulations</a>
                </article>
                <article>
                  <b>Source of Protein</b>
                  <span>Statutory standard</span>
                  <p>Threshold: 5.4g / 100g or 10% of adult daily RDA.</p>
                  <a href="#sources">Advertising and Claims Regulations</a>
                </article>
              </div>

              <h3>ICMR-NIN 2024 &amp; WHO dietary guidelines</h3>
              <div className="standards-grid">
                <article>
                  <b>Daily Salt Upper Limit</b>
                  <span>Official guideline</span>
                  <p>Daily benchmark: 5g salt / 2000mg sodium.</p>
                  <a href="#sources">ICMR-NIN Dietary Guidelines 2024</a>
                </article>
                <article>
                  <b>Daily Added Sugar Upper Limit</b>
                  <span>Official guideline</span>
                  <p>Upper limit: 25g/day for adults.</p>
                  <a href="#sources">WHO Free Sugars Guideline</a>
                </article>
                <article>
                  <b>Total Fat Percentage of Energy</b>
                  <span>Official guideline</span>
                  <p>Daily benchmark: 30% of total energy.</p>
                  <a href="#sources">ICMR-NIN Dietary Guidelines 2024</a>
                </article>
                <article>
                  <b>Minimum Daily Dietary Fibre</b>
                  <span>Official guideline</span>
                  <p>Daily benchmark: 30g/day from varied food sources.</p>
                  <a href="#sources">ICMR-NIN Dietary Guidelines 2024</a>
                </article>
              </div>

              <h3>Diabetes clinical nutrition guidance</h3>
              <div className="standards-grid">
                <article>
                  <b>Carbohydrate per snack serving</b>
                  <span>Clinical assumption</span>
                  <p>Reference guideline: 15g carbohydrate per serving.</p>
                  <a href="#sources">ADA Standards of Care</a>
                </article>
                <article>
                  <b>Added sugar target</b>
                  <span>Clinical assumption</span>
                  <p>Low added-sugar choices are preferred for glucose-management profiles.</p>
                  <a href="#sources">ADA &amp; RSSDI Guidance</a>
                </article>
              </div>
            </div>
          )}
        </section>

        <p className="audit-disclaimer">
          Demonstration audit only. Values and scores must be verified against the exact product label
          and qualified dietary guidance.
        </p>
      </div>
    </main>
  );
}

