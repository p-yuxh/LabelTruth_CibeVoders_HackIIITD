import { useEffect, useRef, useState } from 'react'

const values = [
  ['Strictly Independent', 'No sponsorships or hidden funding—only objective verdicts.'],
  ['Made Personal', 'Filter products by your allergies, diet, and preferences.'],
  ['Backed by Proof', 'Claims are checked against lab data and regulatory standards.'],
]

const steps = [
  ['01', 'Set Your Priorities', 'Choose products, dietary needs, and ingredients to avoid.'],
  ['02', 'We Check the Evidence', 'We compare labels with official sources and independent lab reports.'],
  ['03', 'Get a Clear Verdict', 'See what is verified, contradicted, or still unproven.'],
]

const faqs = [
  ['What is LabelTruth?', 'An independent tool that checks package claims against nutrition data, regulations, and lab evidence.'],
  ['Where does the data come from?', 'Product labels, official sources, regulatory guidance, and independent tests.'],
  ['Can brands pay to change their verdicts?', 'No. LabelTruth is independent, and brands cannot buy or alter a verdict.'],
  ['What if a product has no public lab test available?', 'We clearly show what is verified, what is unverified, and which evidence is still missing.'],
]

const testimonials = [
  ['“Finally, clarity beyond the marketing.”', 'I can quickly see what is actually in my kids’ snacks.', 'Ananya S., Parent'],
  ['“Peace of mind when it matters.”', 'Real cross-checks make managing dietary needs much easier.', 'Rahul M., Shopper'],
  ['“No more guessing at the shelf.”', 'Independent evidence has changed how I fill my cart.', 'Vikram K., Fitness Enthusiast'],
]

function CardSymbol({ type }: { type: number }) {
  const paths = [
    <><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" /><circle cx="12" cy="12" r="2.5" /></>,
    <><path d="M9 3h6M10 3v5l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3M8 14h8" /></>,
    <><path d="m12 3 8 4-8 4-8-4 8-4Z" /><path d="m4 12 8 4 8-4M4 17l8 4 8-4" /></>,
  ]
  return <span className="card-symbol" aria-hidden="true"><svg viewBox="0 0 24 24">{paths[type]}</svg></span>
}

function Product({ name, src }: { name: string; src: string }) {
  return (
    <div className="product">
      <img src={src} alt={name} />
      <span>{name}</span>
    </div>
  )
}

const comparisons = [
  {
    category: 'Instant Noodles',
    filter: 'Noodles',
    left: { name: 'Maggi 2-Minute', image: '/products/comparison/maggi.png', score: '58', note: 'Check sodium and serving size' },
    right: { name: 'Top Ramen Masala', image: '/products/comparison/top-ramen.png', score: '55', note: 'Compare fat and sodium' },
    verdict: 'Classic noodle matchup',
  },
  {
    category: 'Alternative Noodles',
    filter: 'Noodles',
    left: { name: 'Gluten Free 5 Grain', image: '/products/comparison/gluten-free-noodles.png', score: '78', note: 'Multi-grain, gluten-free claim' },
    right: { name: 'Moi Soi Konjac', image: '/products/comparison/moi-soi.png', score: '82', note: 'Low-calorie konjac noodles' },
    verdict: 'Check your dietary fit',
  },
  {
    category: 'Biscuits',
    filter: 'Biscuits',
    left: { name: 'NutriChoice Oats', image: '/products/comparison/nutri-choice.png', score: '69', note: 'Oats claim, verify sugar' },
    right: { name: 'Unibic Butter Cookies', image: '/products/comparison/unibic.png', score: '52', note: 'Indulgent butter cookie' },
    verdict: 'Health claim vs treat',
  },
  {
    category: 'Tea-Time Snacks',
    filter: 'Snacks',
    left: { name: 'Potata Biscuits', image: '/products/comparison/potata.png', score: '51', note: 'Review refined flour and salt' },
    right: { name: 'NutriChoice Oats', image: '/products/comparison/nutri-choice.png', score: '69', note: 'Compare fibre per serving' },
    verdict: 'Compare the full label',
  },
  {
    category: 'Sweet Drinks',
    filter: 'Fruit drinks',
    left: { name: 'Maaza Mango', image: '/products/comparison/maaza.png', score: '46', note: 'Fruit drink; inspect added sugar' },
    right: { name: 'Pepsi', image: '/products/comparison/pepsi.png', score: '34', note: 'Carbonated sugary drink' },
    verdict: 'Sugar is the key check',
  },
  {
    category: 'Soft Drinks',
    filter: 'Soft drinks',
    left: { name: 'Pepsi', image: '/products/comparison/pepsi.png', score: '34', note: 'Compare sugar and caffeine' },
    right: { name: '7UP', image: '/products/comparison/seven-up.png', score: '36', note: 'Compare sugar per 100 ml' },
    verdict: 'Similar product category',
  },
]

const preferenceGroups = [
  { title: 'Dietary Conditions', symbol: '01', options: ['Diabetes', 'Prediabetes', 'High blood pressure', 'High cholesterol', 'Coeliac disease / medically required gluten avoidance', 'Lactose intolerance'] },
  { title: 'Allergies', symbol: '02', options: ['Peanuts', 'Tree nuts', 'Milk / dairy proteins', 'Eggs', 'Soy', 'Wheat', 'Gluten', 'Sesame', 'Fish / shellfish'] },
  { title: 'Nutrition Goals', symbol: '03', options: ['More protein', 'Lower calories', 'Lower sugar', 'Higher fibre', 'Lower sodium', 'Lower saturated fat'] },
  { title: 'Ingredients to Avoid', symbol: '04', options: ['Palm oil', 'Artificial sweeteners', 'Added sugar', 'Caffeine', 'Gelatin / animal-derived ingredients'] },
  { title: 'Dietary Pattern', symbol: '05', options: ['No specific dietary pattern', 'Vegetarian', 'Vegan', 'Vegetarian + eggs', 'Jain food preferences'] },
]

