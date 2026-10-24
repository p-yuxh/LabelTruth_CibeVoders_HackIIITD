import React from 'react';
import { getRatingStyle } from '../utils/themeHelpers';

/**
 * Thin horizontal scale bar from 1 to 10 representing Personalised Rating.
 * Lower is better (1 = best fit / green, 10 = worst fit / red).
 * Includes accessible aria attributes and band marker.
 */
export default function PersonalizedRatingBar({ rating }) {
  if (rating === null || rating === undefined) return null;

  const num = typeof rating === 'number' ? rating : parseFloat(rating);
  if (isNaN(num)) return null;

  const style = getRatingStyle(num);
  // Clamped percentage: 1 maps to 0%, 10 maps to 100%
  const clamped = Math.min(Math.max(num, 1), 10);
  const positionPct = ((clamped - 1) / 9) * 100;

  return (
    <div
      className="rating-bar-container"
      role="meter"
      aria-label="Personalised nutritional rating score bar"
      aria-valuenow={num}
      aria-valuemin={1}
      aria-valuemax={10}
      aria-valuetext={`${num} out of 10, ${style.label}`}
    >
      <div className="rating-bar-header">
        <span className="rating-bar-legend">Scale: 1 = best, 10 = worst</span>
        <span
          className="rating-bar-indicator-badge"
          style={{
            backgroundColor: style.bg,
            color: style.text,
          }}
        >
          {num.toFixed(1)} / 10 {style.label}
        </span>
      </div>

      <div className="rating-bar-track">
        <div
          className="rating-bar-marker"
          style={{
            left: `${positionPct}%`,
            backgroundColor: style.bg,
            borderColor: style.bg,
          }}
          title={`Rating: ${num} (${style.label})`}
        />
      </div>

      <div className="rating-bar-ticks">
        <span>1 (Best)</span>
        <span>3.0</span>
        <span>5.0</span>
        <span>7.0</span>
        <span>10 (Worst)</span>
      </div>
    </div>
  );
}

