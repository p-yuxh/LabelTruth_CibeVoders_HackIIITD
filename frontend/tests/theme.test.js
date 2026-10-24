import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { getVerdictStyle, getRatingStyle, ratingBandsConfig, verdictThemesConfig } from '../src/utils/themeHelpers.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('Claim Verdict Style Mapping (getVerdictStyle)', () => {
  test('VERIFIED verdict maps to dark green CheckCircle2', () => {
    const style = getVerdictStyle('VERIFIED');
    assert.equal(style.label, 'VERIFIED');
    assert.equal(style.icon, 'CheckCircle2');
    assert.equal(style.bg, 'var(--verdict-verified)');
    assert.equal(style.text, 'var(--verdict-text)');
  });

  test('MISLEADING verdict maps to orange AlertTriangle', () => {
    const style = getVerdictStyle('MISLEADING');
    assert.equal(style.label, 'MISLEADING');
    assert.equal(style.icon, 'AlertTriangle');
    assert.equal(style.bg, 'var(--verdict-misleading)');
    assert.equal(style.text, 'var(--verdict-text)');
  });

  test('CONTRADICTED verdict maps to red XCircle', () => {
    const style = getVerdictStyle('CONTRADICTED');
    assert.equal(style.label, 'CONTRADICTED');
    assert.equal(style.icon, 'XCircle');
    assert.equal(style.bg, 'var(--verdict-contradicted)');
    assert.equal(style.text, 'var(--verdict-text)');
  });

  test('NO EVIDENCE verdict maps to slate grey HelpCircle', () => {
    const style = getVerdictStyle('NO EVIDENCE');
    assert.equal(style.label, 'NO EVIDENCE');
    assert.equal(style.icon, 'HelpCircle');
    assert.equal(style.bg, 'var(--verdict-no-evidence)');
    assert.equal(style.text, 'var(--verdict-text)');
  });

  test('Case insensitivity and normalized formatting (e.g. lowercase, underscore)', () => {
    assert.equal(getVerdictStyle('verified').label, 'VERIFIED');
    assert.equal(getVerdictStyle('misleading').label, 'MISLEADING');
    assert.equal(getVerdictStyle('contradicted').label, 'CONTRADICTED');
    assert.equal(getVerdictStyle('no_evidence').label, 'NO EVIDENCE');
  });

  test('Unknown, missing, or null verdict strictly falls back to NO EVIDENCE (never invent 5th verdict)', () => {
    const unknownInputs = ['UNKNOWN', 'INVALID_CLAIM', 'UNCONFIRMED', '', null, undefined, 123, {}];
    for (const input of unknownInputs) {
      const fallback = getVerdictStyle(input);
      assert.equal(fallback.label, 'NO EVIDENCE', `Input ${JSON.stringify(input)} should fall back to NO EVIDENCE`);
      assert.equal(fallback.icon, 'HelpCircle');
      assert.equal(fallback.bg, 'var(--verdict-no-evidence)');
      assert.equal(fallback.text, 'var(--verdict-text)');
    }
  });
});

describe('Personalised Rating Style Mapping (getRatingStyle)', () => {
  test('r = 1.0 (r <= 3.0) maps to "Good fit"', () => {
    const res = getRatingStyle(1.0);
    assert.equal(res.label, 'Good fit');
    assert.equal(res.bg, 'var(--rating-good-bg)');
    assert.equal(res.text, 'var(--rating-good-text)');
  });

  test('r = 3.0 (exact upper boundary of Good fit) maps to "Good fit"', () => {
    const res = getRatingStyle(3.0);
    assert.equal(res.label, 'Good fit');
    assert.equal(res.bg, 'var(--rating-good-bg)');
    assert.equal(res.text, 'var(--rating-good-text)');
  });

  test('r = 3.01 (just above 3.0) maps to "Moderate"', () => {
    const res = getRatingStyle(3.01);
    assert.equal(res.label, 'Moderate');
    assert.equal(res.bg, 'var(--rating-moderate-bg)');
    assert.equal(res.text, 'var(--rating-moderate-text)');
  });

  test('r = 5.0 (exact upper boundary of Moderate) maps to "Moderate"', () => {
    const res = getRatingStyle(5.0);
    assert.equal(res.label, 'Moderate');
    assert.equal(res.bg, 'var(--rating-moderate-bg)');
    assert.equal(res.text, 'var(--rating-moderate-text)');
  });

  test('r = 5.01 (just above 5.0) maps to "Poor"', () => {
    const res = getRatingStyle(5.01);
    assert.equal(res.label, 'Poor');
    assert.equal(res.bg, 'var(--rating-poor-bg)');
    assert.equal(res.text, 'var(--rating-poor-text)');
  });

  test('r = 7.0 (exact upper boundary of Poor) maps to "Poor"', () => {
    const res = getRatingStyle(7.0);
    assert.equal(res.label, 'Poor');
    assert.equal(res.bg, 'var(--rating-poor-bg)');
    assert.equal(res.text, 'var(--rating-poor-text)');
  });

  test('r = 7.01 (just above 7.0) maps to "Very poor"', () => {
    const res = getRatingStyle(7.01);
    assert.equal(res.label, 'Very poor');
    assert.equal(res.bg, 'var(--rating-very-poor-bg)');
    assert.equal(res.text, 'var(--rating-very-poor-text)');
  });

  test('r = 9.26 (decimal in highest risk band) maps to "Very poor"', () => {
    const res = getRatingStyle(9.26);
    assert.equal(res.label, 'Very poor');
    assert.equal(res.bg, 'var(--rating-very-poor-bg)');
    assert.equal(res.text, 'var(--rating-very-poor-text)');
  });

  test('r = 10 (scale maximum) maps to "Very poor"', () => {
    const res = getRatingStyle(10);
    assert.equal(res.label, 'Very poor');
    assert.equal(res.bg, 'var(--rating-very-poor-bg)');
    assert.equal(res.text, 'var(--rating-very-poor-text)');
  });

  test('Missing rating (null, undefined, NaN) maps to "No data" and is NEVER green', () => {
    const missingInputs = [null, undefined, NaN, '', 'N/A'];
    for (const val of missingInputs) {
      const res = getRatingStyle(val);
      assert.equal(res.label, 'No data');
      assert.equal(res.bg, 'var(--rating-nodata-bg)');
      assert.notEqual(res.bg, 'var(--rating-good-bg)', 'Missing rating must never be green');
    }
  });

  test('String numerical inputs (e.g. "9.26") parse correctly', () => {
    const res = getRatingStyle('9.26');
    assert.equal(res.label, 'Very poor');
  });
});