const basicPreferenceGroups = [
  { ...preferenceGroups[1], symbol: '01', options: ['Peanuts', 'Milk / dairy proteins', 'Gluten'] },
  { ...preferenceGroups[2], symbol: '02', options: ['More protein', 'Lower sugar', 'Higher fibre', 'Lower sodium'] },
  { ...preferenceGroups[3], symbol: '03', options: ['Palm oil', 'Artificial sweeteners', 'Added sugar'] },
]

const formulaNotes: Record<number, { title: string; formula: string; why: string; status: string }> = {
  1: { title: 'Nutrient rating', formula: '1 if actual ≤ limit; otherwise min(10, 1 + ceil(excess × 9)), where excess = (actual − limit) / limit.', why: 'Each step represents about 11% over the limit; double the limit reaches 10.', status: 'Design choice. The factor of 9 is tunable.' },
  2: { title: 'Per-serving limit', formula: 'Daily limit × serving share (15–20%).', why: 'Guidelines usually provide daily limits rather than per-product limits.', status: 'Assumption. The serving share is configurable.' },
  3: { title: 'Daily limits', formula: 'Sugar, salt and fat limits are drawn from ICMR-NIN, WHO and ADA guidance.', why: 'These benchmarks anchor the nutrient assessment.', status: 'Sourced; figures should be checked against the original documents.' },
  4: { title: 'Condition profiles', formula: 'Use the strictest limit and highest weight across selected conditions.', why: 'Provides a cautious result when several conditions apply.', status: 'Design choice. Condition weights require dietitian review.' },
  5: { title: 'Nutrient score', formula: 'Base = Σ(w·r)/Σw; final = max(base, 0.7·worst + 0.3·base).', why: 'Prevents one high-risk nutrient from being hidden by an average.', status: 'Design choice. The 0.7/0.3 weighting is not from a guideline.' },
  6: { title: 'Ingredient score', formula: 'Use position weights (first = n, last = 1), or printed percentages, with the same worst-item override.', why: 'Ingredients are generally listed in descending quantity.', status: 'Design choice. The weighting values are configurable.' },
  7: { title: 'Ingredient risk & uncertainty', formula: 'Risk values use 1–10; confidence scaling is resolved 1.0, alternatives 0.6, possible 0.4.', why: 'Reflects both ingredient concern and identification certainty.', status: 'Assumption. Each risk value needs a cited rationale.' },
  8: { title: 'Product rating', formula: '0.6 × nutrient score + 0.4 × ingredient score.', why: 'Measured nutrient limits receive slightly more weight.', status: 'Design choice.' },
  9: { title: 'Claim thresholds', formula: 'Example: “sugar free” requires ≤ 0.5 g sugar per 100 g.', why: 'Used to verify regulated package claims.', status: 'Sourced from and checked against FSSAI documentation.' },
  10: { title: 'Lab gap', formula: '(lab result − label value) / label value × 100, with a tolerance.', why: 'Shows how far an independent lab result differs from the label.', status: 'Standard calculation; the tolerance is currently a placeholder.' },
  11: { title: 'Age & colour bands', formula: 'Report age bands: 2 and 5 years. Rating colour boundaries: 3, 5 and 7.', why: 'Makes older evidence and higher ratings easier to identify.', status: 'Design choice.' },
  12: { title: 'Allergy check', formula: 'Rule matching against ingredient names and known aliases.', why: 'Flags selected allergens without calculating a numeric score.', status: 'Rule-based. Accuracy depends on alias-list completeness.' },
}

function FormulaInfo({ ids }: { ids: number[] }) {
  return (
    <span className="formula-info" aria-label={`Methodology information: ${ids.map(id => formulaNotes[id].title).join(', ')}`}>
      <span className="formula-icon" aria-hidden="true">i</span>
      <span className="formula-tooltip" role="tooltip">
        {ids.map(id => {
          const note = formulaNotes[id]
          return <span className="formula-note" key={id}><b>{note.title}</b><span><strong>Formula</strong>{note.formula}</span><span><strong>Why</strong>{note.why}</span><span><strong>Status</strong>{note.status}</span></span>
        })}
      </span>
    </span>
  )
}

function ComparisonCard({ item }: { item: (typeof comparisons)[number] }) {
  return (
    <article className="comparison-card">
      <div className="comparison-top"><span>{item.category}</span><b>{item.verdict}</b></div>
      <div className="comparison-products">
        {[item.left, item.right].map((product, index) => (
          <div className="compare-product" key={`${product.name}-${index}`}>
            <div className={`compare-image ${product.image.split('/').pop()?.replace('.png', '')} ${
              ['nutri-choice', 'unibic', 'potata'].some(name => product.image.includes(name))
                ? 'wide-pack'
                : ['maaza', 'pepsi', 'seven-up'].some(name => product.image.includes(name))
                  ? 'bottle-pack'
                  : 'tall-pack'
            }`}><img src={product.image} alt={product.name} /></div>
            <h3>{product.name}</h3>
            <p>{product.note}</p>
            <div className="score"><strong>{product.score}</strong><span>/ 100<br />match</span></div>
          </div>
        ))}
        <span className="versus">VS</span>
      </div>
    </article>
  )
}

