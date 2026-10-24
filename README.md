# LabelTruth

LabelTruth is an evidence-based packaged food claims auditor and nutritional evaluation system. It cross-references packaging claims against actual nutrition facts and ingredient statements using statutory standards from FSSAI, ICMR-NIN 2024, ADA 2026, and WHO guidelines.

---

## Core System Architecture

### 1. Personalised Rating (Scale: 1 – 10, Lower is Better)
The Personalised Rating evaluates a product's nutritional suitability strictly based on:
- **Nutrient excess**: Nutrient values compared against the selected health condition limits and weights.
  - Formula: \( r_k = 1 \) if actual \(\le\) limit, else \(\min(10, 1 + \lceil \frac{\text{actual} - \text{limit}}{\text{limit}} \times 9 \rceil)\).
  - Nutrient Rating: Weighted average with a clinical worst-case safety floor: \(\max(\text{base}, 0.7 \times \max(r_k) + 0.3 \times \text{base})\).
- **Ingredient risk**: Position-weighted risk scores (first = \( n \), last = 1) from `ingredient_risks.json`, incorporating condition-specific risk values.
  - Flagged override: \(\max(\text{base}, 0.7 \times \text{worst\_flagged} + 0.3 \times \text{base})\).
- **Product Rating**: \( 0.6 \times \text{Nutrient Rating} + 0.4 \times \text{Ingredient Rating} \).
- **Multiple Conditions**: Strictest (lowest) limit and highest weight per nutrient across active conditions.
- **Strict Independence**: Nothing else alters the rating. No former preference inputs, claim verdicts, or match scores modify the Personalised Rating.

### 2. Allergy Check
A separate hard safety rule:
- **Status options**: `NOT SAFE FOR YOU`, `CANNOT CONFIRM`, or `NONE FOUND`.
- **Safety Suppression**: If `NOT SAFE FOR YOU`, nutritional ratings are suppressed to protect the user from consumption.

### 3. Claim Verification
Objective audit against laboratory and statutory standards:
- Allowed verdicts: `VERIFIED`, `MISLEADING`, `CONTRADICTED`, `NO EVIDENCE`.
- Provided strictly as informative evidence with source links; never alters the Personalised Rating.

### 4. Category Recommendations
- Selects alternative products in the same category.
- Excludes products with allergy status `NOT SAFE FOR YOU`.
- Ranks candidates by Personalised Rating (lowest first).
- Breaks ties by fewer `CONTRADICTED` or `MISLEADING` claims.
- States recommendation reasons in plain words strictly using nutrient and ingredient findings.

---

## Repository Structure

```
LabelTruth/
├── backend/
│   ├── app/
│   │   ├── api/routes.py              # FastAPI endpoints (/audit, /score-personal, /recommendations)
│   │   ├── config_data/
│   │   │   ├── ingredient_risks.json  # Statutory ingredient risk rules & condition risks
│   │   │   └── nutrition_profiles.json # Clinical & statutory condition limits
│   │   ├── models/evidence_log.py     # PostgreSQL EvidenceLog ORM model
│   │   ├── schemas/product.py         # Pydantic schemas
│   │   ├── services/
│   │   │   ├── claims_auditor.py      # Claims auditing against standards
│   │   │   ├── image_detector.py      # OCR & packaging detection
│   │   │   ├── orchestrator.py        # Pipeline orchestrator
│   │   │   ├── personalized_scoring.py# Personalised rating & recommendation engine
│   │   │   ├── reference_standards.py # FSSAI, ICMR-NIN & ADA benchmarks
│   │   │   └── tinyfish_scraper.py    # Retailer scraper service
│   │   └── main.py                    # FastAPI application
│   └── tests/
│       └── test_pipeline.py           # Verification & specification tests
└── frontend/
    └── src/
        ├── components/
        │   ├── Header.jsx
        │   ├── PersonalizedScoringSection.jsx
        │   ├── ProductCard.jsx
        │   ├── ReferenceStandardsSection.jsx
        │   └── SearchSection.jsx
        ├── services/api.js
        └── App.jsx
```

---

## Running the Application

### Backend
```bash
cd backend
python -m uvicorn app.main:app --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Running Tests
```bash
python -m pytest backend/tests/test_pipeline.py -k "not async" -v
```

