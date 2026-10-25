import React, { useState, useEffect } from 'react';
import FigmaFormulaInfo from './FigmaFormulaInfo';
import { calculatePersonalizedScore } from '../services/api';
import {
  Card,
  SectionHeading,
  Accordion,
  Badge,
  TextLink,
  DataTable,
  Callout,
} from './AuditSharedComponents';

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
  const [productOpen, setProductOpen] = useState(true);
  const [nutrientsOpen, setNutrientsOpen] = useState(false);
  const [ingredientsOpen, setIngredientsOpen] = useState(false);
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

  // Format Nutrient Breakdown rows for DataTable
  const nutrientHeaders = ['Nutrient', 'Actual', 'Limit', 'Excess', 'Risk score', 'Weight', 'Basis', 'Source'];
  const formattedNutrientRows = (auditData.nutrientBreakdownRows || []).map((row) => [
    row[0],
    row[1],
    row[2],
    row[3],
    <span className="lt-risk-cell" key="risk"><b>{row[4]}</b></span>,
    row[5],
    row[6],
    <span key="src" style={{ minWidth: '140px', display: 'inline-block' }}>{row[7]}</span>,
  ]);

  // Format Top Contributing Ingredients for DataTable
  const ingredientHeaders = ['Ingredient', 'Position', 'Weight', 'Risk score', 'Reason / finding', 'Citation'];
  const formattedIngredientRows = (auditData.topIngredientsRows || []).map((ing, idx) => [
    <b key="name" style={{ color: '#172015' }}>{ing.name}</b>,
    ing.position || `#${idx + 1}`,
    ing.weight || '1',
    <span className="lt-risk-cell" key="risk"><b>{ing.risk || '3/10'}</b></span>,
    ing.reason || 'Ingredient assessed for processing and health fit.',
    <TextLink href="#standards" key="cite">{ing.citation || 'ICMR-NIN 2024'}</TextLink>,
  ]);

  return (
    <main className="audit-page">
      {/* Header aligned to shared container */}
      <header className="audit-header">
        <div className="audit-header-inner">
          <button className="audit-brand" onClick={onBack} aria-label="Back to home">
            <b>LT</b>
            <span>
              LabelTruth
              <small>Packaged food claims &amp; ingredients auditor</small>
            </span>
          </button>
          <div className="audit-header-actions">
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
                className="audit-history auth-btn-account"
                type="button"
                onClick={onOpenAccount}
              >
                {user?.full_name ? user.full_name.split(' ')[0] : 'Account'}
              </button>
            ) : (
              <button
                className="audit-history auth-btn-dark"
                type="button"
                onClick={() => onOpenAuth && onOpenAuth('login')}
              >
                Log in
              </button>
            )}
          </div>
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
          <div style={{ gridColumn: '1 / -1', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#3d4a3a' }}>
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
        <section className="profile-panel">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
            <SectionHeading>
              YOUR DIETARY CONDITIONS &amp; PREFERENCES <FigmaFormulaInfo ids={[4, 12]} />
            </SectionHeading>
            <button
              type="button"
              className="personalize-quick-btn"
              onClick={() => onOpenPersonalize && onOpenPersonalize('complete')}
            >
              Customise full profile →
            </button>
          </div>
          <h1 style={{ margin: '8px 0 16px', fontSize: '20px', textTransform: 'uppercase', letterSpacing: '-0.3px', color: '#172015' }}>
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
            <div className="profile-meta-row" style={{ marginTop: '14px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
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

        {/* Main 2-Column Balanced Detail Grid */}
        <section className="audit-detail-grid">
          {/* Left Column: Claims, Ingredients, Coverage */}
          <div className="report-left">
            {/* Claims Verification Card (Accordion Header Consistency) */}
            <Card className="claims-card" style={{ padding: '0', overflow: 'hidden' }}>
              <button
                className="card-toggle"
                onClick={() => setClaimsOpen(!claimsOpen)}
                type="button"
                style={{ borderRadius: claimsOpen ? '15px 15px 0 0' : '15px' }}
              >
                <span>
                  Claims verification ({auditData.claims.length}) <FigmaFormulaInfo ids={[9]} />
                </span>
                <b>{claimsOpen ? '−' : '+'}</b>
              </button>

              <div style={{ padding: '20px' }}>
                <div className="claim-legend">
                  <Badge variant="verified">Verified</Badge>
                  <Badge variant="misleading">Misleading</Badge>
                  <Badge variant="contradicted">Contradicted</Badge>
                  <Badge variant="no-evidence">No evidence</Badge>
                </div>

                {claimsOpen && (
                  <div className="claim-list">
                    {auditData.claims.length === 0 ? (
                      <div style={{ color: '#4b5847', fontSize: '13px', padding: '12px 0' }}>
                        No front-of-pack marketing claims detected on packaging.
                      </div>
                    ) : (
                      auditData.claims.map((claim, idx) => (
                        <div key={`${claim.claim}-${idx}`}>
                          <b>“{claim.claim}”</b>
                          <Badge variant={claim.verdictClass}>{claim.verdictLabel}</Badge>
                          <p>{claim.reason}</p>
                          {claim.sourceUrl && (
                            <TextLink
                              href={claim.sourceUrl.startsWith('http') ? claim.sourceUrl : '#sources'}
                              target={claim.sourceUrl.startsWith('http') ? '_blank' : undefined}
                            >
                              Cited from verified source
                            </TextLink>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            </Card>

            {/* Ingredients Card */}
            <Card className="ingredients-card">
              <SectionHeading>Ingredients</SectionHeading>
              <p>{auditData.ingredientsStatement}</p>
              <div className="ingredient-flags">
                {auditData.hasPalmOil && <Badge variant="tag-grey">Palm oil</Badge>}
                {auditData.hasAllergen && <Badge variant="tag-grey">Allergen</Badge>}
                {auditData.hasAdditive && <Badge variant="tag-grey">Additive</Badge>}
                {!auditData.hasPalmOil && !auditData.hasAllergen && !auditData.hasAdditive && (
                  <Badge variant="tag-grey">No flagged additives</Badge>
                )}
              </div>
            </Card>

            {/* Coverage Card */}
            <Card className="coverage-card">
              <b>
                Independent lab &amp; regulatory coverage <FigmaFormulaInfo ids={[10]} />
              </b>
              <p>
                {auditData.labCoverage?.findings_summary ||
                  'Cross-checked against package details, nutrition guidance, and independent laboratory evidence.'}
              </p>
              <TextLink href="#sources" isDark>
                View reference report
              </TextLink>
            </Card>
          </div>

          {/* Right Column: Score Panel, Alternatives */}
          <div className="report-right">
            {/* Score Panel */}
            <Card className="score-panel risk">
              <div className="score-title">
                <SectionHeading>
                  Personalised rating <FigmaFormulaInfo ids={[4, 8, 11]} />
                </SectionHeading>
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
              <Badge
                className="risk-label"
                style={{
                  borderColor: auditData.severityColor,
                  color: auditData.severityColor,
                }}
              >
                {auditData.riskLabel}
              </Badge>
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
            </Card>

            {/* Alternatives Card ("Smarter Swaps") */}
            <Card className="alternatives-card">
              <div className="alternatives-heading">
                <div>
                  <SectionHeading>Smarter swaps</SectionHeading>
                  <h2>Suggested alternatives</h2>
                </div>
                <p>Compare the full label before choosing.</p>
              </div>
              <div className="alternative-list">
                {auditData.alternatives.length === 0 ? (
                  <div style={{ color: '#4b5847', fontSize: '13px', padding: '14px', textAlign: 'center' }}>
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
            </Card>
          </div>
        </section>

        {/* Technical Risk Reports (Full Width Side-by-Side Grid) */}
        <section className="technical-report">
          <article className="technical-card">
            <div className="technical-head">
              <b>Risk &amp; regulatory audit</b>
              <div>
                <Badge variant={ratingVal > 7 ? 'critical' : 'caution'}>
                  {ratingVal > 7 ? 'Fail / critical' : 'Benchmark review'}
                </Badge>
                <Badge variant="evidence">Evidence-backed</Badge>
              </div>
              <TextLink href="#standards">View full report</TextLink>
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
                <Badge variant="caution">Caution</Badge>
                <Badge variant="evidence">Evidence-backed</Badge>
              </div>
              <TextLink href="#sources">View source report</TextLink>
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
        </section>

        {/* Analysed Product Summary Accordion */}
        <Accordion
          title="Analysed product"
          isOpen={productOpen}
          onToggle={() => setProductOpen(!productOpen)}
          className="analysed-dropdown"
        >
          <div className="product-summary" style={{ padding: '0', border: '0', boxShadow: 'none' }}>
            <div className="product-title">
              <div>
                <SectionHeading>Product overview</SectionHeading>
                <h2>{auditData.productName}</h2>
                <p>
                  {auditData.brand ? `${auditData.brand} · ` : ''}
                  {auditData.category} · India
                </p>
              </div>
              <img src={auditData.productImage} alt={auditData.productName} />
            </div>
            {auditData.hasPalmOil && (
              <Callout variant="warning" title="Palm oil detected">
                Listed as an edible oil and associated with elevated saturated fat.
              </Callout>
            )}
            <Callout variant="summary" title="Audit summary">
              {auditData.summary}
            </Callout>
            <SectionHeading style={{ marginTop: '24px', marginBottom: '10px' }}>
              Nutrition facts <small>({auditData.servingSize})</small>
            </SectionHeading>
            <div className="fact-grid">
              {auditData.nutritionFacts.map(([label, value]) => (
                <div key={label}>
                  <span>{label}</span>
                  <b>{value}</b>
                </div>
              ))}
            </div>
          </div>
        </Accordion>

        {/* Nutrient Breakdown Table Accordion */}
        <Accordion
          title="Nutrient breakdown & citations"
          id="nutrients"
          isOpen={nutrientsOpen}
          onToggle={() => setNutrientsOpen(!nutrientsOpen)}
          infoComponent={<FigmaFormulaInfo ids={[1, 2, 3, 5]} />}
        >
          <DataTable
            headers={nutrientHeaders}
            rows={formattedNutrientRows}
            alignRightIndexes={[1, 2, 3, 4, 5]}
            nowrapIndexes={[1, 2, 3, 4, 5, 6]}
          />
        </Accordion>

        {/* Top Contributing Ingredients Accordion */}
        <Accordion
          title="Top contributing ingredients"
          isOpen={ingredientsOpen}
          onToggle={() => setIngredientsOpen(!ingredientsOpen)}
          infoComponent={<FigmaFormulaInfo ids={[6, 7]} />}
        >
          <DataTable
            headers={ingredientHeaders}
            rows={formattedIngredientRows}
            alignRightIndexes={[1, 2, 3]}
            nowrapIndexes={[1, 2, 3]}
          />
        </Accordion>

        {/* Audit Evidence & Source Traceability Accordion */}
        <Accordion
          title="Audit evidence & source traceability"
          id="sources"
          isOpen={sourcesOpen}
          onToggle={() => setSourcesOpen(!sourcesOpen)}
          infoComponent={<FigmaFormulaInfo ids={[10, 11]} />}
        >
          <div className="source-content" style={{ padding: '0' }}>
            <div className="source-status">
              <span>Source verification status</span>
              <b>{auditData.verifiedSourcesCount} verified sources</b>
              <Badge variant="tag-grey">{auditData.isCached ? 'Cached verified' : 'Live audit'}</Badge>
            </div>

            <div className="source-grid">
              <article>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                  <SectionHeading>Primary product label</SectionHeading>
                  <Badge variant="verified">Verified</Badge>
                </div>
                <b>Nutrition panel &amp; ingredient list</b>
                <p>Serving size, nutrient values, allergen declaration, additives, and pack claims.</p>
              </article>
              <article>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                  <SectionHeading>Official brand listing</SectionHeading>
                  <Badge variant="verified">Verified</Badge>
                </div>
                <b>Product description &amp; claims</b>
                <p>Cross-checked against manufacturer product disclosures.</p>
              </article>
              <article>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                  <SectionHeading>Retailer listing</SectionHeading>
                  <Badge variant="verified">Corroborated</Badge>
                </div>
                <b>Pack imagery &amp; availability</b>
                <p>Used to corroborate visible front-of-pack claim wording.</p>
              </article>
              <article>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                  <SectionHeading>Regulatory references</SectionHeading>
                  <Badge variant="verified">Verified</Badge>
                </div>
                <b>FSSAI, ICMR-NIN &amp; WHO</b>
                <p>Statutory benchmarks and health guidelines applied in audit.</p>
              </article>
            </div>

            {/* Section 1 & Section 2 Lab Evidence if present */}
            {auditData.independentEvidence?.section_1?.items?.length > 0 && (
              <div style={{ marginTop: '16px', padding: '16px', borderRadius: '10px', background: '#f5faf1', border: '1px solid #dcebd2' }}>
                <SectionHeading>Independent lab &amp; regulatory evidence</SectionHeading>
                <div style={{ fontSize: '12px', color: '#3d4a3a', margin: '6px 0 12px', lineHeight: 1.5 }}>
                  Reported evidence for the tested batch, not proof of wrongdoing. Results apply to the batch tested; the product may have changed since.
                </div>
                {auditData.independentEvidence.section_1.items.map((item, i) => (
                  <div key={i} style={{ padding: '10px 0', borderTop: '1px solid #e1ecdb' }}>
                    <b style={{ fontSize: '14px', color: '#172015' }}>{item.lab_name || item.title}</b>
                    <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#3d4a3a' }}>{item.findings_summary}</p>
                    {item.source_url && (
                      <TextLink href={item.source_url} target="_blank">
                        View lab report document
                      </TextLink>
                    )}
                  </div>
                ))}
              </div>
            )}

            <Callout variant="extraction" title="Extraction basis">
              Per serving · India market · Current visible packaging · FSSAI compliance review
            </Callout>
          </div>
        </Accordion>

        {/* Scientific & Compliance Advisories Accordion */}
        <Accordion
          title="Scientific & compliance citations (advisories)"
          isOpen={advisoriesOpen}
          onToggle={() => setAdvisoriesOpen(!advisoriesOpen)}
        >
          <div className="advisory-grid">
            <article>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                <b>Palmolein &amp; saturated fat</b>
                <Badge variant="tag-grey">Nutrition advisory</Badge>
              </div>
              <p>
                Frequent high saturated-fat intake may contribute to elevated cardiovascular risk.
                Assessment depends on total daily diet and serving frequency.
              </p>
              <TextLink href="#standards">ICMR-NIN Dietary Guidelines for Indians, 2024</TextLink>
            </article>
            <article>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                <b>Sodium &amp; hypertension</b>
                <Badge variant="tag-grey">Clinical advisory</Badge>
              </div>
              <p>
                Elevated sodium intake is associated with increased blood pressure risk.
                This product exceeds the per-serving snack benchmark.
              </p>
              <TextLink href="#standards">WHO Sodium Intake Guideline</TextLink>
            </article>
            <article>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                <b>Food additives &amp; flavour enhancers</b>
                <Badge variant="tag-grey">Compliance note</Badge>
              </div>
              <p>
                Permitted additives must remain within regulatory thresholds and be declared using
                applicable class names or INS numbers.
              </p>
              <TextLink href="#standards">FSSAI Food Product Standards and Additives Regulations</TextLink>
            </article>
          </div>
        </Accordion>

        {/* Statutory Standards Knowledge Base Accordion */}
        <Accordion
          title="Statutory standards & reference citations"
          id="standards"
          isOpen={standardsOpen}
          onToggle={() => setStandardsOpen(!standardsOpen)}
          infoComponent={<FigmaFormulaInfo ids={[2, 3, 9]} />}
        >
          <div className="standards-content">
            <SectionHeading>FSSAI statutory claim standards</SectionHeading>
            <div className="standards-grid">
              <article>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                  <b>High Protein / Rich in Protein</b>
                  <Badge variant="tag-grey">Statutory standard</Badge>
                </div>
                <p>Threshold: 10.8g / 100g or 20% of adult daily RDA.</p>
                <TextLink href="#sources">Food Safety and Standards Regulations</TextLink>
              </article>
              <article>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                  <b>Source of Protein</b>
                  <Badge variant="tag-grey">Statutory standard</Badge>
                </div>
                <p>Threshold: 5.4g / 100g or 10% of adult daily RDA.</p>
                <TextLink href="#sources">Advertising and Claims Regulations</TextLink>
              </article>
            </div>

            <SectionHeading style={{ marginTop: '24px' }}>ICMR-NIN 2024 &amp; WHO dietary guidelines</SectionHeading>
            <div className="standards-grid">
              <article>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                  <b>Daily Salt Upper Limit</b>
                  <Badge variant="tag-grey">Official guideline</Badge>
                </div>
                <p>Daily benchmark: 5g salt / 2000mg sodium.</p>
                <TextLink href="#sources">ICMR-NIN Dietary Guidelines 2024</TextLink>
              </article>
              <article>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                  <b>Daily Added Sugar Upper Limit</b>
                  <Badge variant="tag-grey">Official guideline</Badge>
                </div>
                <p>Upper limit: 25g/day for adults.</p>
                <TextLink href="#sources">WHO Free Sugars Guideline</TextLink>
              </article>
              <article>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                  <b>Total Fat Percentage of Energy</b>
                  <Badge variant="tag-grey">Official guideline</Badge>
                </div>
                <p>Daily benchmark: 30% of total energy.</p>
                <TextLink href="#sources">ICMR-NIN Dietary Guidelines 2024</TextLink>
              </article>
              <article>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                  <b>Minimum Daily Dietary Fibre</b>
                  <Badge variant="tag-grey">Official guideline</Badge>
                </div>
                <p>Daily benchmark: 30g/day from varied food sources.</p>
                <TextLink href="#sources">ICMR-NIN Dietary Guidelines 2024</TextLink>
              </article>
            </div>

            <SectionHeading style={{ marginTop: '24px' }}>Diabetes clinical nutrition guidance</SectionHeading>
            <div className="standards-grid">
              <article>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                  <b>Carbohydrate per snack serving</b>
                  <Badge variant="tag-grey">Clinical assumption</Badge>
                </div>
                <p>Reference guideline: 15g carbohydrate per serving.</p>
                <TextLink href="#sources">ADA Standards of Care</TextLink>
              </article>
              <article>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
                  <b>Added sugar target</b>
                  <Badge variant="tag-grey">Clinical assumption</Badge>
                </div>
                <p>Low added-sugar choices are preferred for glucose-management profiles.</p>
                <TextLink href="#sources">ADA &amp; RSSDI Guidance</TextLink>
              </article>
            </div>
          </div>
        </Accordion>

        <p className="audit-disclaimer">
          Demonstration audit only. Values and scores must be verified against the exact product label
          and qualified dietary guidance.
        </p>
      </div>
    </main>
  );
}