const nutrients = [
  ['Total / Added Sugars', '2g', '15g', '0%', '1/10', '3', 'Per serving', 'ICMR-NIN 2024'],
  ['Sodium', '860mg', '300mg', '+186.7%', '10/10', '3', 'Per serving', 'ICMR-NIN 2024'],
  ['Saturated Fat', '14.3g', '3g', '+376.7%', '10/10', '2.5', 'Per serving', 'ICMR-NIN 2024'],
  ['Total Fat', '32.4g', '8g', '+305%', '10/10', '1.5', 'Per serving', 'ICMR-NIN 2024'],
  ['Carbohydrates', '54.6g', '25g', '+118.4%', '10/10', '1', 'Per serving', 'ICMR-NIN 2024'],
]

function getSeverityColor(score: number) {
  const severity = Math.min(10, Math.max(0, score))
  const lightness = 78 - severity * 4.2
  return `hsl(2 72% ${lightness}%)`
}

function AuditPage({ product, preferences, onBack }: { product: string; preferences: string[]; onBack: () => void }) {
  const personalisedRating = 8.26
  const severityColor = getSeverityColor(personalisedRating)
  const needleAngle = -180 + (personalisedRating / 10) * 180
  const [query, setQuery] = useState(product)
  const [shownProduct, setShownProduct] = useState(product)
  const [nutrientsOpen, setNutrientsOpen] = useState(false)
  const [ingredientsOpen, setIngredientsOpen] = useState(false)
  const [productOpen, setProductOpen] = useState(false)
  const [claimsOpen, setClaimsOpen] = useState(false)
  const [standardsOpen, setStandardsOpen] = useState(false)
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const [advisoriesOpen, setAdvisoriesOpen] = useState(false)
  return (
    <main className="audit-page">
      <header className="audit-header">
        <button className="audit-brand" onClick={onBack}><b>LT</b><span>LabelTruth<small>Packaged food claims & ingredients auditor</small></span></button>
        <button className="audit-history">Search history</button>
      </header>
      <div className="audit-wrap">
        <form className="audit-search" onSubmit={event => { event.preventDefault(); if (query.trim()) setShownProduct(query.trim()) }}>
          <input value={query} onChange={event => setQuery(event.target.value)} aria-label="Product name" />
          <button type="submit">Search product <span>→</span></button>
          <div className="audit-suggestions"><b>Suggestions:</b>{['Maggi 2-Minute Noodles', 'Lay’s Potato Chips', 'Coca-Cola Zero', 'Amul Butter'].map(item => <button type="button" onClick={() => { setQuery(item); setShownProduct(item) }} key={item}>{item}</button>)}</div>
        </form>

        <div className="live-strip"><span><i /> Live verified audit</span><b>9 verified sources</b></div>

        <div className="allergy-strip standalone"><b>Allergy status: {preferences.some(item => ['Peanuts', 'Tree nuts', 'Milk / dairy proteins', 'Eggs', 'Soy', 'Wheat', 'Gluten', 'Sesame', 'Fish / shellfish'].includes(item)) ? 'Review required' : 'None found'} <FormulaInfo ids={[12]} /></b><span>Your allergens: {preferences.filter(item => preferenceGroups[1].options.includes(item)).join(', ') || 'None selected'}</span></div>

        <section className="audit-detail-grid">
          <div className="report-left">
            <article className="claims-card">
              <button className="card-toggle" onClick={() => setClaimsOpen(!claimsOpen)}><span>Claims verification (4) <FormulaInfo ids={[9]} /></span><b>{claimsOpen ? '−' : '+'}</b></button>
              <div className="claim-legend"><i className="verified">Verified</i><i className="misleading">Misleading</i><i className="contradicted">Contradicted</i><i className="no-evidence">No evidence</i></div>
              {claimsOpen && <div className="claim-list">
                <div><b>“Ready in 2 minutes”</b><em className="verified">Verified</em><p>Preparation instruction is supported by the product label.</p><a href="#sources">Cited from label source →</a></div>
                <div><b>“Source of protein”</b><em className="misleading">Misleading</em><p>Protein per serving does not clearly meet the statutory claim threshold.</p><a href="#standards">View applicable standard →</a></div>
                <div><b>“Better-for-you snack”</b><em className="contradicted">Contradicted</em><p>High sodium and saturated fat conflict with the implied health positioning.</p><a href="#nutrients">View nutrient evidence →</a></div>
                <div><b>“Quality ingredients”</b><em className="no-evidence">No evidence</em><p>No measurable definition or independent evidence was found.</p></div>
              </div>}
            </article>
            <article className="ingredients-card"><span>Ingredients</span><p><b>Edible vegetable oil</b> (palmolein), wheat flour, seasoning, sugar, iodised salt, spices, acidity regulators, flavour enhancers and milk solids.</p><div className="ingredient-flags"><i>Palm oil</i><i>Allergen</i><i>Additive</i></div></article>
            <article className="coverage-card"><b>Independent lab & regulatory coverage <FormulaInfo ids={[10]} /></b><p>Cross-checked against package details, nutrition guidance, and available independent sources.</p><a href="#sources">View reference report →</a></article>
            <div className="technical-report">
              <article className="technical-card">
                <div className="technical-head"><b>Risk & regulatory audit</b><div><i className="critical">Fail / critical</i><i className="evidence">Evidence-backed</i></div><a href="#standards">View full report</a></div>
                <h3>FSSAI & ICMR-NIN risk-level finding</h3>
                <p>Serving-level nutrient and ingredient findings assessed against applicable Indian dietary and claim standards.</p>
                <div className="technical-metrics"><div><span>Regulatory status</span><b>Limit exceeded</b></div><div><span>Evidence confidence</span><b>High confidence</b></div><div><span>Citations checked</span><b>8 sources</b></div><div><span>Market assessed</span><b>India</b></div></div>
                <dl><div><dt>Product status</dt><dd>High sodium and saturated fat per serving; front-of-pack positioning requires context.</dd></div><div><dt>Clinical rationale</dt><dd>Frequent intake may conflict with sodium, saturated-fat, and cardiometabolic dietary goals.</dd></div><div><dt>Regulatory basis</dt><dd>Benchmarked against FSSAI claim rules and ICMR-NIN dietary guidance.</dd></div></dl>
              </article>
              <article className="technical-card">
                <div className="technical-head"><b>Risk & consumer-use note</b><div><i className="caution">Caution</i><i className="evidence">Evidence-backed</i></div><a href="#sources">View source report</a></div>
                <h3>Consumer-use & intake-frequency note</h3>
                <p>Risk interpretation based on the declared serving and available package information.</p>
                <div className="technical-metrics five"><div><span>Product type</span><b>Packaged snack</b></div><div><span>Primary concern</span><b>Sodium / fat</b></div><div><span>Serving basis</span><b>Per pack</b></div><div><span>HFSS signal</span><b className="high-signal">High</b></div><div><span>Recommended use</span><b>Occasional</b></div></div>
                <dl><div><dt>Practical note</dt><dd>Compare serving sizes and frequency; pair with minimally processed foods where possible.</dd></div><div><dt>Evidence context</dt><dd>Assessment does not replace medical advice and may change with reformulation.</dd></div></dl>
              </article>
            </div>
          </div>
          <div className="report-right">
            <article className="score-panel risk">
              <div className="score-title"><span>Personalised rating <FormulaInfo ids={[4, 8, 11]} /></span><div className="rating-result" style={{ '--severity-red': severityColor } as React.CSSProperties}><strong>{personalisedRating.toFixed(2)}<small>/10</small></strong><div className="rating-gauge" role="meter" aria-label="High risk severity" aria-valuemin={0} aria-valuemax={10} aria-valuenow={personalisedRating} style={{ '--needle-angle': `${needleAngle}deg` } as React.CSSProperties}><i /><b>High risk</b></div></div></div>
              <b className="risk-label">High risk / exceeds limits</b>
              <div className="subscores"><div><strong>9.26</strong><span>Nutrient rating</span></div><div><strong>6.77</strong><span>Ingredient rating</span></div></div>
            </article>

            <article className="alternatives-card">
              <div className="alternatives-heading">
                <div><span>Smarter swaps</span><h2>Suggested alternatives</h2></div>
                <p>Compare the full label before choosing.</p>
              </div>
              <div className="alternative-list">
                {[
                  { name: 'Moi Soi Konjac Noodles', image: '/products/comparison/moi-soi.png', reason: 'Lower-calorie noodle base', score: '3.2' },
                  { name: 'Gluten Free 5 Grain', image: '/products/comparison/gluten-free-noodles.png', reason: 'Multi-grain alternative', score: '4.1' },
                  { name: 'Top Ramen Masala', image: '/products/comparison/top-ramen.png', reason: 'Compare sodium per serving', score: '5.5' },
                ].map(alternative => (
                  <div className="alternative-product" key={alternative.name}>
                    <img src={alternative.image} alt="" />
                    <div><b>{alternative.name}</b><span>{alternative.reason}</span></div>
                    <strong>{alternative.score}<small>/10</small></strong>
                  </div>
                ))}
              </div>
            </article>

            <section className="breakdown" id="nutrients">
              <button onClick={() => setNutrientsOpen(!nutrientsOpen)}><span>Nutrient breakdown & citations <FormulaInfo ids={[1, 2, 3, 5]} /></span><b>{nutrientsOpen ? '−' : '+'}</b></button>
              {nutrientsOpen && <div className="table-wrap"><table><thead><tr><th>Nutrient</th><th>Actual</th><th>Limit</th><th>Excess</th><th>Risk score</th><th>Weight</th><th>Basis</th><th>Source</th></tr></thead><tbody>{nutrients.map(row => <tr key={row[0]}>{row.map((cell,index) => <td key={`${cell}-${index}`}>{index === 4 ? <b>{cell}</b> : cell}</td>)}</tr>)}</tbody></table></div>}
            </section>

            <section className="breakdown">
              <button onClick={() => setIngredientsOpen(!ingredientsOpen)}><span>Top contributing ingredients <FormulaInfo ids={[6, 7]} /></span><b>{ingredientsOpen ? '−' : '+'}</b></button>
              {ingredientsOpen && <div className="ingredient-table">
                <div className="ingredient-head"><span>Ingredient</span><span>Position</span><span>Weight</span><span>Risk</span><span>Reason / finding</span><span>Citation</span></div>
                <article><b>Edible vegetable oil<br /><small>(Palmolein, sunflower oil)</small></b><span>#2</span><span>3</span><strong>8/10</strong><p>Palmolein contains saturated fatty acids and is a major contributor to the overall HFSS classification.</p><a href="#standards">ICMR-NIN 2024</a></article>
                <article><b>Seasoning blend<br /><small>Salt, spices, additives</small></b><span>#3</span><span>2</span><strong>5/10</strong><p>Flavour enhancers, processed starches, and elevated sodium increase the ingredient risk.</p><a href="#standards">FSSAI Additives</a></article>
                <article><b>Refined wheat flour</b><span>#1</span><span>1</span><strong>4/10</strong><p>Primary refined carbohydrate; review against fibre goals and gluten restrictions.</p><a href="#standards">ICMR-NIN 2024</a></article>
              </div>}
            </section>

            <section className="breakdown analysed-dropdown">
              <button onClick={() => setProductOpen(!productOpen)}><span>Analysed product</span><b>{productOpen ? '−' : '+'}</b></button>
              {productOpen && <article className="product-summary">
                <div className="product-title"><div><span>Product overview</span><h2>{shownProduct}</h2><p>Savoury packaged food · India</p></div><img src="/products/comparison/maggi.png" alt="" /></div>
                <div className="warning-box"><b>Palm oil detected</b><p>Listed as a cooking oil and associated with higher saturated fat.</p></div>
                <div className="summary-box"><b>Audit summary</b><p>This product is high in sodium and saturated fat per serving. Review portion size and the complete ingredient statement.</p></div>
                <h3>Nutrition facts <small>(per serving)</small></h3>
                <div className="fact-grid">{[['Calories','536 kcal'],['Carbohydrates','54.6g'],['Total sugars','2g'],['Protein','6.4g'],['Total fat','32.4g'],['Saturated fat','14.3g'],['Sodium','860mg'],['Added sugar','2g']].map(([label,value]) => <div key={label}><span>{label}</span><b>{value}</b></div>)}</div>
              </article>}
            </section>

          </div>
        </section>

        <section className="breakdown report-section" id="sources">
          <button onClick={() => setSourcesOpen(!sourcesOpen)}><span>Audit evidence & source traceability <FormulaInfo ids={[10, 11]} /></span><b>{sourcesOpen ? '−' : '+'}</b></button>
          {sourcesOpen && <div className="source-content">
            <div className="source-status"><span>Source verification status</span><b>9 verified sources</b><i>Live audit</i></div>
            <div className="source-grid">
              <article><span>Primary product label</span><b>Nutrition panel & ingredient list</b><p>Serving size, nutrient values, allergen declaration, additives, and pack claims.</p><i>Verified</i></article>
              <article><span>Official brand listing</span><b>Product description & claims</b><p>Cross-checked against current manufacturer product information.</p><i>Verified</i></article>
              <article><span>Retailer listing</span><b>Pack imagery & availability</b><p>Used to compare visible front-of-pack wording and package details.</p><i>Corroborated</i></article>
              <article><span>Regulatory references</span><b>FSSAI, ICMR-NIN & WHO</b><p>Thresholds and dietary benchmarks used in the evidence assessment.</p><i>Verified</i></article>
            </div>
            <div className="extraction-row"><b>Extraction basis</b><span>Per serving · India market · Current visible package · Front and back label review</span></div>
          </div>}
        </section>

        <section className="breakdown report-section">
          <button onClick={() => setAdvisoriesOpen(!advisoriesOpen)}><span>Scientific & compliance citations (advisories)</span><b>{advisoriesOpen ? '−' : '+'}</b></button>
          {advisoriesOpen && <div className="advisory-list">
            <article><b>Palmolein & saturated fat</b><span>Nutrition advisory</span><p>Frequent high saturated-fat intake may contribute to elevated cardiovascular risk. Assessment depends on total diet and serving frequency.</p><a href="#standards">ICMR-NIN Dietary Guidelines for Indians, 2024</a></article>
            <article><b>Sodium & hypertension</b><span>Clinical advisory</span><p>High sodium intake is associated with increased blood pressure risk. This product exceeds the selected per-serving benchmark.</p><a href="#standards">WHO Sodium Intake Guideline</a></article>
            <article><b>Food additives & flavour enhancers</b><span>Compliance note</span><p>Permitted additives must remain within regulatory limits and be declared using the applicable class name or INS number.</p><a href="#standards">FSSAI Food Product Standards and Additives Regulations</a></article>
          </div>}
        </section>

        <section className="breakdown standards" id="standards">
          <button onClick={() => setStandardsOpen(!standardsOpen)}><span>Statutory standards & reference citations <FormulaInfo ids={[2, 3, 9]} /></span><b>{standardsOpen ? '−' : '+'}</b></button>
          {standardsOpen && <div className="standards-content">
            <h3>FSSAI statutory claim standards</h3>
            <div className="standards-grid">
              <article><b>High Protein / Rich in Protein</b><span>Statutory standard</span><p>Threshold: 10.8g / 100g or 20% of adult daily RDA.</p><a href="#sources">Food Safety and Standards Regulations</a></article>
              <article><b>Source of Protein</b><span>Statutory standard</span><p>Threshold: 5.4g / 100g or 10% of adult daily RDA.</p><a href="#sources">Advertising and Claims Regulations</a></article>
            </div>
            <h3>ICMR-NIN 2024 & WHO dietary guidelines</h3>
            <div className="standards-grid">
              <article><b>Daily Salt Upper Limit</b><span>Official guideline</span><p>Daily benchmark: 5g salt / 2000mg sodium.</p><a href="#sources">ICMR-NIN Dietary Guidelines 2024</a></article>
              <article><b>Daily Added Sugar Upper Limit</b><span>Official guideline</span><p>Upper limit: 25g/day for adults.</p><a href="#sources">WHO Free Sugars Guideline</a></article>
              <article><b>Total Fat Percentage of Energy</b><span>Official guideline</span><p>Daily benchmark: 30% of total energy.</p><a href="#sources">ICMR-NIN Dietary Guidelines 2024</a></article>
              <article><b>Minimum Daily Dietary Fibre</b><span>Official guideline</span><p>Daily benchmark: 30g/day from varied food sources.</p><a href="#sources">ICMR-NIN Dietary Guidelines 2024</a></article>
              <article><b>WHO Free Sugars Intake</b><span>Official guideline</span><p>Free sugars should remain below 10% of total daily energy intake.</p><a href="#sources">WHO Sugars Intake Guideline</a></article>
              <article><b>WHO Sodium Intake</b><span>Official guideline</span><p>Recommended maximum: 2000mg sodium per day for adults.</p><a href="#sources">WHO Sodium Guideline</a></article>
            </div>
            <h3>Diabetes clinical nutrition guidance</h3>
            <div className="standards-grid">
              <article><b>Carbohydrate per snack serving</b><span>Clinical assumption</span><p>Reference guideline: 15g carbohydrate per serving.</p><a href="#sources">ADA Standards of Care</a></article>
              <article><b>Added sugar target</b><span>Clinical assumption</span><p>Low added-sugar choices are preferred for glucose-management profiles.</p><a href="#sources">ADA & RSSDI Guidance</a></article>
            </div>
          </div>}
        </section>
        <p className="audit-disclaimer">Demonstration audit only. Values and scores must be verified against the exact product label and qualified dietary guidance.</p>
      </div>
    </main>
  )
}

