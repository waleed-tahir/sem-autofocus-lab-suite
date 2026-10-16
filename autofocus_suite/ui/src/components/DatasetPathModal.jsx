import React, { useState, useEffect } from 'react';
import { Folder, Check, AlertCircle, X, RefreshCw, HardDrive } from 'lucide-react';

export default function DatasetPathModal({ 
  isOpen, 
  onClose, 
  onDatasetPathChanged,
  currentPath 
}) {
  const [pathInput, setPathInput] = useState(currentPath || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  useEffect(() => {
    if (currentPath) {
      setPathInput(currentPath);
    }
  }, [currentPath]);

  if (!isOpen) return null;

  const handleApply = async (targetPath) => {
    const pathToSubmit = targetPath || pathInput;
    if (!pathToSubmit.trim()) return;

    setLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await fetch('/api/dataset-path', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: pathToSubmit.trim() })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to set dataset directory');
      }

      setSuccessMsg(`Successfully loaded ${data.count} dataset(s) from directory.`);
      if (onDatasetPathChanged) {
        onDatasetPathChanged(data.path, data.datasets);
      }
      setTimeout(() => {
        onClose();
        setSuccessMsg(null);
      }, 1000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const defaultLabPath = "c:\\Users\\PC\\Desktop\\Computer Vision Lab\\datasets";

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0, 0, 0, 0.65)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      animation: 'fadeIn 0.15s ease'
    }}>
      <div className="win-card" style={{
        width: '540px',
        maxWidth: '92vw',
        background: 'var(--bg-card)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6)',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        padding: '24px'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '6px',
              background: 'rgba(0, 183, 195, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-cyan)'
            }}>
              <Folder size={18} />
            </div>
            <div>
              <h3 style={{ fontSize: '15px', fontWeight: '600' }}>Select Datasets Directory</h3>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                Point to a directory containing SEM / TEM focal stack folders
              </p>
            </div>
          </div>

          <button 
            className="btn-fluent-secondary"
            onClick={onClose}
            style={{ padding: '6px 8px', borderRadius: '4px' }}
          >
            <X size={14} />
          </button>
        </div>

        {/* Input Field */}
        <div>
          <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', marginBottom: '6px', color: 'var(--text-secondary)' }}>
            Dataset Root Path (Absolute Windows Directory):
          </label>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input 
              type="text" 
              className="macos-input"
              style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '12px' }}
              placeholder="e.g. C:\Microscopy\Datasets"
              value={pathInput}
              onChange={(e) => setPathInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleApply()}
            />
            <button 
              className="btn-fluent-primary"
              onClick={() => handleApply()}
              disabled={loading}
              style={{ minWidth: '90px' }}
            >
              {loading ? <RefreshCw size={14} className="animate-spin" /> : <Check size={14} />}
              {loading ? 'Scanning...' : 'Apply'}
            </button>
          </div>
        </div>

        {/* Quick Presets */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', textTransform: 'uppercase', fontWeight: '600' }}>
            Quick Presets:
          </span>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button 
              className="btn-fluent-secondary"
              style={{ fontSize: '11.5px', padding: '5px 10px' }}
              onClick={() => {
                setPathInput(defaultLabPath);
                handleApply(defaultLabPath);
              }}
            >
              <HardDrive size={13} color="var(--accent-cyan)" />
              Default Lab Suite ({defaultLabPath})
            </button>
          </div>
        </div>

        {/* Status Messages */}
        {error && (
          <div style={{
            background: 'rgba(232, 17, 35, 0.15)',
            border: '1px solid rgba(232, 17, 35, 0.3)',
            borderRadius: '4px',
            padding: '8px 12px',
            fontSize: '12px',
            color: '#FF6B68',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <AlertCircle size={15} />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div style={{
            background: 'rgba(16, 124, 65, 0.15)',
            border: '1px solid rgba(16, 124, 65, 0.3)',
            borderRadius: '4px',
            padding: '8px 12px',
            fontSize: '12px',
            color: '#34C759',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <Check size={15} />
            <span>{successMsg}</span>
          </div>
        )}
      </div>
    </div>
  );
}
