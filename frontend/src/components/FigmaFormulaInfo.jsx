import React from 'react';

const formulaNotes = {
  1: {
    title: 'Nutrient rating',
    formula: '1 if actual ≤ limit; otherwise min(10, 1 + ceil(excess × 9)), where excess = (actual − limit) / limit.',
    why: 'Each step represents about 11% over the limit; double the limit reaches 10.',
    status: 'Design choice. The factor of 9 is tunable.',
  },
  2: {
    title: 'Per-serving limit',
    formula: 'Daily limit × serving share (15–20%).',
    why: 'Guidelines usually provide daily limits rather than per-product limits.',
    status: 'Assumption. The serving share is configurable.',
  },
  3: {
    title: 'Daily limits',
    formula: 'Sugar, salt and fat limits are drawn from ICMR-NIN, WHO and ADA guidance.',
    why: 'These benchmarks anchor the nutrient assessment.',
    status: 'Sourced; figures should be checked against the original documents.',
  },
  4: {
    title: 'Condition profiles',
    formula: 'Use the strictest limit and highest weight across selected conditions.',
    why: 'Provides a cautious result when several conditions apply.',
    status: 'Design choice. Condition weights require dietitian review.',
  },
  5: {
    title: 'Nutrient score',
    formula: 'Base = Σ(w·r)/Σw; final = max(base, 0.7·worst + 0.3·base).',
    why: 'Prevents one high-risk nutrient from being hidden by an average.',
    status: 'Design choice. The 0.7/0.3 weighting is not from a guideline.',
  },
  6: {
    title: 'Ingredient score',
    formula: 'Use position weights (first = n, last = 1), or printed percentages, with the same worst-item override.',
    why: 'Ingredients are generally listed in descending quantity.',
    status: 'Design choice. The weighting values are configurable.',
  },
  7: {
    title: 'Ingredient risk & uncertainty',
    formula: 'Risk values use 1–10; confidence scaling is resolved 1.0, alternatives 0.6, possible 0.4.',
    why: 'Reflects both ingredient concern and identification certainty.',
    status: 'Assumption. Each risk value needs a cited rationale.',
  },
  8: {
    title: 'Product rating',
    formula: '0.6 × nutrient score + 0.4 × ingredient score.',
    why: 'Measured nutrient limits receive slightly more weight.',
    status: 'Design choice.',
  },
  9: {
    title: 'Claim thresholds',
    formula: 'Example: “sugar free” requires ≤ 0.5 g sugar per 100 g.',
    why: 'Used to verify regulated package claims.',
    status: 'Sourced from and checked against FSSAI documentation.',
  },
  10: {
    title: 'Lab gap',
    formula: '(lab result − label value) / label value × 100, with a tolerance.',
    why: 'Shows how far an independent lab result differs from the label.',
    status: 'Standard calculation; the tolerance is currently a placeholder.',
  },
  11: {
    title: 'Age & colour bands',
    formula: 'Report age bands: 2 and 5 years. Rating colour boundaries: 3, 5 and 7.',
    why: 'Makes older evidence and higher ratings easier to identify.',
    status: 'Design choice.',
  },
  12: {
    title: 'Allergy check',
    formula: 'Rule matching against ingredient names and known aliases.',
    why: 'Flags selected allergens without calculating a numeric score.',
    status: 'Rule-based. Accuracy depends on alias-list completeness.',
  },
};

export default function FigmaFormulaInfo({ ids = [] }) {
  if (!ids || ids.length === 0) return null;

  return (
    <span
      className="formula-info"
      aria-label={`Methodology information: ${ids.map((id) => formulaNotes[id]?.title).filter(Boolean).join(', ')}`}
    >
      <span className="formula-icon" aria-hidden="true">i</span>
      <span className="formula-tooltip" role="tooltip">
        {ids.map((id) => {
          const note = formulaNotes[id];
          if (!note) return null;
          return (
            <span className="formula-note" key={id}>
              <b>{note.title}</b>
              <span><strong>Formula</strong>{note.formula}</span>
              <span><strong>Why</strong>{note.why}</span>
              <span><strong>Status</strong>{note.status}</span>
            </span>
          );
        })}
      </span>
    </span>
  );
}