describe('Accessibility & Contrast Verification (WCAG AA >= 4.5:1)', () => {
  // Relative luminance calculation per WCAG 2.1
  function getLuminance(hex) {
    const clean = hex.replace('#', '');
    const r = parseInt(clean.substring(0, 2), 16) / 255;
    const g = parseInt(clean.substring(2, 4), 16) / 255;
    const b = parseInt(clean.substring(4, 6), 16) / 255;
    const a = [r, g, b].map((v) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
    return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
  }

  function getContrast(hex1, hex2) {
    const l1 = getLuminance(hex1);
    const l2 = getLuminance(hex2);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
  }

  test('Claim verdict colours meet WCAG AA contrast ratio >= 4.5:1', () => {
    const colors = [
      { name: 'VERIFIED', bg: '#14532d', text: '#ffffff' },
      { name: 'MISLEADING', bg: '#b45309', text: '#ffffff' },
      { name: 'CONTRADICTED', bg: '#b42318', text: '#ffffff' },
      { name: 'NO EVIDENCE', bg: '#5f6675', text: '#ffffff' },
    ];

    for (const c of colors) {
      const ratio = getContrast(c.bg, c.text);
      assert.ok(
        ratio >= 4.5,
        `Verdict ${c.name} contrast ratio ${ratio.toFixed(2)} is less than 4.5:1 required by WCAG AA`
      );
    }
  });

  test('Rating band colours meet WCAG AA contrast ratio >= 4.5:1', () => {
    const colors = [
      { name: 'Good fit', bg: '#14532d', text: '#ffffff' },
      { name: 'Moderate (amber with dark text)', bg: '#f59e0b', text: '#111111' },
      { name: 'Poor', bg: '#c2410c', text: '#ffffff' },
      { name: 'Very poor', bg: '#b42318', text: '#ffffff' },
      { name: 'No data', bg: '#5f6675', text: '#ffffff' },
    ];

    for (const c of colors) {
      const ratio = getContrast(c.bg, c.text);
      assert.ok(
        ratio >= 4.5,
        `Rating band ${c.name} contrast ratio ${ratio.toFixed(2)} is less than 4.5:1 required by WCAG AA`
      );
    }
  });
});

describe('Single Source of Truth & No Hardcoded Hex in Components', () => {
  const componentsDir = path.resolve(__dirname, '../src/components');
  const verdictAndRatingHexes = [
    '#14532d',
    '#b45309',
    '#b42318',
    '#5f6675',
    '#f59e0b',
    '#c2410c',
  ];

  test('No verdict or rating component uses hardcoded verdict/rating hex colours', () => {
    const files = fs.readdirSync(componentsDir).filter((f) => f.endsWith('.jsx'));
    for (const file of files) {
      const filePath = path.join(componentsDir, file);
      const content = fs.readFileSync(filePath, 'utf-8');

      for (const hex of verdictAndRatingHexes) {
        assert.ok(
          !content.toLowerCase().includes(hex.toLowerCase()),
          `Found forbidden hardcoded verdict/rating hex ${hex} in ${file}. Colours must be referenced through theme CSS variables.`
        );
      }
    }
  });

  test('All required CSS variables are declared in :root in index.css', () => {
    const cssPath = path.resolve(__dirname, '../src/index.css');
    const cssContent = fs.readFileSync(cssPath, 'utf-8');

    const requiredVars = [
      '--verdict-verified',
      '--verdict-misleading',
      '--verdict-contradicted',
      '--verdict-no-evidence',
      '--verdict-text',
      '--rating-good-bg',
      '--rating-good-text',
      '--rating-moderate-bg',
      '--rating-moderate-text',
      '--rating-poor-bg',
      '--rating-poor-text',
      '--rating-very-poor-bg',
      '--rating-very-poor-text',
      '--rating-nodata-bg',
      '--rating-nodata-text',
    ];

    for (const varName of requiredVars) {
      assert.ok(
        cssContent.includes(varName),
        `Required CSS variable ${varName} missing from index.css`
      );
    }
  });
});

