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

  test('Contains exact Section 1 Heading: Independent lab & regulatory evidence', () => {
    assert.match(
      componentCode,
      /Independent lab &amp; regulatory evidence|Independent lab & regulatory evidence/i
    );
  });

  test('Contains exact Section 2 Heading: Social media & community opinions (unverified)', () => {
    assert.match(
      componentCode,
      /Social media &amp; community opinions \(unverified\)|Social media & community opinions \(unverified\)/i
    );
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

  test('Section 2 displays mandatory unverified opinion label', () => {
    assert.match(
      componentCode,
      /Unverified opinion\. Not used in verdicts, ratings or recommendations\./i
    );
  });

  test('Includes collapsible Reported, not verified group with reason', () => {
    assert.match(componentCode, /Reported, not verified/i);
    assert.match(componentCode, /not_verified_reason/i);
  });

  test('Handles empty states: No matching lab report found and No public opinions collected', () => {
    assert.match(componentCode, /No matching lab report found/i);
    assert.match(componentCode, /No public opinions collected/i);
  });
});

