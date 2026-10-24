import React, { useState } from 'react';
import {
  X,
  Eye,
  EyeOff,
  Check,
  AlertCircle,
  Sliders,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Package,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { apiForgotPassword, apiResetPassword } from '../services/api';

export default function AuthModal() {
  const {
    authModalOpen,
    setAuthModalOpen,
    authModalTab,
    setAuthModalTab,
    login,
    signup,
    openPersonalize,
    openLegal,
  } = useAuth();

  // Form states
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [termsAgreed, setTermsAgreed] = useState(false);
  const [ageConfirmed, setAgeConfirmed] = useState(false);

  // Status & validation states
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Forgot password mode
  const [forgotMode, setForgotMode] = useState(false);
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [resetStep, setResetStep] = useState('request'); // 'request' | 'confirm'

  if (!authModalOpen) return null;

  // Password strength evaluation
  const evalPasswordStrength = (pwd) => {
    if (!pwd) return { score: 0, label: '', color: '#d1d5db' };
    if (pwd.length < 8) return { score: 1, label: 'Too short (min 8 characters)', color: '#ef4444' };
    const hasUpper = /[A-Z]/.test(pwd);
    const hasLower = /[a-z]/.test(pwd);
    const hasDigit = /[0-9]/.test(pwd);
    const hasSpecial = /[^A-Za-z0-9]/.test(pwd);
    const checks = [hasUpper, hasLower, hasDigit, hasSpecial].filter(Boolean).length;
    if (pwd.length >= 12 && checks >= 3) return { score: 3, label: 'Strong password', color: '#10b981' };
    if (checks >= 2) return { score: 2, label: 'Medium strength', color: '#d97706' };
    return { score: 1, label: 'Weak password: add numbers or uppercase', color: '#ef4444' };
  };

  const strength = evalPasswordStrength(password);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');
    setLoading(true);

    try {
      if (authModalTab === 'signup') {
        if (!termsAgreed) {
          throw new Error('You must agree to the Terms and Privacy Policy to create an account.');
        }
        if (!ageConfirmed) {
          throw new Error('You must confirm that you are 18 or older to register.');
        }
        if (password.length < 8) {
          throw new Error('Password must be at least 8 characters long.');
        }

        await signup({
          full_name: name,
          email,
          password,
          terms_agreed: termsAgreed,
          age_confirmed: ageConfirmed,
        });
      } else {
        // Log in
        await login({ email, password });
      }
    } catch (err) {
      setErrorMsg(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setLoading(true);
    try {
      if (resetStep === 'request') {
        const res = await apiForgotPassword(email);
        setSuccessMsg(res.message);
        if (res.reset_code) {
          setResetCode(res.reset_code);
        }
        setResetStep('confirm');
      } else {
        const res = await apiResetPassword({
          email,
          reset_token: resetCode,
          new_password: newPassword,
        });
        setSuccessMsg(res.message);
        setTimeout(() => {
          setForgotMode(false);
          setResetStep('request');
          setAuthModalTab('login');
        }, 1500);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Password reset request failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleGuestPath = (path) => {
    setAuthModalOpen(false);
    openPersonalize(path);
  };

  return (
    <div
      className="auth-modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) setAuthModalOpen(false);
      }}
    >
      <div className="auth-modal-window">
        {/* Close Button */}
        <button
          type="button"
          className="auth-close-btn"
          aria-label="Close modal"
          onClick={() => setAuthModalOpen(false)}
        >
          <X size={20} />
        </button>

        {/* -------------------------------------------------------------
            LEFT PANEL: Light Green Gradient + Neutral Illustrated Artwork
           ------------------------------------------------------------- */}
        <div className="auth-left-panel">
          <div className="auth-brand-lockup">
            <div className="auth-logo-badge">LT</div>
            <span className="auth-logo-text">LabelTruth</span>
          </div>

          <div className="auth-left-content">
            <span className="auth-eyebrow">KNOW WHAT'S INSIDE</span>
            <h2 className="auth-headline">Better choices start with the truth.</h2>
            <p className="auth-subtext">
              Save comparisons, revisit evidence, and make every shopping decision with confidence.
            </p>
          </div>

          {/* Neutral Illustrated Product Packaging Vector Graphics */}
          <div className="auth-illustration-container" aria-hidden="true">
            <svg
              className="auth-illustrated-svg"
              viewBox="0 0 280 180"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Product Box 1 (Cereal / Snack) */}
              <rect
                x="30"
                y="40"
                width="70"
                height="110"
                rx="6"
                fill="#ffffff"
                stroke="#a7f3d0"
                strokeWidth="2.5"
              />
              <rect x="42" y="55" width="46" height="8" rx="2" fill="#d1fae5" />
              <rect x="42" y="70" width="35" height="5" rx="1.5" fill="#e5e7eb" />
              <rect x="42" y="80" width="46" height="5" rx="1.5" fill="#e5e7eb" />
              <circle cx="65" cy="115" r="16" fill="#ecfdf5" stroke="#10b981" strokeWidth="2" />
              <path
                d="M59 115L63 119L71 111"
                stroke="#047857"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Product Bottle 2 (Beverage / Oil) */}
              <rect
                x="120"
                y="55"
                width="50"
                height="95"
                rx="12"
                fill="#ffffff"
                stroke="#6ee7b7"
                strokeWidth="2.5"
              />
              <rect x="135" y="32" width="20" height="23" rx="4" fill="#a7f3d0" />
              <line x1="130" y1="85" x2="160" y2="85" stroke="#10b981" strokeWidth="2" />
              <rect x="130" y="93" width="30" height="4" rx="1" fill="#e5e7eb" />
              <rect x="130" y="101" width="22" height="4" rx="1" fill="#e5e7eb" />

              {/* Inspection Nutrition Fact Card 3 */}
              <rect
                x="190"
                y="65"
                width="65"
                height="85"
                rx="6"
                fill="#ffffff"
                stroke="#10b981"
                strokeWidth="2.5"
              />
              <rect x="200" y="78" width="45" height="6" rx="2" fill="#047857" />
              <line x1="200" y1="92" x2="245" y2="92" stroke="#e5e7eb" strokeWidth="1.5" />
              <line x1="200" y1="102" x2="245" y2="102" stroke="#e5e7eb" strokeWidth="1.5" />
              <line x1="200" y1="112" x2="245" y2="112" stroke="#e5e7eb" strokeWidth="1.5" />
              <circle cx="238" cy="132" r="7" fill="#10b981" />
              <path
                d="M234 132L237 135L242 129"
                stroke="#ffffff"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        </div>

        {/* -------------------------------------------------------------
            RIGHT PANEL: White Panel, Forms, and Preferences Cards
           ------------------------------------------------------------- */}
        <div className="auth-right-panel">
          {/* Tab Switcher (Log in | Sign up) */}
          {!forgotMode && (
            <div className="auth-tab-row" role="tablist" aria-label="Account access modes">
              <button
                type="button"
                role="tab"
                id="tab-login"
                aria-selected={authModalTab === 'login'}
                aria-controls="panel-login"
                className={`auth-tab-btn ${authModalTab === 'login' ? 'active' : ''}`}
                onClick={() => {
                  setAuthModalTab('login');
                  setErrorMsg('');
                  setSuccessMsg('');
                }}
              >
                Log in
              </button>
              <button
                type="button"
                role="tab"
                id="tab-signup"
                aria-selected={authModalTab === 'signup'}
                aria-controls="panel-signup"
                className={`auth-tab-btn ${authModalTab === 'signup' ? 'active' : ''}`}
                onClick={() => {
                  setAuthModalTab('signup');
                  setErrorMsg('');
                  setSuccessMsg('');
                }}
              >
                Sign up
              </button>
            </div>
          )}

          {/* Inline Screen Reader Announced Alerts */}
          {errorMsg && (
            <div className="auth-inline-error" role="alert" aria-live="polite">
              <AlertCircle size={16} />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="auth-inline-success" role="status" aria-live="polite">
              <Check size={16} />
              <span>{successMsg}</span>
            </div>
          )}

          {/* =========================================================
              FORGOT PASSWORD FLOW
             ========================================================= */}
          {forgotMode ? (
            <form onSubmit={handleForgotPassword} className="auth-form-body">
              <h3 className="auth-form-title">Reset Your Password</h3>
              <p className="auth-form-description">
                {resetStep === 'request'
                  ? 'Enter your registered email address and we will provide a reset code.'
                  : 'Enter the verification code and choose your new password.'}
              </p>

              <div className="auth-input-group">
                <label htmlFor="forgot-email" className="auth-label">
                  Email address
                </label>
                <input
                  id="forgot-email"
                  type="email"
                  required
                  className="auth-input"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={resetStep === 'confirm'}
                />
              </div>

              {resetStep === 'confirm' && (
                <>
                  <div className="auth-input-group">
                    <label htmlFor="reset-code" className="auth-label">
                      Reset Code
                    </label>
                    <input
                      id="reset-code"
                      type="text"
                      required
                      className="auth-input"
                      placeholder="e.g. A1B2C3D4"
                      value={resetCode}
                      onChange={(e) => setResetCode(e.target.value)}
                    />
                  </div>

                  <div className="auth-input-group">
                    <label htmlFor="reset-new-password" className="auth-label">
                      New Password (min 8 characters)
                    </label>
                    <input
                      id="reset-new-password"
                      type="password"
                      required
                      minLength={8}
                      className="auth-input"
                      placeholder="Enter new secure password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                    />
                  </div>
                </>
              )}

              <button type="submit" className="auth-primary-btn" disabled={loading}>
                {loading
                  ? 'Processing...'
                  : resetStep === 'request'
                  ? 'Send Reset Code'
                  : 'Update Password'}
              </button>

              <button
                type="button"
                className="auth-text-link"
                style={{ marginTop: '12px', textAlign: 'center', display: 'block' }}
                onClick={() => {
                  setForgotMode(false);
                  setResetStep('request');
                  setErrorMsg('');
                }}
              >
                Back to Log in
              </button>
            </form>
          ) : authModalTab === 'signup' ? (
            /* =========================================================
                SIGN UP FORM
               ========================================================= */
            <form onSubmit={handleSubmit} className="auth-form-body" id="panel-signup">
              <div className="auth-input-group">
                <label htmlFor="signup-name" className="auth-label">
                  Full name
                </label>
                <input
                  id="signup-name"
                  type="text"
                  required
                  className="auth-input"
                  placeholder="e.g. Aarti Sharma"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div className="auth-input-group">
                <label htmlFor="signup-email" className="auth-label">
                  Email address
                </label>
                <input
                  id="signup-email"
                  type="email"
                  required
                  className="auth-input"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div className="auth-input-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label htmlFor="signup-password" className="auth-label">
                    Password (min 8 characters)
                  </label>
                </div>
                <div className="auth-password-wrapper">
                  <input
                    id="signup-password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    minLength={8}
                    className="auth-input"
                    placeholder="Create a secure password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    className="auth-pw-toggle"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>

                {/* Password strength hint & bar */}
                {password.length > 0 && (
                  <div className="auth-strength-container">
                    <div className="auth-strength-bars">
                      <span
                        className={`auth-strength-bar ${strength.score >= 1 ? 'filled' : ''}`}
                        style={{ backgroundColor: strength.score >= 1 ? strength.color : undefined }}
                      />
                      <span
                        className={`auth-strength-bar ${strength.score >= 2 ? 'filled' : ''}`}
                        style={{ backgroundColor: strength.score >= 2 ? strength.color : undefined }}
                      />
                      <span
                        className={`auth-strength-bar ${strength.score >= 3 ? 'filled' : ''}`}
                        style={{ backgroundColor: strength.score >= 3 ? strength.color : undefined }}
                      />
                    </div>
                    <span className="auth-strength-text" style={{ color: strength.color }}>
                      {strength.label}
                    </span>
                  </div>
                )}
              </div>

              {/* Required Checkbox 1: Terms & Privacy */}
              <div className="auth-checkbox-row">
                <input
                  id="signup-terms"
                  type="checkbox"
                  required
                  checked={termsAgreed}
                  onChange={(e) => setTermsAgreed(e.target.checked)}
                  className="auth-checkbox"
                />
                <label htmlFor="signup-terms" className="auth-checkbox-label">
                  I agree to the{' '}
                  <button
                    type="button"
                    className="auth-link-button"
                    onClick={() => openLegal('terms')}
                  >
                    Terms
                  </button>{' '}
                  and{' '}
                  <button
                    type="button"
                    className="auth-link-button"
                    onClick={() => openLegal('privacy')}
                  >
                    Privacy Policy
                  </button>
                </label>
              </div>

              {/* Required Checkbox 2: 18 or older */}
              <div className="auth-checkbox-row">
                <input
                  id="signup-age"
                  type="checkbox"
                  required
                  checked={ageConfirmed}
                  onChange={(e) => setAgeConfirmed(e.target.checked)}
                  className="auth-checkbox"
                />
                <label htmlFor="signup-age" className="auth-checkbox-label">
                  I am 18 or older
                </label>
              </div>

              <button type="submit" className="auth-primary-btn" disabled={loading}>
                {loading ? 'Creating account...' : 'Create account'}
              </button>

              <div className="auth-switch-prompt">
                Already have an account?{' '}
                <button
                  type="button"
                  className="auth-text-link"
                  onClick={() => {
                    setAuthModalTab('login');
                    setErrorMsg('');
                  }}
                >
                  Log in
                </button>
              </div>
            </form>
          ) : (
            /* =========================================================
                LOG IN FORM
               ========================================================= */
            <form onSubmit={handleSubmit} className="auth-form-body" id="panel-login">
              <div className="auth-input-group">
                <label htmlFor="login-email" className="auth-label">
                  Email address
                </label>
                <input
                  id="login-email"
                  type="email"
                  required
                  className="auth-input"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div className="auth-input-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <label htmlFor="login-password" className="auth-label">
                    Password
                  </label>
                  <button
                    type="button"
                    className="auth-text-link"
                    style={{ fontSize: '0.8rem' }}
                    onClick={() => {
                      setForgotMode(true);
                      setErrorMsg('');
                      setSuccessMsg('');
                    }}
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="auth-password-wrapper">
                  <input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    className="auth-input"
                    placeholder="Your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    className="auth-pw-toggle"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button type="submit" className="auth-primary-btn" disabled={loading}>
                {loading ? 'Logging in...' : 'Log in'}
              </button>

              <div className="auth-switch-prompt">
                New to LabelTruth?{' '}
                <button
                  type="button"
                  className="auth-text-link"
                  onClick={() => {
                    setAuthModalTab('signup');
                    setErrorMsg('');
                  }}
                >
                  Create an account
                </button>
              </div>
            </form>
          )}

          {/* =========================================================
              BELOW BOTH FORMS: TWO PERSONALISATION PATH CARDS
             ========================================================= */}
          <div className="auth-personalise-section">
            <div className="auth-or-divider">
              <span>OR PERSONALISE AS GUEST</span>
            </div>

            <div className="auth-path-cards-grid">
              {/* Path A: Concerned Consumer */}
              <button
                type="button"
                className="auth-path-card"
                onClick={() => handleGuestPath('basic')}
                title="Open basic preferences without health conditions"
              >
                <div className="auth-path-card-icon basic">
                  <Sliders size={18} />
                </div>
                <div className="auth-path-card-text">
                  <div className="auth-path-card-title">Just a concerned consumer</div>
                  <div className="auth-path-card-subtitle">Set basic preferences</div>
                </div>
                <ArrowRight size={15} className="auth-path-card-arrow" />
              </button>

              {/* Path B: Complete Personalisation */}
              <button
                type="button"
                className="auth-path-card complete"
                onClick={() => handleGuestPath('complete')}
                title="Build complete profile including clinical conditions & allergies"
              >
                <div className="auth-path-card-icon complete">
                  <Sparkles size={18} />
                </div>
                <div className="auth-path-card-text">
                  <div className="auth-path-card-title">I need more personalisation</div>
                  <div className="auth-path-card-subtitle">Build my complete profile</div>
                </div>
                <ArrowRight size={15} className="auth-path-card-arrow" />
              </button>
            </div>

            <p className="auth-guest-note">
              Guests can use either path without an account (profile kept in session only, never stored); offer "Create account to save this".
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
