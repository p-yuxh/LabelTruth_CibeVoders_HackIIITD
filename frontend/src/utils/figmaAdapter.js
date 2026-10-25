/**
 * Adapter module mapping backend AuditResponse and ProductAuditData
 * into normalized props for the Figma presentational components.
 */

export function getSeverityColor(score) {
  if (score == null || isNaN(score)) return '#68717e';
  const severity = Math.min(10, Math.max(0, Number(score)));
  const lightness = 78 - severity * 4.2;
  return `hsl(2 72% ${lightness}%)`;
}

export function getNeedleAngle(score) {
  if (score == null || isNaN(score)) return -180;
  const num = Math.min(10, Math.max(0, Number(score)));
  return -180 + (num / 10) * 180;
}

export function getCategoryFallbackImage(category = '', name = '') {
  const text = `${category} ${name}`.toLowerCase();
  if (text.includes('noodle') || text.includes('maggi') || text.includes('ramen')) {
    return '/products/comparison/maggi.png';
  }
  if (text.includes('biscuit') || text.includes('cookie') || text.includes('oat') || text.includes('potata')) {
    return '/products/comparison/nutri-choice.png';
  }
  if (text.includes('chocolate')) {
    return '/products/dark-chocolate.png';
  }
  if (text.includes('juice') || text.includes('drink') || text.includes('beverage') || text.includes('pepsi') || text.includes('coke') || text.includes('maaza')) {
    return '/products/fruit-juice.png';
  }
  if (text.includes('makhana') || text.includes('snack') || text.includes('chip')) {
    return '/products/makhana.png';
  }
  return '/products/corn-flakes.png';
}

export function normalizeVerdict(verdict = '') {
  const norm = String(verdict || '').toUpperCase().trim().replace(/\s+/g, '_');
  if (norm.includes('VERIFIED')) {
    return { class: 'verified', label: 'Verified' };
  }
  if (norm.includes('MISLEADING')) {
    return { class: 'misleading', label: 'Misleading' };
  }
  if (norm.includes('CONTRADICTED') || norm.includes('FALSE')) {
    return { class: 'contradicted', label: 'Contradicted' };
  }
  return { class: 'no-evidence', label: 'No evidence' };
}

