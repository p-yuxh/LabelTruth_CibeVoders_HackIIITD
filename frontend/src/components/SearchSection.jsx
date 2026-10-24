import React, { useState, useRef } from 'react';
import { Search, RefreshCw, Camera, UploadCloud, X, CheckCircle2 } from 'lucide-react';
import { detectProductFromImage } from '../services/api';

const SUGGESTIONS = [
  'Cadbury Bournvita',
  'Nestle Maggi 2-Minute Noodles',
  'Too Yumm Multigrain Chips',
  'Yoga Bar Dark Chocolate Oats',
  'Amul Butter',
];

export default function SearchSection({ onSearch, onImageAudit, loading }) {
  const [query, setQuery] = useState('');
  const [forceRefresh, setForceRefresh] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState('');
  const [detectingImage, setDetectingImage] = useState(false);
  const [detectedLabel, setDetectedLabel] = useState('');

  const fileInputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (loading) return;

    if (query.trim()) {
      onSearch(query.trim(), forceRefresh);
    }
  };

  const handleChipClick = (suggestion) => {
    setQuery(suggestion);
    handleClearImage();
    onSearch(suggestion, forceRefresh);
  };

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSelectedImage(file);
    const url = URL.createObjectURL(file);
    setImagePreviewUrl(url);
    setDetectingImage(true);
    setDetectedLabel('Scanning packaging image...');

    try {
      // Run automatic product detection from image
      const res = await detectProductFromImage(file);
      const productName = res.detected_product || '';
      
      setDetectedLabel(productName);
      setQuery(productName);

      // Trigger product audit directly!
      if (productName && productName !== 'Packaged Food Product') {
        onSearch(productName, forceRefresh);
      }
    } catch (err) {
      setDetectedLabel('Could not auto-detect product. Please type query.');
    } finally {
      setDetectingImage(false);
    }
  };

  const handleClearImage = () => {
    setSelectedImage(null);
    if (imagePreviewUrl) {
      URL.revokeObjectURL(imagePreviewUrl);
      setImagePreviewUrl('');
    }
    setDetectedLabel('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="search-card">
      <form onSubmit={handleSubmit} className="search-input-wrapper">
        {/* Hidden File Input */}
        <input
          type="file"
          ref={fileInputRef}
          accept="image/*"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />

        {/* Attach Image Button */}
        <button
          type="button"
          className="image-attach-btn"
          onClick={() => fileInputRef.current?.click()}
          title="Upload or snap a photo of product packaging"
          disabled={loading || detectingImage}
        >
          <Camera size={18} />
          <span>Attach Photo</span>
        </button>

        {/* Search Query Input */}
        <input
          type="text"
          className="search-input"
          placeholder="Search food brand or attach product photo to detect automatically..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading || detectingImage}
        />

        {/* Submit Audit Button */}
        <button
          type="submit"
          className="btn-search"
          disabled={loading || detectingImage || !query.trim()}
        >
          {loading || detectingImage ? (
            <div className="spinner" />
          ) : (
            <>
              <Search size={16} />
              <span>Audit Product</span>
            </>
          )}
        </button>
      </form>

      {/* Image Attachment Preview Strip */}
      {selectedImage && (
        <div className="image-preview-strip">
          <div className="image-preview-info">
            {imagePreviewUrl && (
              <img
                src={imagePreviewUrl}
                alt="Product package"
                className="image-preview-thumb"
              />
            )}
            <div>
              <div className="image-detected-tag">
                {detectingImage ? (
                  <span>Analyzing packaging...</span>
                ) : (
                  <span>Detected: {detectedLabel || selectedImage.name}</span>
                )}
              </div>
              <div className="image-detected-sub">
                {selectedImage.name} • {(selectedImage.size / 1024).toFixed(1)} KB
              </div>
            </div>
          </div>

          <button
            type="button"
            className="btn-remove-image"
            onClick={handleClearImage}
            title="Remove attached photo"
          >
            <X size={14} />
            <span>Remove</span>
          </button>
        </div>
      )}

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
              disabled={loading || detectingImage}
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
