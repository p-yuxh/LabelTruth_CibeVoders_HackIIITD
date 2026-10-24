import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  apiLogIn,
  apiSignUp,
  apiGetMe,
  apiSaveProfile,
  fetchProfileOptions,
} from '../services/api';
import localProfileOptions from '../config/profile_options.json';

const AuthContext = createContext(null);

const DEFAULT_GUEST_PROFILE = {
  dietary_conditions: [],
  allergies: [],
  nutrition_goals: [],
  avoid_ingredients: [],
  dietary_pattern: 'none',
  health_data_consent: false,
  path_taken: 'basic',
};

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('labeltruth_token'));
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(() => {
    try {
      const saved = localStorage.getItem('labeltruth_guest_profile');
      return saved ? JSON.parse(saved) : DEFAULT_GUEST_PROFILE;
    } catch {
      return DEFAULT_GUEST_PROFILE;
    }
  });
  const [profileOptions, setProfileOptions] = useState(localProfileOptions);

  // Modal display states
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalTab, setAuthModalTab] = useState('login'); // 'login' | 'signup'
  const [personalizeModalOpen, setPersonalizeModalOpen] = useState(false);
  const [personalizePath, setPersonalizePath] = useState('basic'); // 'basic' (Path A) | 'complete' (Path B)
  const [accountModalOpen, setAccountModalOpen] = useState(false);
  const [savedModalOpen, setSavedModalOpen] = useState(false);
  const [legalModalOpen, setLegalModalOpen] = useState(false);
  const [legalModalType, setLegalModalType] = useState('terms'); // 'terms' | 'privacy'

  // Fetch options from backend or fallback to bundled json
  useEffect(() => {
    fetchProfileOptions()
      .then((opts) => {
        if (opts && opts.sections) setProfileOptions(opts);
      })
      .catch(() => {});
  }, []);

  // Validate session on mount
  useEffect(() => {
    if (token) {
      apiGetMe(token)
        .then((res) => {
          if (res.user) setUser(res.user);
          if (res.profile) setProfile(res.profile);
        })
        .catch(() => {
          // Token expired or invalid
          localStorage.removeItem('labeltruth_token');
          setToken(null);
          setUser(null);
        });
    }
  }, [token]);

  const login = async (credentials) => {
    const res = await apiLogIn(credentials);
    localStorage.setItem('labeltruth_token', res.token);
    setToken(res.token);
    setUser(res.user);
    if (res.profile) setProfile(res.profile);
    setAuthModalOpen(false);
    return res;
  };

  const signup = async (userData) => {
    const res = await apiSignUp(userData);
    localStorage.setItem('labeltruth_token', res.token);
    setToken(res.token);
    setUser(res.user);
    if (res.profile) setProfile(res.profile);
    setAuthModalOpen(false);
    return res;
  };

  const logout = () => {
    localStorage.removeItem('labeltruth_token');
    setToken(null);
    setUser(null);
    // Revert to guest profile in session
    try {
      const savedGuest = localStorage.getItem('labeltruth_guest_profile');
      setProfile(savedGuest ? JSON.parse(savedGuest) : DEFAULT_GUEST_PROFILE);
    } catch {
      setProfile(DEFAULT_GUEST_PROFILE);
    }
  };

  const saveUserProfile = async (profileData) => {
    const res = await apiSaveProfile(profileData, token);
    const updatedProfile = res.profile || profileData;
    setProfile(updatedProfile);

    // If guest, keep in local storage session
    if (!token) {
      try {
        localStorage.setItem('labeltruth_guest_profile', JSON.stringify(updatedProfile));
      } catch {}
    }
    return res;
  };

  const openAuth = (tab = 'login') => {
    setAuthModalTab(tab);
    setAuthModalOpen(true);
  };

  const openPersonalize = (path = 'basic') => {
    setPersonalizePath(path);
    setPersonalizeModalOpen(true);
  };

  const openLegal = (type = 'terms') => {
    setLegalModalType(type);
    setLegalModalOpen(true);
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        profile,
        profileOptions,
        isLoggedIn: Boolean(user && token),
        isGuest: !token,
        login,
        signup,
        logout,
        saveUserProfile,
        setUser,
        setProfile,
        // Modal toggles
        authModalOpen,
        setAuthModalOpen,
        authModalTab,
        setAuthModalTab,
        personalizeModalOpen,
        setPersonalizeModalOpen,
        personalizePath,
        setPersonalizePath,
        accountModalOpen,
        setAccountModalOpen,
        savedModalOpen,
        setSavedModalOpen,
        legalModalOpen,
        setLegalModalOpen,
        legalModalType,
        setLegalModalType,
        // Convenience triggers
        openAuth,
        openPersonalize,
        openLegal,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

