import React, { useState } from 'react';
import { Search, RefreshCw } from 'lucide-react';

const SUGGESTIONS = [
  'Cadbury Bournvita',
  'Nestle Maggi 2-Minute Noodles',
  'Lays Potato Chips India',
  'Coca-Cola Zero Sugar Diet Coke',
  'Yoga Bar Dark Chocolate Oats',
  'Amul Butter',
];

export default function SearchSection({ onSearch, loading }) {
  const [query, setQuery] = useState('');
  const [forceRefresh, setForceRefresh] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (loading) return;

    const clean = query.trim();
    if (clean && clean.toLowerCase() !== 'packaged food product') {
      onSearch(clean, forceRefresh);
    }
  };

  const handleChipClick = (suggestion) => {
    setQuery(suggestion);
    onSearch(suggestion, forceRefresh);
  };

  return (
    <div className="search-card">
      <form onSubmit={handleSubmit} className="search-input-wrapper">
        {/* Search Query Input */}
        <input
          type="text"
          className="search-input"
          placeholder="Search packaged food or brand (e.g. Cadbury Bournvita, Nestle Maggi, Lay's Potato Chips, Diet Coke)..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
          autoFocus
        />

        {/* Submit Audit Button */}
        <button
          type="submit"
          className="btn-search"
          disabled={loading || !query.trim()}
        >
          {loading ? (
            <div className="spinner" />
          ) : (
            <>
              <Search size={16} />
              <span>Audit Product</span>
            </>
          )}
        </button>
      </form>

      {/* Suggestion Chips & Refresh Checkbox */}
      <div className="search-footer">
        <div className="suggestion-chips">
          <span className="chip-label">Suggestions:</span>
          {SUGGESTIONS.map((item) => (
            <button
              key={item}
              type="button"
              className="chip-btn"
              onClick={() => handleChipClick(item)}
              disabled={loading}
            >
              {item}
            </button>
          ))}
        </div>

        <div className="search-options">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={forceRefresh}
              onChange={(e) => setForceRefresh(e.target.checked)}
            />
            <span>Force fresh verification from live sources</span>
          </label>
          {forceRefresh && (
            <span style={{ color: '#ffffff', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 700 }}>
              <RefreshCw size={12} /> Live Scan Active
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