export default function App() {
  const [openFaq, setOpenFaq] = useState(0)
  const [scrollProgress, setScrollProgress] = useState(0)
  const [authOpen, setAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login')
  const [authStep, setAuthStep] = useState<'form' | 'personalize'>('form')
  const [personalizationMode, setPersonalizationMode] = useState<'basic' | 'complete'>('basic')
  const [submitted, setSubmitted] = useState(false)
  const [preferences, setPreferences] = useState<string[]>([])
  const [productQuery, setProductQuery] = useState('')
  const [auditedProduct, setAuditedProduct] = useState('')
  const [compareFilter, setCompareFilter] = useState('All products')
  const searchRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const updateProgress = () => {
      const available = document.documentElement.scrollHeight - window.innerHeight
      setScrollProgress(available > 0 ? window.scrollY / available : 0)
      const searchScroll = Math.min(window.scrollY / 180, 1)
      searchRef.current?.style.setProperty('--search-scroll', String(searchScroll))
      searchRef.current?.style.setProperty('--search-scale', String(1 - searchScroll * 0.035))
      searchRef.current?.style.setProperty('--search-opacity', String(1 - searchScroll * 0.12))
    }
    const observer = new IntersectionObserver(
      entries => entries.forEach(entry => entry.isIntersecting && entry.target.classList.add('is-visible')),
      { threshold: 0.12 },
    )
    document.querySelectorAll('.section, footer').forEach(section => observer.observe(section))
    window.addEventListener('scroll', updateProgress, { passive: true })
    updateProgress()
    return () => {
      observer.disconnect()
      window.removeEventListener('scroll', updateProgress)
    }
  }, [])

  useEffect(() => {
    document.body.style.overflow = authOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [authOpen])

  const openAuth = (mode: 'login' | 'signup') => {
    setAuthMode(mode)
    setAuthStep('form')
    setSubmitted(false)
    setAuthOpen(true)
  }

  const togglePreference = (option: string) => {
    setPreferences(current => current.includes(option) ? current.filter(item => item !== option) : [...current, option])
  }

  if (auditedProduct) {
    return <AuditPage product={auditedProduct} preferences={preferences} onBack={() => setAuditedProduct('')} />
  }

  return (
    <main>
      <div className="scroll-progress" style={{ transform: `scaleX(${scrollProgress})` }} />
      <header>
        <a className="brand" href="#home">Label<span>Truth</span></a>
        <nav aria-label="Main navigation">
          <a href="#home">Home</a><a href="#about">About</a><a href="#features">Features</a><a href="#compare">Compare</a><a href="#faq">FAQ</a>
        </nav>
        <button className="login" onClick={() => openAuth('login')}>Log in</button>
      </header>

      {authOpen && (
        <div className="auth-page" role="dialog" aria-modal="true" aria-label={authMode === 'login' ? 'Log in' : 'Create account'}>
          <button className="auth-backdrop" aria-label="Close account form" onClick={() => setAuthOpen(false)} />
          <section className={`auth-shell ${authStep === 'personalize' ? 'personalize-shell' : ''}`}>
            <button className="auth-close" onClick={() => setAuthOpen(false)} aria-label="Close">×</button>
            {authStep === 'personalize' ? (
              <div className="personalization">
                <button className="personalization-back" onClick={() => setAuthStep('form')}>← Back to account</button>
                <div className="personalization-heading">
                  <span>{personalizationMode === 'basic' ? 'THE ESSENTIALS' : 'MAKE LABELTRUTH YOURS'}</span>
                  <h2>{personalizationMode === 'basic' ? 'Set Your Basic Preferences' : 'Personalise Your Experience'}</h2>
                  <p>{personalizationMode === 'basic' ? 'Choose a few priorities for more relevant product checks.' : 'Select everything that applies. You can change these choices later.'}</p>
                </div>
                <div className="preference-groups">
                  {(personalizationMode === 'basic' ? basicPreferenceGroups : preferenceGroups).map(group => (
                    <fieldset className="preference-group" key={group.title}>
                      <legend><span>{group.symbol}</span>{group.title}</legend>
                      <div className="preference-options">
                        {group.options.map(option => {
                          const selected = preferences.includes(option)
                          return <button type="button" className={selected ? 'selected' : ''} onClick={() => togglePreference(option)} key={option} aria-pressed={selected}>
                            <i>{selected ? '✓' : '+'}</i>{option}
                          </button>
                        })}
                      </div>
                    </fieldset>
                  ))}
                </div>
                <div className="personalization-footer">
                  <span>{preferences.length} selected</span>
                  <button onClick={() => { setSubmitted(true); setAuthStep('form') }}>{preferences.length ? 'Save preferences' : 'Skip for now'}<b>→</b></button>
                </div>
              </div>
            ) : <>
            <div className="auth-art">
              <a className="brand" href="#home" onClick={() => setAuthOpen(false)}>Label<span>Truth</span></a>
              <div className="auth-art-copy">
                <span>KNOW WHAT’S INSIDE</span>
                <h2>Better choices start with the truth.</h2>
                <p>Save comparisons, revisit evidence, and make every shopping decision with confidence.</p>
              </div>
              <div className="auth-mini-products" aria-hidden="true">
                <img src="/products/corn-flakes.png" alt="" />
                <img src="/products/dark-chocolate.png" alt="" />
                <img src="/products/fruit-juice.png" alt="" />
              </div>
            </div>
            <div className="auth-form-side">
              <div className="auth-tabs">
                <button className={authMode === 'login' ? 'active' : ''} onClick={() => { setAuthMode('login'); setSubmitted(false) }}>Log in</button>
                <button className={authMode === 'signup' ? 'active' : ''} onClick={() => { setAuthMode('signup'); setSubmitted(false) }}>Sign up</button>
              </div>
              <div className="auth-heading">
                <span>{authMode === 'login' ? 'WELCOME BACK' : 'JOIN LABELTRUTH'}</span>
                <h2>{authMode === 'login' ? 'Log in to your account' : 'Create your account'}</h2>
                <p>{authMode === 'login' ? 'Continue making informed food choices.' : 'Start saving smarter product comparisons.'}</p>
              </div>
              {submitted ? (
                <div className="auth-success">
                  <span>✓</span>
                  <h3>{authMode === 'login' ? 'Login form submitted' : 'Account details received'}</h3>
                  <p>This is currently a frontend preview. Connect authentication later to enable real accounts.</p>
                  <button onClick={() => setSubmitted(false)}>Back to form</button>
                </div>
              ) : (
                <form className="auth-form" onSubmit={(event) => { event.preventDefault(); setSubmitted(true) }}>
                  {authMode === 'signup' && <label>Full name<input name="name" type="text" placeholder="Your name" autoComplete="name" required /></label>}
                  <label>Email address<input name="email" type="email" placeholder="you@example.com" autoComplete="email" required /></label>
                  <label>Password<input name="password" type="password" placeholder="At least 8 characters" autoComplete={authMode === 'login' ? 'current-password' : 'new-password'} minLength={8} required /></label>
                  {authMode === 'signup' && <label className="auth-consent"><input type="checkbox" required /><span>I agree to the Terms and Privacy Policy.</span></label>}
                  {authMode === 'login' && <button className="forgot" type="button">Forgot password?</button>}
                  <button className="auth-submit" type="submit">{authMode === 'login' ? 'Log in' : 'Create account'}<span>→</span></button>
                </form>
              )}
              <p className="auth-switch">{authMode === 'login' ? 'New to LabelTruth?' : 'Already have an account?'} <button onClick={() => { setAuthMode(authMode === 'login' ? 'signup' : 'login'); setSubmitted(false) }}>{authMode === 'login' ? 'Create an account' : 'Log in'}</button></p>
              <div className="auth-paths">
                <button onClick={() => { setPersonalizationMode('basic'); setAuthStep('personalize') }}>Just a concerned consumer <span>Set basic preferences →</span></button>
                <button onClick={() => { setPersonalizationMode('complete'); setAuthStep('personalize') }}>I need more personalisation <span>Build my complete profile →</span></button>
              </div>
            </div>
            </>}
          </section>
        </div>
      )}

      <section className="hero" id="home">
        <div className="search-shell" ref={searchRef}>
          <form className="search" onSubmit={event => { event.preventDefault(); if (productQuery.trim()) setAuditedProduct(productQuery.trim()) }}>
            <input value={productQuery} onChange={event => setProductQuery(event.target.value)} placeholder="Search a product or ingredient" aria-label="Search a product or ingredient" />
            <button className="search-submit" type="submit" aria-label="Search product">⌕</button>
          </form>
        </div>
        <p className="eyebrow">Clear claims. Credible evidence.</p>
        <h1>Question the claim.<br />Verify the <em>proof.</em></h1>
        <p className="subhead">Look past the label. Compare the facts.</p>
        <div className="products" aria-label="Example verified products">
          <Product name="Kellogg's Corn Flakes" src="/products/corn-flakes.png" />
          <Product name="Farmley Peri-Peri Makhana" src="/products/makhana.png" />
          <Product name="Amul Dark Chocolate" src="/products/dark-chocolate.png" />
          <Product name="Real Mixed Fruit Juice" src="/products/fruit-juice.png" />
          <Product name="Makino Corn Munch" src="/products/corn-munch.png" />
        </div>
      </section>

      <section className="food-gallery" aria-label="Packaged foods in stores">
        <div className="gallery-copy">
          <span>FROM THE AISLE</span>
          <h2>Real products.<br />Clearer choices.</h2>
        </div>
        <figure>
          <img src="https://images.unsplash.com/photo-1688217170693-e821c6e18d72?auto=format&fit=crop&w=900&q=82" alt="Colourful packaged snacks displayed in a store" />
          <figcaption>Snacks</figcaption>
        </figure>
        <figure>
          <img src="https://images.unsplash.com/photo-1641652682537-e1a9334f206d?auto=format&fit=crop&w=900&q=82" alt="Packaged food products on grocery shelves" />
          <figcaption>Everyday foods</figcaption>
        </figure>
        <figure>
          <img src="https://images.unsplash.com/photo-1604719312245-6d2c47114758?auto=format&fit=crop&w=900&q=82" alt="Rows of packaged grocery products" />
          <figcaption>Pantry staples</figcaption>
        </figure>
      </section>

      <section className="section reality">
        <div className="section-heading"><span>THE REALITY</span><h2>Why We Need This Now</h2><p>The truth shouldn’t be hidden behind the label.</p></div>
        <div className="grid three reality-cards">
          {[
            ['The Health Halo', 'Words like “clean” and “zero sugar” can distract from what is actually inside.'],
            ['The Evidence Gap', 'Independent tests can reveal what bold package claims leave out.'],
            ['The Ingredient Maze', 'Complex names make everyday labels difficult to understand.'],
          ].map(([title, copy], index) => <article className="card" key={title}><CardSymbol type={index} /><h3>{title}</h3><p>{copy}</p></article>)}
        </div>
      </section>

      <section className="section values" id="features">
        <div className="section-heading"><span>THE DIFFERENCE</span><h2>Why LabelTruth?</h2><p>Independent evidence, made personal.</p></div>
        <div className="grid three">{values.map(([title, copy]) => <article className="value" key={title}><i>✓</i><h3>{title}</h3><p>{copy}</p></article>)}</div>
      </section>

      <section className="section how">
        <div className="section-heading"><span>SIMPLE BY DESIGN</span><h2>How It Works</h2></div>
        <div className="how-layout">
          <figure className="how-visual">
            <img src="https://images.unsplash.com/photo-1667665908399-6d858dd26231?auto=format&fit=crop&w=1100&q=84" alt="Indian woman comparing products in a grocery aisle" />
            <figcaption><b>Shop smarter</b><span>Evidence at every step.</span></figcaption>
          </figure>
          <div className="steps">{steps.map(([number, title, copy]) => <article className="step" key={number}><b>{number}</b><div><h3>{title}</h3><p>{copy}</p></div></article>)}</div>
        </div>
      </section>

      <section className="section testimonials">
        <div className="section-heading left"><span>REAL STORIES</span><h2>What consumers say about LabelTruth</h2></div>
        <div className="grid three">{testimonials.map(([quote, copy, by]) => <article className="quote" key={quote}><h3>{quote}</h3><p>{copy}</p><small>— {by}</small></article>)}</div>
      </section>

      <section className="section compare" id="compare">
        <div className="section-heading">
          <span>PRODUCT MATCHUPS</span>
          <h2>Compare Beyond the Label</h2>
          <p>Quick evidence-led snapshots across popular food types.</p>
        </div>
        <div className="category-pills" aria-label="Product categories">
          {['All products', 'Noodles', 'Biscuits', 'Snacks', 'Fruit drinks', 'Soft drinks'].map(type => (
            <button
              type="button"
              className={compareFilter === type ? 'active' : ''}
              onClick={() => setCompareFilter(type)}
              aria-pressed={compareFilter === type}
              key={type}
            >
              {type}
            </button>
          ))}
        </div>
        <div className="comparison-grid">{comparisons.filter(item => compareFilter === 'All products' || item.filter === compareFilter).map(item => <ComparisonCard item={item} key={item.category} />)}</div>
        <p className="comparison-note">Scores are illustrative match summaries. Always review the full evidence for your dietary needs.</p>
      </section>

      <section className="section faq" id="faq">
        <div className="section-heading left"><span>QUESTIONS, ANSWERED</span><h2>FAQ</h2></div>
        <div className="faq-list">{faqs.map(([question, answer], index) => <article className={openFaq === index ? 'faq-item open' : 'faq-item'} key={question}>
          <button onClick={() => setOpenFaq(openFaq === index ? -1 : index)} aria-expanded={openFaq === index}><span>{question}</span><b>+</b></button>
          <div><p>{answer}</p></div>
        </article>)}</div>
      </section>

      <section className="section about" id="about">
        <div className="section-heading left"><span>ABOUT US</span><h2>Built for clarity, not clicks.</h2></div>
        <div className="about-grid">
          <article className="mission"><h3>Our Mission</h3><p>Make packaged-food claims clear, credible, and easy to compare.</p></article>
          <div><article><h3>Why We Built This</h3><p>Food labels are full of appealing claims but short on clear context.</p></article>
          <article><h3>How We Stand Apart</h3><p>We compare claims with nutrition data, regulations, and independent evidence.</p></article></div>
          <figure className="about-photo"><img src="https://images.unsplash.com/photo-1628102491629-778571d893a3?auto=format&fit=crop&w=900&q=84" alt="Shopper choosing groceries in a supermarket" /></figure>
        </div>
      </section>

      <footer>
        <div className="footer-brand"><a className="brand" href="#home">Label<span>Truth</span></a><p>Truth belongs on every label.</p><small>Independent food-claim clarity for everyday choices.</small></div>
        <div><b>Explore</b><a href="#about">About us</a><a href="#features">Why LabelTruth</a><a href="#compare">Compare products</a><a href="#faq">FAQ</a><a href="#home">How it works</a></div>
        <div><b>Contact</b><a href="mailto:hello@labeltruth.com">hello@labeltruth.com</a><a href="tel:+91987XXXXXXX">+91 987XX XXXXX</a><span>Arise Complex, Near RQS Building<br />ALT State, India</span></div>
        <div className="footer-support"><b>Need help?</b><p>Questions about a claim or product?</p><a className="support-button" href="tel:+91987XXXXXXX"><span aria-hidden="true">24/7</span> Support helpline</a></div>
        <div className="footer-bottom"><small>© 2025 LabelTruth. All rights reserved.</small><div><a href="#">Privacy</a><a href="#">Terms</a></div></div>
      </footer>
    </main>
  )
}
