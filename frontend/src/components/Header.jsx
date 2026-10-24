import React, { useState } from 'react';
import {
  History,
  Sliders,
  Bookmark,
  User as UserIcon,
  LogOut,
  Settings,
  ChevronDown,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Header({ onOpenEvidenceLogs }) {
  const {
    isLoggedIn,
    user,
    logout,
    openAuth,
    openPersonalize,
    setAccountModalOpen,
    setSavedModalOpen,
    profile,
  } = useAuth();

  const [menuOpen, setMenuOpen] = useState(false);

  // Compute active chips count
  const activeConditions = (profile?.dietary_conditions || []).length;
  const activeAllergies = (profile?.allergies || []).length;
  const activeGoals = (profile?.nutrition_goals || []).length;
  const totalActive = activeConditions + activeAllergies + activeGoals;

  return (
    <header className="desktop-header">
      <div className="brand-wrapper">
        <div className="logo-badge">LT</div>
        <div className="brand-text">
          <h1>LabelTruth</h1>
          <p>Packaged Food Claims &amp; Ingredients Auditor</p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {/* Personalise Button */}
        <button
          type="button"
          className="header-action-btn personalize-btn"
          onClick={() => openPersonalize('basic')}
          title="Personalise ratings, clinical conditions and nutrition goals"
        >
          <Sliders size={14} />
          <span>Personalise</span>
          {totalActive > 0 && <span className="header-badge">{totalActive}</span>}
        </button>

        {/* Saved Comparisons */}
        <button
          type="button"
          className="header-action-btn"
          onClick={() => setSavedModalOpen(true)}
          title="Browse saved product comparisons"
        >
          <Bookmark size={14} />
          <span>Saved</span>
        </button>

        {/* Evidence Logs History */}
        <button
          type="button"
          className="header-action-btn"
          onClick={onOpenEvidenceLogs}
          title="Browse previously audited products"
        >
          <History size={14} />
          <span>Audit History</span>
        </button>

        {/* User Account or Login / Signup Button */}
        {isLoggedIn ? (
          <div style={{ position: 'relative' }}>
            <button
              type="button"
              className="header-user-btn"
              onClick={() => setMenuOpen(!menuOpen)}
              aria-expanded={menuOpen}
              aria-haspopup="true"
            >
              <div className="header-avatar-circle">
                {user?.full_name ? user.full_name[0].toUpperCase() : 'U'}
              </div>
              <span className="header-user-name">
                {user?.full_name ? user.full_name.split(' ')[0] : 'Account'}
              </span>
              <ChevronDown size={13} />
            </button>

            {menuOpen && (
              <div
                className="header-dropdown-menu"
                onMouseLeave={() => setMenuOpen(false)}
              >
                <div className="dropdown-user-info">
                  <div style={{ fontWeight: 700, color: '#ffffff' }}>{user.full_name}</div>
                  <div style={{ fontSize: '0.74rem', color: '#9ca3af' }}>{user.email}</div>
                </div>

                <div className="dropdown-divider" />

                <button
                  type="button"
                  className="dropdown-item"
                  onClick={() => {
                    setMenuOpen(false);
                    openPersonalize('complete');
                  }}
                >
                  <Sliders size={14} />
                  <span>Personalise Experience</span>
                </button>

                <button
                  type="button"
                  className="dropdown-item"
                  onClick={() => {
                    setMenuOpen(false);
                    setSavedModalOpen(true);
                  }}
                >
                  <Bookmark size={14} />
                  <span>Saved Comparisons</span>
                </button>

                <button
                  type="button"
                  className="dropdown-item"
                  onClick={() => {
                    setMenuOpen(false);
                    setAccountModalOpen(true);
                  }}
                >
                  <Settings size={14} />
                  <span>Account Settings</span>
                </button>

                <div className="dropdown-divider" />

                <button
                  type="button"
                  className="dropdown-item logout"
                  onClick={() => {
                    setMenuOpen(false);
                    logout();
                  }}
                >
                  <LogOut size={14} />
                  <span>Log out</span>
                </button>
              </div>
            )}
          </div>
        ) : (
          <button
            type="button"
            className="header-login-btn"
            onClick={() => openAuth('login')}
          >
            <UserIcon size={14} />
            <span>Log in | Sign up</span>
          </button>
        )}
      </div>
    </header>
  );
}
