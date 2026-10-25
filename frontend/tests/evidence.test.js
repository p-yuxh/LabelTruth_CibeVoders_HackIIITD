import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('Independent Evidence Frontend Architecture & Compliance', () => {
  const componentPath = path.join(__dirname, '../src/components/IndependentEvidenceSection.jsx');
  const componentCode = fs.readFileSync(componentPath, 'utf-8');

  test('Contains exact Section Heading: Independent lab & regulatory evidence', () => {
    assert.match(
      componentCode,
      /Independent lab &amp; regulatory evidence|Independent lab & regulatory evidence/i
    );
  });

  test('Absence of social media and community opinions panel or tags', () => {
    assert.doesNotMatch(
      componentCode,
      /Social media &amp; community opinions|Social media & community opinions/i
    );
    assert.doesNotMatch(componentCode, /social-item-card/i);
    assert.doesNotMatch(componentCode, /social-unverified-tag/i);
    assert.doesNotMatch(componentCode, /No public opinions collected/i);
  });

  test('Section 1 item displays mandatory batch disclaimer', () => {
    assert.match(
      componentCode,
      /Reported evidence for the tested batch, not proof of wrongdoing/i
    );
    assert.match(
      componentCode,
      /Results apply to the batch tested; the product may have changed since/i
    );
  });

  test('Includes collapsible Reported, not verified group with reason', () => {
    assert.match(componentCode, /Reported, not verified/i);
    assert.match(componentCode, /not_verified_reason/i);
  });

  test('Handles empty state: No matching lab report found for this product and category browse link', () => {
    assert.match(componentCode, /No matching lab report found for this product/i);
    assert.match(componentCode, /Browse Consumer Voice/i);
    assert.match(componentCode, /not evidence for this product/i);
  });
});