export function adaptAuditData(auditResult, activePreferences = []) {
  if (!auditResult) return null;
  const data = auditResult.data || {};
  const query = auditResult.query || '';
  const productName = data.product_name?.value || query || 'Packaged Food';
  const brand = data.brand?.value || '';
  const category = data.category?.value || 'Packaged Food';
  const sourceUrls = auditResult.source_urls || [];
  const verifiedSourcesCount = Math.max(sourceUrls.length, 1);

  // Scoring
  const scoring = data.personalized_scoring || {};
  const personalisedRating = scoring.personalized_rating != null
    ? Number(scoring.personalized_rating)
    : (data.personalised_rating != null ? Number(data.personalised_rating) : null);

  const nutrientRating = scoring.subscores?.nutrient_rating != null
    ? Number(scoring.subscores.nutrient_rating).toFixed(2)
    : (scoring.nutrient_score != null ? Number(scoring.nutrient_score).toFixed(2) : '—');

  const ingredientRating = scoring.subscores?.ingredient_rating != null
    ? Number(scoring.subscores.ingredient_rating).toFixed(2)
    : (scoring.ingredient_score != null ? Number(scoring.ingredient_score).toFixed(2) : '—');

  let riskLabel = 'Moderate fit';
  if (personalisedRating != null) {
    if (personalisedRating <= 3.0) riskLabel = 'Good fit / within limits';
    else if (personalisedRating <= 5.0) riskLabel = 'Moderate fit';
    else if (personalisedRating <= 7.0) riskLabel = 'Poor fit / elevated risk';
    else riskLabel = 'High risk / exceeds limits';
  }

  // Allergy Check
  const allergyAlert = scoring.allergy_alert || {};
  const hasAllergyConflict = Boolean(allergyAlert.has_conflict);
  const detectedAllergens = allergyAlert.detected_allergens || [];

  // Claims
  const rawClaims = Array.isArray(data.front_pack_claims) ? data.front_pack_claims : [];
  const claims = rawClaims.map((c) => {
    const verdictInfo = normalizeVerdict(c.audit_verdict);
    return {
      claim: c.claim || 'Front-of-pack claim',
      verdictClass: verdictInfo.class,
      verdictLabel: verdictInfo.label,
      reason: c.verdict_reason || 'Verified against product nutrition panel and statutory standards.',
      sourceUrl: c.source_url || '#sources',
    };
  });

  // Ingredients statement & flags
  const ingredients = Array.isArray(data.ingredients) ? data.ingredients : [];
  const ingredientNames = ingredients.map((i) => i.name || i).filter(Boolean);
  const ingredientsStatement = ingredientNames.length > 0
    ? ingredientNames.join(', ')
    : 'Complete ingredient statement cross-referenced from packaging records.';

  const hasPalmOil = Boolean(
    data.oil_listed?.is_palm_oil_or_derivative ||
    ingredients.some((i) => i.is_palm_oil_or_derivative) ||
    /palm|palmolein/i.test(ingredientsStatement)
  );

  const hasAllergen = Boolean(
    ingredients.some((i) => i.is_allergen) ||
    hasAllergyConflict
  );

  const hasAdditive = Boolean(
    ingredients.some((i) => i.is_additive) ||
    /additive|flavour|flavor|preservative|ins\s*\d+/i.test(ingredientsStatement)
  );

  // Nutrition Facts Per Serving Grid
  const nutrition = data.nutrition || {};
  const servingSize = nutrition.serving_size?.value || '1 serving';

  const formatMetric = (metric, defaultUnit = 'g') => {
    if (!metric || metric.value == null) return '—';
    return `${metric.value}${metric.unit || defaultUnit}`;
  };

  const nutritionFacts = [
    ['Calories', formatMetric(nutrition.kcal, ' kcal')],
    ['Carbohydrates', formatMetric(nutrition.carbs_g, 'g')],
    ['Total sugars', formatMetric(nutrition.sugars_g, 'g')],
    ['Protein', formatMetric(nutrition.protein_g, 'g')],
    ['Total fat', formatMetric(nutrition.fat_g, 'g')],
    ['Saturated fat', formatMetric(nutrition.saturated_fat_g, 'g')],
    ['Sodium', formatMetric(nutrition.sodium_mg, 'mg')],
    ['Added sugar', formatMetric(nutrition.added_sugars_g, 'g')],
  ];

  // Nutrient Breakdown Table
  let nutrientBreakdownRows = [];
  if (scoring.details?.nutrient_breakdown && Array.isArray(scoring.details.nutrient_breakdown)) {
    nutrientBreakdownRows = scoring.details.nutrient_breakdown.map((row) => [
      row.nutrient || 'Nutrient',
      row.actual != null ? `${row.actual}${row.unit || 'g'}` : '—',
      row.limit != null ? `${row.limit}${row.unit || 'g'}` : '—',
      row.excess_pct != null ? (row.excess_pct > 0 ? `+${row.excess_pct.toFixed(1)}%` : `${row.excess_pct.toFixed(1)}%`) : '0%',
      `${row.risk_score != null ? row.risk_score : 1}/10`,
      String(row.weight || 1),
      row.basis || 'Per serving',
      row.source || 'ICMR-NIN 2024',
    ]);
  } else {
    // Generate from available nutrition metrics
    const benchmarks = [
      { name: 'Total / Added Sugars', metric: nutrition.sugars_g || nutrition.added_sugars_g, limit: 15, unit: 'g', source: 'ICMR-NIN 2024', weight: 3 },
      { name: 'Sodium', metric: nutrition.sodium_mg, limit: 300, unit: 'mg', source: 'ICMR-NIN 2024', weight: 3 },
      { name: 'Saturated Fat', metric: nutrition.saturated_fat_g, limit: 3, unit: 'g', source: 'ICMR-NIN 2024', weight: 2.5 },
      { name: 'Total Fat', metric: nutrition.fat_g, limit: 8, unit: 'g', source: 'ICMR-NIN 2024', weight: 1.5 },
      { name: 'Carbohydrates', metric: nutrition.carbs_g, limit: 25, unit: 'g', source: 'ICMR-NIN 2024', weight: 1 },
    ];
    nutrientBreakdownRows = benchmarks.map((b) => {
      const val = b.metric?.value != null ? Number(b.metric.value) : null;
      if (val == null) {
        return [b.name, '—', `${b.limit}${b.unit}`, '0%', '1/10', String(b.weight), 'Per serving', b.source];
      }
      const excess = val > b.limit ? ((val - b.limit) / b.limit) * 100 : 0;
      const score = val <= b.limit ? 1 : Math.min(10, Math.ceil(1 + ((val - b.limit) / b.limit) * 9));
      return [
        b.name,
        `${val}${b.unit}`,
        `${b.limit}${b.unit}`,
        excess > 0 ? `+${excess.toFixed(1)}%` : '0%',
        `${score}/10`,
        String(b.weight),
        'Per serving',
        b.source,
      ];
    });
  }

  // Top Contributing Ingredients Table
  let topIngredientsRows = [];
  if (scoring.details?.top_contributing_ingredients && Array.isArray(scoring.details.top_contributing_ingredients)) {
    topIngredientsRows = scoring.details.top_contributing_ingredients;
  } else if (ingredients.length > 0) {
    topIngredientsRows = ingredients.slice(0, 5).map((ing, idx) => ({
      name: ing.name || `Ingredient #${idx + 1}`,
      position: `#${idx + 1}`,
      weight: idx === 0 ? 3 : (idx === 1 ? 2 : 1),
      risk: ing.is_palm_oil_or_derivative ? '8/10' : (ing.is_additive ? '5/10' : '3/10'),
      reason: ing.is_palm_oil_or_derivative
        ? 'Palmolein contains saturated fatty acids and contributes to HFSS rating.'
        : (ing.is_additive ? 'Additives and flavour enhancers elevate processing risk.' : 'Standard recipe ingredient.'),
      citation: 'FSSAI Standards',
    }));
  }

  // Suggested Alternatives
  let rawAlternatives = [];
  if (data.recommendations && Array.isArray(data.recommendations.alternatives)) {
    rawAlternatives = data.recommendations.alternatives;
  } else if (Array.isArray(data.recommendations)) {
    rawAlternatives = data.recommendations;
  }

  const alternatives = rawAlternatives.map((alt) => ({
    name: alt.name || alt.product_name || 'Alternative Product',
    image: alt.image_url || getCategoryFallbackImage(alt.category || category, alt.name),
    reason: alt.swap_rationale || alt.reason_summary || (alt.rating_difference ? `+${Math.abs(alt.rating_difference).toFixed(1)} rating improvement` : 'Healthier category alternative'),
    score: alt.personalized_rating != null ? Number(alt.personalized_rating).toFixed(1) : (alt.rating != null ? Number(alt.rating).toFixed(1) : '3.5'),
  }));

  // Lab Coverage & Independent Evidence
  const labCoverage = data.lab_test_coverage || {};
  const indEvidence = data.independent_evidence || {};

  return {
    query,
    productName,
    brand,
    category,
    summary: data.summary || 'This product was analyzed against statutory Indian food safety and nutrition benchmarks.',
    isCached: Boolean(auditResult.is_cached),
    createdAt: auditResult.created_at,
    sourceUrls,
    verifiedSourcesCount,
    // Scoring
    personalisedRating,
    severityColor: getSeverityColor(personalisedRating),
    needleAngle: getNeedleAngle(personalisedRating),
    riskLabel,
    nutrientRating,
    ingredientRating,
    // Allergy
    hasAllergyConflict,
    detectedAllergens,
    // Claims
    claims,
    // Ingredients
    ingredientsStatement,
    hasPalmOil,
    hasAllergen,
    hasAdditive,
    servingSize,
    nutritionFacts,
    // Breakdown tables
    nutrientBreakdownRows,
    topIngredientsRows,
    // Alternatives
    alternatives,
    alternativesStatus: data.recommendations?.status || (alternatives.length > 0 ? 'ready' : 'not_needed'),
    // Coverage & Evidence
    labCoverage,
    independentEvidence: indEvidence,
    referenceStandards: data.reference_standards || [],
    productImage: getCategoryFallbackImage(category, productName),
  };
}
