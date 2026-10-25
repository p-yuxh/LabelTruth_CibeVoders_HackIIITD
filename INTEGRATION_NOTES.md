# LabelTruth Frontend Integration Notes (Phase 1 & Phase 2)

## Phase 1: Read-Only Audit

### Section A: Backend API Contract
The backend runs on FastAPI at port `8000` (default host `http://localhost:8000`). All endpoints are registered under both `/api` prefix (configured via `settings.API_V1_PREFIX = "/api"`) and without prefix. The frontend Vite proxy maps `/api` requests to `http://localhost:8000`.

| Method | Route | Auth | Request Payload | Response Body / Status | Error Codes | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/audit` | Optional (Guest/User) | `AuditRequest` JSON: `query` (str, min len 2), `force_refresh` (bool), `conditions` (list[str]), `user_allergens` (list[str]), `avoid_ingredients` (list[str]), `dietary_pattern` (str), `nutrition_goals` (list[str]) | `AuditResponse`: `query`, `is_cached`, `evidence_log_id`, `created_at`, `source_urls`, `data` (`ProductAuditData`), `tinyfish_agent_raw` | 400, 422, 500 | Core product audit endpoint; orchestrates scraping, claim auditing, scoring, and recommendation lookup. |
| `POST` | `/api/detect-image` | Optional | `multipart/form-data`: `file` (UploadFile) | `{ detected_product: str, brand: str, confidence: float }` | 400, 422, 500 | Image product OCR recognition. |
| `POST` | `/api/audit-image` | Optional | `multipart/form-data`: `file` (UploadFile), `force_refresh` (bool) | `AuditResponse` | 400, 422, 500 | Combines image OCR and audit pipeline. |
| `GET` | `/api/evidence-logs` | Optional | Query params: `limit` (int, default 30), `offset` (int, default 0) | `List[EvidenceLogItem]`: `id`, `query`, `product_name`, `brand`, `category`, `is_cached`, `created_at`, `source_urls`, `product_data` | 500 | Evidence log registry for past audits ("Search history"). |
| `GET` | `/api/evidence-logs/{log_id}` | Optional | Path param: `log_id` (int) | `EvidenceLogItem` | 404, 500 | Fetches a specific past audit by ID. |
| `POST` | `/api/score-personal` | Optional | `PersonalizeRequest`: `product_data` (dict), `conditions` (list[str]), `user_allergens` (list[str]), `avoid_ingredients` (list[str]), `dietary_pattern` (str), `nutrition_goals` (list[str]) | Dict: `personalized_rating`, `risk_band`, `rating_label`, `nutrient_score`, `ingredient_score`, `subscores`, `details` (nutrient & ingredient breakdown), `allergy_alert` | 400, 422, 500 | Dynamic on-demand recalculation of personalized score when user preferences update. |
| `POST` | `/api/products/{id}/alternatives` | Optional | Path: `id` (int/str), Body: `AlternativesRequest` (`conditions`, `user_allergens`, `product_data`) | `AlternativesResponse`: `product_id`, `job_id`, `status` ("ready" \| "pending" \| "not_needed"), `alternatives` | 400, 422, 500 | Triggers better alternatives lookup or returns immediate cached pool. |
| `GET` | `/api/alternatives/jobs/{job_id}` | Optional | Path: `job_id` (str) | `AlternativesResponse`: `status` ("ready" \| "in_progress" \| "failed"), `alternatives` | 404, 500 | Polling endpoint for background live discovery top-up. |
| `POST` | `/api/recommendations` | Optional | Recommendation payload (`product_name`, `category`, `conditions`, `user_allergens`) | List of recommended alternative items | 400, 500 | Legacy alias for candidate alternatives. |
| `GET` | `/api/reference-standards` | Optional | Query param: `share_of_daily` (float, default 0.15) | List of standards: `{ code, title, authority, benchmark_value, unit, scope, citation }` | 500 | ICMR-NIN, FSSAI, and WHO guidelines for nutrient limits & claim rules. |
| `GET` | `/api/independent-evidence` | Optional | Query: `query`, `product_name`, `brand`, `category` | Dict: `section_1` (batch test reports), `section_2` (regulatory actions/recalls), `reported_not_verified` | 500 | Verified lab report data from Consumer Voice & FSSAI. |
| `GET` | `/api/diagnostics/evidence-links` | Optional | None | List of verified domain links and HTTP statuses | 500 | Reachability diagnostic for lab reports. |
| `GET` | `/api/health` | Optional | None | `{ status: "ok", service: "labeltruth-api", version: "1.0.0" }` | 500 | Service heartbeat. |
| `GET` | `/api/profile-options` | Optional | None | `{ sections: [...] }` defining 5 personalization sections (conditions, allergies, goals, ingredients to avoid, patterns) | 500 | Master chip options configuration. |
| `POST` | `/api/auth/signup` | Public | `SignUpRequest`: `full_name`, `email`, `password` (min 8), `terms_agreed: true`, `age_confirmed: true` | `{ token: str, user: UserOut, profile: ProfileOut }` | 400, 422 | User registration. |
| `POST` | `/api/auth/login` | Public | `LoginRequest`: `email`, `password` | `{ token: str, user: UserOut, profile: ProfileOut }` | 401, 422 | User login; issues Bearer token. |
| `GET` | `/api/auth/me` | Bearer Token | Header: `Authorization: Bearer <token>` | `{ user: UserOut, profile: ProfileOut }` | 401 | Validate session on startup / profile hydration. |
| `PUT` | `/api/auth/profile` | Bearer Token | Header: `Authorization: Bearer <token>`, Body: `EditProfileRequest` (`full_name`, `email`) | `{ user: UserOut }` | 400, 401 | Updates user account details. |
| `POST` | `/api/auth/verify-email` | Optional | Token payload | `{ message: str, is_verified: bool }` | 400 | Email verification. |
| `POST` | `/api/auth/forgot-password` | Public | `ForgotPasswordRequest`: `email` | `{ message: str }` | 422 | Trigger password recovery link. |
| `POST` | `/api/auth/reset-password` | Public | `ResetPasswordRequest`: `email`, `reset_token`, `new_password` | `{ message: str }` | 400, 422 | Complete password reset. |
| `POST` | `/api/profile/save` | Optional Bearer | Header: optional Bearer token, Body: `ProfileSaveRequest` (`dietary_conditions`, `allergies`, `nutrition_goals`, `avoid_ingredients`, `dietary_pattern`, `health_data_consent`, `consent_version`, `path_taken`) | `{ status: "success", profile: ProfileOut }` | 400, 422 | Saves user personalization (persisted to DB if logged in, returned for session if guest). Enforces consent gate. |
| `GET` | `/api/auth/export-data` | Bearer Token | Header: `Authorization: Bearer <token>` | JSON data export of user profile and history | 401 | GDPR/DPDP data portability. |
| `DELETE` | `/api/auth/account` | Bearer Token | Header: `Authorization: Bearer <token>`, Body: `DeleteAccountRequest` (`password`) | `{ status: "deleted" }` | 401, 403 | Account erasure. |
| `GET` | `/api/saved-comparisons` | Bearer Token | Header: `Authorization: Bearer <token>` | List of saved comparisons | 401 | Get user's saved comparison queries. |
| `POST` | `/api/saved-comparisons` | Bearer Token | Header: `Authorization: Bearer <token>`, Body: `SavedComparisonCreate` (`query`, `product_name`, `product_id`) | Saved comparison record | 401 | Save a comparison. |
| `DELETE` | `/api/saved-comparisons/{id}` | Bearer Token | Header: `Authorization: Bearer <token>`, Path: `id` | `{ status: "deleted" }` | 401, 404 | Delete a saved comparison. |

---

### Section B: Existing Frontend Audit & Regression Checklist
- **Stack**: React 18 (`^18.3.1`), Vite 5 (`^5.2.0`), Lucide React (`^0.359.0`), Plain CSS (`src/index.css`), Node native test runner (`node --test tests/*.test.js`).
- **State Management**:
  - `AuthContext.jsx`: handles `user`, `token`, `profile`, `profileOptions`, `login()`, `signup()`, `logout()`, `saveUserProfile()`, and modal visibility states (`authModalOpen`, `personalizeModalOpen`, `accountModalOpen`, `savedModalOpen`, `legalModalOpen`).
  - `App.jsx`: handles `loading`, `loadingStep`, `error`, `auditResult`, `evidenceModalOpen`, `handleSearch()`, `handleSelectCachedLog()`, `handleProfileSaved()`.
- **Validation**:
  - Signup enforces `terms_agreed: true`, `age_confirmed: true`, and password min length 8 with password strength calculation.
  - Path B personalization enforces a dedicated health consent notice before saving clinical conditions and allergens.
  - Query search requires at least 2 characters.
- **Regression Checklist (User Flows)**:
  1. **Text Query Audit**: Typing a product name (e.g., "Maggi 2-Minute Noodles", "Yoga Bar Dark Chocolate Oats") and pressing Audit/Search sends `POST /api/audit` and displays the audit dossier.
  2. **Live Refresh Toggle**: Checking "Force fresh verification from live sources" passes `force_refresh: true` to `/api/audit`.
  3. **Suggestion Quick Search**: Clicking suggestions (Maggi, Bournvita, Lays, Amul Butter, etc.) triggers immediate audit.
  4. **Loading Feedback**: Step-by-step progress messages during audit execution.
  5. **Empty and Error States**: Clean message when no query entered or when server returns an error.
  6. **Cache Status Display**: Clear indication if result was served from cache or scraped live, plus source URL links.
  7. **Personalised Rating Display**: Rating score (1–10 scale), needle gauge or progress bar, risk band label (Good fit, Moderate, Poor, Very poor), and subscores (Nutrient rating, Ingredient rating).
  8. **Allergy Conflict Alert**: High-visibility banner when product contains user-declared allergens.
  9. **Claims Verification**: List of front-of-pack claims with 4 distinct verdicts (`VERIFIED`, `MISLEADING`, `CONTRADICTED`, `NO EVIDENCE`), evidence rationale, and citation links.
  10. **Ingredient Statement & Palm Oil Detection**: Highlighting of palm oil/palmolein, allergens, and food additives.
  11. **Nutrition Breakdown Table**: Per-serving nutrient values, reference limits, excess percentages, risk scores, and citations.
  12. **Top Contributing Ingredients Table**: Ingredients ranked by risk contribution with positions and citations.
  13. **Independent Evidence (Lab Reports)**: Section 1 batch-tested reports with batch disclaimers, Section 2 regulatory actions, and collapsible unverified reports.
  14. **Better Alternatives ("Smarter Swaps")**: Asynchronous top-up and display of healthier alternatives with rating difference and swap rationale.
  15. **Statutory Standards Knowledge Base**: FSSAI & ICMR-NIN reference benchmarks viewer.
  16. **Audit History Registry**: Browse and re-open past audited products from `/api/evidence-logs`.
  17. **Authentication (Log In / Sign Up / Forgot Password / Session)**: Real JWT token lifecycle, auto-hydration on page load, logout reverting to guest session.
  18. **Two-Path Personalization Flow**:
      - Path A: Quick selection of basic preferences without storing sensitive health data.
      - Path B: Complete 5-section profile with explicit health data consent gate.
      - Dynamic recalculation (`/api/score-personal`) of existing audit result upon profile save.
  19. **Account Management & Data Export**: View profile, edit details, download data JSON, delete account.
  20. **Saved Comparisons**: Save product comparisons to account and retrieve/delete them.
  21. **Legal Modals**: View Terms of Service and Privacy Policy.

---

### Section C: `figma/` Frontend Audit
- **Framework & Bundler**: React 19 (`^19.0.0`), Vite 8 (`^8.0.5`), `@tailwindcss/vite` + `tailwindcss` (`^4.0.0`), TypeScript (`^5.7.0`).
- **Styling**: Google Font `Manrope`, CSS variables (`--green: #4f9c22`, `--lime: #b9e56d`, `--pale: #eaf6df`, `--ink: #132015`), `.audit-page` responsive layout, CSS needle rotation for rating gauge, smooth scroll, and clean card styling in `figma/src/index.css` (530 lines).
- **Screens & Structure**:
  - **Landing View**: Navigation header, Hero search with dynamic scroll-scaling animation, verified product pills with image thumbnails, "From the Aisle" photo gallery, "The Reality" cards (3 cards with custom SVG icons), "The Difference" values, "Simple by Design - How It Works" 3-step section with lifestyle visual, Testimonials (3 quotes), "Compare Beyond the Label" category filter tabs with side-by-side comparison cards (`ComparisonCard`), FAQs accordion, "About Us", and multi-column Footer.
  - **Audit View (`AuditPage`)**: Dedicated audit view triggered when a product is audited. Includes brand home button, search history button, live search input with suggestions, live verification badge, standalone allergy alert strip, Personalised Rating gauge with needle angle, Claims verification accordion with 4 verdicts, Ingredients statement with Palm oil / Allergen / Additive tags, Independent coverage card, Technical risk report cards (FSSAI/ICMR finding + consumer-use note), Suggested alternatives card ("Smarter swaps"), Collapsible nutrient breakdown table, Collapsible ingredients table, Analysed product summary card, Audit evidence & source traceability, Advisories, and Statutory standards.
  - **Auth Modal**: Two-column modal with brand artwork on left, tabbed Log in / Sign up forms on right, Terms & Privacy checkbox, and quick access buttons for Path A ("Just a concerned consumer") and Path B ("I need more personalisation").
  - **Personalization Sub-view**: Multi-section preference chip selector with Basic vs Complete mode toggling.
  - **Mock Data**:
    - Hardcoded comparison items in `comparisons` array using assets in `figma/public/products/comparison/`.
    - Hardcoded audit view displaying Maggi sample values (Rating 8.26, needle angle, 4 static claims, 5 static nutrients, static alternatives).
    - Hardcoded FAQ questions, testimonials, and static formulas tooltip.

---

### Section D: Comprehensive Mapping Table

| Figma Screen / Component | Existing Frontend Equivalent | Backend Endpoint(s) | Status | Action Needed |
| :--- | :--- | :--- | :--- | :--- |
| **Landing Header** (`header`) | `Header.jsx` | N/A (State / AuthContext) | Direct Match | Render Figma branding, navigation anchor links, and auth state ("Log in" vs User Avatar/Menu). |
| **Hero Search Bar** (`.hero .search`) | `SearchSection.jsx` | `POST /api/audit` | Needs Adapter | Wire real text input, submit trigger, suggestion pills, and force-refresh option to trigger `handleSearch()`. |
| **Landing Comparisons** (`.comparison-card`) | `SavedComparisonsModal.jsx` / Mock | `GET /saved-comparisons` | Needs Adapter | Retain Figma interactive category tabs & curated matchups; support saving comparisons to backend. |
| **Landing FAQs / About / Values / How** | (Static landing copy) | N/A | Direct Match | Render directly from Figma JSX/CSS. |
| **Audit View Container** (`AuditPage`) | `App.jsx` + `ProductCard.jsx` | `POST /api/audit` | Direct Match | Activate when `auditResult` is populated. "LT LabelTruth" brand button returns to Landing; "Search history" opens `EvidenceModal`. |
| **Live Verification Strip** (`.live-strip`) | `CacheStatusBanner.jsx` | `is_cached`, `source_urls` | Needs Adapter | Map real source count (`source_urls.length`) and live/cached status dynamically. |
| **Allergy Strip** (`.allergy-strip`) | `ProductCard.jsx` (Allergy alert) | `personalized_scoring.allergy_alert` | Direct Match | Map `has_conflict`, detected allergens, and user preferences dynamically. |
| **Personalised Rating Gauge** (`.score-panel`) | `PersonalizedRatingBar.jsx` | `personalized_scoring` | Needs Adapter | Calculate needle rotation `(-180 + (rating/10)*180)deg`, map severity color, display dynamic subscores (`nutrient_rating`, `ingredient_rating`). |
| **Claims Verification Accordion** (`.claims-card`) | `ProductCard.jsx` + `ClaimVerdictTag.jsx` | `front_pack_claims` | Direct Match | Map dynamic claims list: verdict badge (`VERIFIED`, `MISLEADING`, `CONTRADICTED`, `NO EVIDENCE`), verdict reason, and citation source URL. |
| **Ingredients Statement** (`.ingredients-card`) | `ProductCard.jsx` (`ingredients`, `oil_listed`) | `ingredients`, `oil_listed` | Direct Match | Render real ingredient text; conditionally show `Palm oil`, `Allergen`, and `Additive` badges based on actual audit flags. |
| **Coverage Card** (`.coverage-card`) | `ProductCard.jsx` (`lab_test_coverage`) | `lab_test_coverage`, `independent_evidence` | Needs Adapter | Show real lab test coverage summary & anchor link to `#sources`. |
| **Technical Risk Report Cards** (`.technical-report`) | `ProductCard.jsx` (Statutory limits) | `reference_standards`, `personalized_scoring` | Needs Adapter | Populate dynamic FSSAI & ICMR-NIN limit finding and consumer-use frequency note from real audit metrics. |
| **Alternatives Card** (`.alternatives-card`) | `ProductCard.jsx` (`recommendations`) | `POST /products/{id}/alternatives`, `GET /alternatives/jobs/{id}` | Needs Adapter | Bind real candidate alternatives; show thumbnail, name, swap rationale, and rating score. |
| **Nutrient Breakdown Table** (`#nutrients`) | `ProductCard.jsx` (`nutrition`, `details.nutrient_breakdown`) | `nutrition` | Direct Match | Map real table: Nutrient name, actual value + unit, limit, excess percentage, risk score (1-10), weight, basis, source citation. |
| **Top Contributing Ingredients Table** (`.ingredient-table`) | `ProductCard.jsx` (`details.top_contributing_ingredients`) | `ingredients`, `personalized_scoring` | Direct Match | Map real ingredients table: name, position, weight, risk score, reason/finding, citation. |
| **Analysed Product Summary** (`.product-summary`) | `ProductCard.jsx` | `ProductAuditData` | Direct Match | Map product name, brand, category, palm oil alert, executive summary, and 8-grid nutrition facts per serving. |
| **Audit Evidence & Source Traceability** (`#sources`) | `IndependentEvidenceSection.jsx` | `source_urls`, `independent_evidence` | Needs Adapter | Display Section 1 batch-tested reports (with mandatory batch disclaimer), Section 2 regulatory actions, and collapsible unverified reports. |
| **Scientific & Compliance Advisories** (`.advisory-list`) | `ReferenceStandardsSection.jsx` | `reference_standards` | Needs Adapter | Render dynamically generated advisory items based on nutrients exceeding statutory limits. |
| **Statutory Standards Knowledge Base** (`#standards`) | `ReferenceStandardsSection.jsx` | `GET /reference-standards` | Needs Adapter | Render real statutory standards categories: FSSAI claim rules, ICMR-NIN & WHO dietary limits, and diabetes benchmarks. |
| **Auth Modal** (`.auth-page`) | `AuthModal.jsx` | `POST /auth/login`, `POST /auth/signup` | Direct Match | Wire Figma 2-column modal to real authentication endpoints with full validation (terms, age 18+, password strength, error feedback). |
| **Personalization Selector** (`.personalization`) | `PersonalizeModal.jsx` | `GET /profile-options`, `POST /profile/save` | Direct Match | Support Path A (basic) and Path B (complete), render dynamic chip options from `profile_options.json`, enforce health consent gate for Path B, and trigger live re-scoring. |
| **Search History Modal** | `EvidenceModal.jsx` | `GET /evidence-logs` | Needs Figma Design | Style `EvidenceModal` using Figma design system tokens (Manrope typography, card styling, green accents) and trigger it from "Search history" button. |
| **User Account & Legal Modals** | `AccountModal.jsx`, `LegalModal.jsx` | `GET/PUT /auth/profile`, `DELETE /auth/account`, `GET /auth/export-data` | Needs Figma Design | Style using Figma design system; accessible from header account menu and footer links. |

---

## Phase 2: Architecture & Integration Plan

### Architecture Decision: Keep `frontend/` as Single App Shell
We will retain the existing `frontend/` directory as the sole frontend application for the project:
1. **Stack Stability**: `frontend/` has a fully configured Vite build pipeline, React 18, and 35 passing tests in `frontend/tests/` verifying WCAG contrast, rating bands, claim verdict mappings, and modal compliance.
2. **Zero Backend Changes**: Dev-server proxy in `frontend/vite.config.js` routes all `/api` calls seamlessly to `http://localhost:8000` without requiring backend CORS or port alterations.
3. **Figma UI Integration**:
   - Copy all Figma images from `figma/public/products/` into `frontend/public/products/`.
   - Port all CSS variables, typography (`Manrope`), and component classes from `figma/src/index.css` into `frontend/src/index.css`, preserving existing `--verdict-*` and `--rating-*` variables required by tests.
   - Implement presentational components matching Figma JSX structure 1:1, wired to real services (`api.js`, `AuthContext.jsx`).
   - Create an adapter module `frontend/src/utils/figmaAdapter.js` to normalize backend `ProductAuditData` into the exact props required by the Figma audit and landing components.
4. **Graceful Handling of States**:
   - Loading states styled with Figma's palette and typography.
   - Empty search states and error callouts styled to match Figma design tokens.
   - All interactive buttons wired to functional handlers (no dead buttons).

### Open Questions for User Approval
1. **Landing Page vs Audit View Navigation**: In Figma, entering a search query transitions from the Landing Page into the Audit View (`AuditPage`), and clicking the "LT LabelTruth" logo returns to the Landing Page. We plan to retain this exact behavior.
2. **Search History Access**: In Figma, the Audit View header includes a "Search history" button. We will wire this button to open the existing Evidence Log Modal (`EvidenceModal.jsx`), restyled in Figma tokens.
3. **Alternative Product Images**: When backend returns live alternatives that do not have custom photography, we will display a category-specific fallback thumbnail from the Figma product assets.

---
**STOPPING FOR USER APPROVAL**: No code files will be edited until explicit user approval is granted.

