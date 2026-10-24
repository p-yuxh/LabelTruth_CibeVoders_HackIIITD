import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle } from 'lucide-react';
import { getVerdictStyle } from '../utils/themeHelpers';

const VERDICT_ICON_MAP = {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
};

/**
 * Standardized Claim Verdict Tag component.
 * Displays icon + uppercase label + background color according to the four clinical verdict categories.
 * Accessible with contrast >= 4.5:1 and discernible in greyscale.
 */
export default function ClaimVerdictTag({ verdict, className = '', style = {} }) {
  const verdictStyle = getVerdictStyle(verdict);
  const IconComponent = VERDICT_ICON_MAP[verdictStyle.icon] || HelpCircle;

  return (
    <span
      className={`verdict-tag ${className}`.trim()}
      style={{
        backgroundColor: verdictStyle.bg,
        color: verdictStyle.text,
        ...style,
      }}
      role="status"
      aria-label={`Claim verdict: ${verdictStyle.label}`}
    >
      <IconComponent size={13} aria-hidden="true" style={{ flexShrink: 0 }} />
      <span>{verdictStyle.label}</span>
    </span>
  );
}

