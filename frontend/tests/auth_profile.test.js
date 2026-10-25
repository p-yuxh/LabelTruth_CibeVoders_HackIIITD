import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('Auth & Personalisation Frontend Architecture & Reference Specs', () => {
  const authModalPath = path.join(__dirname, '../src/components/AuthModal.jsx');
  const authModalCode = fs.readFileSync(authModalPath, 'utf-8');

  const personalizeModalPath = path.join(__dirname, '../src/components/PersonalizeModal.jsx');
  const personalizeModalCode = fs.readFileSync(personalizeModalPath, 'utf-8');

  const optionsPath = path.join(__dirname, '../src/config/profile_options.json');
  const optionsData = JSON.parse(fs.readFileSync(optionsPath, 'utf-8'));

  test('AuthModal contains reference branding lockup, eyebrow, headline and subtext', () => {
    assert.match(authModalCode, /KNOW WHAT'S INSIDE/i);
    assert.match(authModalCode, /Better choices start with the truth\./i);
    assert.match(
      authModalCode,
      /Save comparisons, revisit evidence, and make every shopping decision with confidence\./i
    );
    assert.match(authModalCode, /auth-illustrated-svg/i);
  });

  test('AuthModal includes Log in | Sign up tab switcher and close button', () => {
    assert.match(authModalCode, /Log in/i);
    assert.match(authModalCode, /Sign up/i);
    assert.match(authModalCode, /auth-close-btn/i);
  });

  test('Sign up requires Terms and 18+ checkboxes, password strength meter (min 8 chars)', () => {
    assert.match(authModalCode, /I agree to the[\s\S]*Terms[\s\S]*Privacy Policy/i);
    assert.match(authModalCode, /I am 18 or older/i);
    assert.match(authModalCode, /Password \(min 8 characters\)/i);
    assert.match(authModalCode, /auth-strength-bars/i);
  });

  test('Log in has exact placeholder "Your password", "Forgot password?", and generic failure handling', () => {
    assert.match(authModalCode, /placeholder="Your password"/i);
    assert.match(authModalCode, /Forgot password\?/i);
    assert.match(authModalCode, /role="alert"/i);
    assert.match(authModalCode, /aria-live="polite"/i);
  });

  test('Below both forms: Two preference cards (Path A & Path B) and guest session note', () => {
    assert.match(authModalCode, /Just a concerned consumer/i);
    assert.match(authModalCode, /Set basic preferences/i);
    assert.match(authModalCode, /I need more personalisation/i);
    assert.match(authModalCode, /Build my complete profile/i);
    assert.match(authModalCode, /Guests can use either path without an account/i);
  });

  test('PersonalizeModal contains exact subtitle, action buttons and medical disclaimer', () => {
    assert.match(
      personalizeModalCode,
      /Select everything that applies\. You can change these choices later\./i
    );
    assert.match(personalizeModalCode, /Save profile/i);
    assert.match(personalizeModalCode, /Skip for now/i);
    assert.match(
      personalizeModalCode,
      /General information, not medical advice\. Follow your doctor's or dietitian's advice\./i
    );
  });

  test('PersonalizeModal enforces separate health consent screen for Path B (sections 01 and 02)', () => {
    assert.match(
      personalizeModalCode,
      /We store your conditions and allergies only to personalise ratings and safety checks\. You can delete them anytime\./i
    );
    assert.match(personalizeModalCode, /I Consent &amp; Continue|I Consent & Continue/i);
    assert.match(personalizeModalCode, /health-consent-card/i);
  });

  test('Pill chips use + icon unselected and tick icon checked (not colour alone)', () => {
    assert.match(personalizeModalCode, /pill-chip/i);
    assert.match(personalizeModalCode, /Plus size=/i);
    assert.match(personalizeModalCode, /Check size=/i);
  });

  test('profile_options.json defines 5 sections with exact required chips', () => {
    assert.equal(optionsData.sections.length, 5);

    const conditionsSec = optionsData.sections.find((s) => s.id === 'dietary_conditions');
    const conditionIds = conditionsSec.chips.map((c) => c.id);
    assert.ok(conditionIds.includes('diabetes'));
    assert.ok(conditionIds.includes('prediabetes'));
    assert.ok(conditionIds.includes('high_blood_pressure'));
    assert.ok(conditionIds.includes('high_cholesterol'));
    assert.ok(conditionIds.includes('coeliac_disease'));
    assert.ok(conditionIds.includes('lactose_intolerance'));

    const allergiesSec = optionsData.sections.find((s) => s.id === 'allergies');
    const allergyIds = allergiesSec.chips.map((c) => c.id);
    assert.ok(allergyIds.includes('peanuts'));
    assert.ok(allergyIds.includes('milk'));
    assert.ok(allergyIds.includes('eggs'));
    assert.ok(allergyIds.includes('wheat'));
    assert.ok(allergyIds.includes('gluten'));
    assert.ok(!allergyIds.includes('tree_nuts'));
    assert.ok(!allergyIds.includes('soy'));
    assert.ok(!allergyIds.includes('sesame'));
    assert.ok(!allergyIds.includes('fish_shellfish'));

    const patternSec = optionsData.sections.find((s) => s.id === 'dietary_pattern');
    assert.equal(patternSec.is_single_select, true);
  });
});
