import ratingBandsConfig from '../config/rating_bands.json' with { type: 'json' };
import verdictThemesConfig from '../config/verdict_themes.json' with { type: 'json' };

/**
 * Maps a claim verdict string to its theme styling and Lucide icon.
 * Fallback for unknown, empty, or missing values is strictly 'NO EVIDENCE'.
 * Exactly four verdicts are supported: VERIFIED, MISLEADING, CONTRADICTED, NO EVIDENCE.
 *
 * @param {string|null|undefined} verdict
 * @returns {{ bg: string, text: string, icon: string, label: string }}
 */
export function getVerdictStyle(verdict) {
  if (!verdict || typeof verdict !== 'string') {
    return { ...verdictThemesConfig['NO EVIDENCE'] };
  }

  const clean = verdict.trim().toUpperCase().replace(/[-_]/g, ' ');

  if (clean.includes('CONTRADICTED')) {
    return { ...verdictThemesConfig['CONTRADICTED'] };
  }
  if (clean.includes('MISLEADING')) {
    return { ...verdictThemesConfig['MISLEADING'] };
  }
  if (clean.includes('VERIFIED')) {
    return { ...verdictThemesConfig['VERIFIED'] };
  }
  if (clean.includes('NO EVIDENCE') || clean.includes('UNVERIFIED') || clean.includes('NONE')) {
    return { ...verdictThemesConfig['NO EVIDENCE'] };
  }

  // Unknown or unrecognized falls back to NO EVIDENCE
  return { ...verdictThemesConfig['NO EVIDENCE'] };
}

/**
 * Maps a numerical Personalised Rating (1-10 scale, lower is better) to band styling.
 *
 * Scale boundaries:
 *  - r <= 3.0:        "Good fit"   (#14532d / var(--rating-good-bg))
 *  - 3.0 < r <= 5.0:  "Moderate"   (#f59e0b / var(--rating-moderate-bg))
 *  - 5.0 < r <= 7.0:  "Poor"       (#c2410c / var(--rating-poor-bg))
 *  - r > 7.0:         "Very poor"  (#b42318 / var(--rating-very-poor-bg))
 *  - None / missing:  "No data"    (#5f6675 / var(--rating-nodata-bg))
 *
 * @param {number|string|null|undefined} rating
 * @returns {{ bg: string, text: string, label: string }}
 */
export function getRatingStyle(rating) {
  if (rating === null || rating === undefined || rating === '') {
    return { ...ratingBandsConfig.no_data };
  }

  const num = typeof rating === 'number' ? rating : parseFloat(rating);
  if (isNaN(num)) {
    return { ...ratingBandsConfig.no_data };
  }

  const { bands, no_data } = ratingBandsConfig;

  for (const band of bands) {
    if (band.cutoff === null || band.cutoff === undefined) {
      // Catch-all upper band (e.g. r > 7.0)
      return {
        bg: band.bg,
        text: band.text,
        label: band.label,
      };
    }
    if (num <= band.cutoff) {
      return {
        bg: band.bg,
        text: band.text,
        label: band.label,
      };
    }
  }

  return { ...no_data };
}

export { ratingBandsConfig, verdictThemesConfig };

