import React, { useState } from 'react';
import {
  X,
  User,
  Mail,
  ShieldCheck,
  AlertTriangle,
  Download,
  Trash2,
  CheckCircle2,
  AlertCircle,
  KeyRound,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import {
  apiUpdateUser,
  apiVerifyEmail,
  apiExportData,
  apiDeleteAccount,
} from '../services/api';

export default function AccountModal() {
  const {
    accountModalOpen,
    setAccountModalOpen,
    user,
    token,
    setUser,
    logout,
  } = useAuth();

  const [editName, setEditName] = useState(user?.full_name || '');
  const [editEmail, setEditEmail] = useState(user?.email || '');
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // Delete modal state
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  if (!accountModalOpen || !user) return null;

  const handleUpdate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMsg('');
    setErrorMsg('');
    try {
      const res = await apiUpdateUser({ full_name: editName, email: editEmail }, token);
      setUser(res.user);
      setMsg(res.message);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to update profile.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    setLoading(true);
    setMsg('');
    setErrorMsg('');
    try {
      const res = await apiVerifyEmail(token);
      setUser({ ...user, is_verified: true });
      setMsg(res.message);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to verify email.');
    } finally {
      setLoading(false);
    }
  };

  const handleExportData = async () => {
    try {
      setLoading(true);
      const data = await apiExportData(token);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `labeltruth_my_data_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setMsg('Personal data package downloaded successfully.');
    } catch (err) {
      setErrorMsg(err.message || 'Failed to export data.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async (e) => {
    e.preventDefault();
    setDeleteLoading(true);
    setDeleteError('');
    try {
      await apiDeleteAccount(deletePassword, token);
      logout();
      setConfirmDeleteOpen(false);
      setAccountModalOpen(false);
    } catch (err) {
      setDeleteError(err.message || 'Incorrect password.');
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <div
      className="auth-modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="account-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) setAccountModalOpen(false);
      }}
    >
      <div className="account-modal-window">
        {/* Header */}
        <div className="personalize-modal-header" style={{ padding: '24px 28px 18px 28px' }}>
          <div>
            <div className="personalize-eyebrow">YOUR ACCOUNT</div>
            <h2 id="account-modal-title" className="personalize-title">
              Account &amp; Security Settings
            </h2>
          </div>
          <button
            type="button"
            className="auth-close-btn"
            aria-label="Close account modal"
            onClick={() => setAccountModalOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        {/* Inline Alerts */}
        {msg && (
          <div className="auth-inline-success" role="status" style={{ margin: '0 28px 16px 28px' }}>
            <CheckCircle2 size={16} />
            <span>{msg}</span>
          </div>
        )}
        {errorMsg && (
          <div className="auth-inline-error" role="alert" style={{ margin: '0 28px 16px 28px' }}>
            <AlertCircle size={16} />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="account-modal-body">
          {/* Verification Status */}
          <div className="account-verification-card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {user.is_verified ? (
                <div className="acc-verified-badge">
                  <CheckCircle2 size={16} color="#047857" />
                  <span>Verified Email Address</span>
                </div>
              ) : (
                <div className="acc-unverified-badge">
                  <AlertTriangle size={16} color="#d97706" />
                  <span>Email Not Verified</span>
                </div>
              )}
            </div>
            {!user.is_verified && (
              <button
                type="button"
                className="acc-verify-btn"
                disabled={loading}
                onClick={handleVerify}
              >
                Verify Email
              </button>
            )}
          </div>

          {/* Edit Profile Form */}
          <form onSubmit={handleUpdate} className="account-edit-form">
            <h3 className="account-section-heading">Personal Information</h3>

            <div className="auth-input-group">
              <label htmlFor="acc-name" className="auth-label">
                Full name
              </label>
              <input
                id="acc-name"
                type="text"
                required
                className="auth-input"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
              />
            </div>

            <div className="auth-input-group">
              <label htmlFor="acc-email" className="auth-label">
                Email address
              </label>
              <input
                id="acc-email"
                type="email"
                required
                className="auth-input"
                value={editEmail}
                onChange={(e) => setEditEmail(e.target.value)}
              />
            </div>

            <button type="submit" className="auth-primary-btn" style={{ width: 'auto' }} disabled={loading}>
              Save Profile Changes
            </button>
          </form>

          {/* Export My Data (JSON) */}
          <div className="account-data-section">
            <h3 className="account-section-heading">Data Portability</h3>
            <p style={{ fontSize: '0.82rem', color: '#6b7280', margin: '4px 0 12px 0' }}>
              Download a complete JSON package of your account data, choices, and saved comparisons.
            </p>
            <button
              type="button"
              className="personalize-secondary-btn"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
              onClick={handleExportData}
              disabled={loading}
            >
              <Download size={15} /> Export My Data (JSON)
            </button>
          </div>

          {/* Delete Account (Hard Delete) */}
          <div className="account-danger-zone">
            <h3 className="account-section-heading" style={{ color: '#dc2626' }}>
              Delete Account
            </h3>
            <p style={{ fontSize: '0.82rem', color: '#6b7280', margin: '4px 0 12px 0' }}>
              Hard delete your account, personal data, and saved comparisons permanently. This action cannot be undone.
            </p>
            <button
              type="button"
              className="acc-danger-btn"
              onClick={() => {
                setConfirmDeleteOpen(true);
                setDeleteError('');
                setDeletePassword('');
              }}
            >
              <Trash2 size={15} /> Delete Account
            </button>
          </div>
        </div>

        {/* Delete Confirmation Dialog */}
        {confirmDeleteOpen && (
          <div className="acc-confirm-overlay">
            <div className="acc-confirm-box">
              <h4 style={{ color: '#991b1b', fontSize: '1rem', fontWeight: 800 }}>
                Confirm Permanent Account Deletion
              </h4>
              <p style={{ fontSize: '0.82rem', color: '#4b5563', margin: '8px 0 16px 0' }}>
                Please enter your password to confirm hard deletion. All your personal data and comparisons will be erased immediately.
              </p>

              {deleteError && (
                <div className="auth-inline-error" style={{ marginBottom: '12px' }}>
                  <AlertCircle size={15} />
                  <span>{deleteError}</span>
                </div>
              )}

              <form onSubmit={handleDeleteAccount}>
                <div className="auth-input-group">
                  <label htmlFor="confirm-del-pwd" className="auth-label">
                    Your Password
                  </label>
                  <input
                    id="confirm-del-pwd"
                    type="password"
                    required
                    className="auth-input"
                    placeholder="Enter password to confirm"
                    value={deletePassword}
                    onChange={(e) => setDeletePassword(e.target.value)}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '16px' }}>
                  <button
                    type="button"
                    className="personalize-secondary-btn"
                    onClick={() => setConfirmDeleteOpen(false)}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="acc-danger-btn"
                    disabled={deleteLoading}
                  >
                    {deleteLoading ? 'Deleting...' : 'Permanently Delete'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
