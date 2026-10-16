import React, { useState, useRef } from 'react';
import { 
  ZoomIn, 
  Layers, 
  Eye, 
  Maximize2, 
  Sliders, 
  ShieldCheck, 
  Sparkles 
} from 'lucide-react';

export default function StackInspector({ 
  currentDataset, 
  theme 
}) {
  const [frameIdx, setFrameIdx] = useState(96);
  const [useAnscombe, setUseAnscombe] = useState(false);
  const [showRois, setShowRois] = useState(true);
  const [zoomLevel, setZoomLevel] = useState(3);
  const [loupeActive, setLoupeActive] = useState(false);
  const [loupePos, setLoupePos] = useState({ x: 0, y: 0 });

  const imgRef = useRef(null);
  const totalFrames = 200;

  const handleMouseMove = (e) => {
    if (!imgRef.current) return;
    const rect = imgRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    if (x >= 0 && x <= rect.width && y >= 0 && y <= rect.height) {
      setLoupeActive(true);
      setLoupePos({ x, y, width: rect.width, height: rect.height });
    } else {
      setLoupeActive(false);
    }
  };

  const handleMouseLeave = () => {
    setLoupeActive(false);
  };

  const frameUrl = `/api/frame/${currentDataset}/${frameIdx}?overlay_rois=${showRois}&anscombe=${useAnscombe}`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header Banner */}
      <div className="glass-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 22px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '38px', height: '38px', borderRadius: '10px', background: 'rgba(0, 229, 255, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ZoomIn size={20} color="#00E5FF" />
          </div>
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: '600' }}>Micrograph Stack & Interactive 4x Loupe Inspector</h2>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Inspect high-magnification specimen edge sharpness, beam shot grain, and Anscombe noise conversion
            </p>
          </div>
        </div>

        {/* Preset Quick Focus Jumps */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            className="btn-macos-secondary"
            onClick={() => setFrameIdx(30)}
            style={{ fontSize: '12px' }}
          >
            Under-Focus (z = 30)
          </button>
          <button 
            className="btn-macos-secondary"
            onClick={() => setFrameIdx(75)}
            style={{ fontSize: '12px' }}
          >
            Near Focus (z = 75)
          </button>
          <button 
            className="btn-macos-primary"
            onClick={() => setFrameIdx(96)}
            style={{ fontSize: '12px', padding: '6px 14px' }}
          >
            ★ True In-Focus (z = 96)
          </button>
          <button 
            className="btn-macos-secondary"
            onClick={() => setFrameIdx(160)}
            style={{ fontSize: '12px' }}
          >
            Over-Focus (z = 160)
          </button>
        </div>
      </div>

      {/* Main Inspection Canvas */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Controls Toolbar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
          {/* Continuous Z-Slider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flex: 1, minWidth: '300px' }}>
            <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)' }}>
              Focal Plane:
            </span>
            <input 
              type="range"
              min="0"
              max={totalFrames - 1}
              value={frameIdx}
              onChange={(e) => setFrameIdx(parseInt(e.target.value))}
              style={{ flex: 1, accentColor: 'var(--accent-blue)', cursor: 'pointer' }}
            />
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: '700', minWidth: '80px', color: frameIdx === 96 ? '#30D158' : 'var(--text-primary)' }}>
              z = {frameIdx} {frameIdx === 96 && '★ Peak'}
            </span>
          </div>

          {/* Toggles */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', cursor: 'pointer' }}>
              <input 
                type="checkbox"
                checked={useAnscombe}
                onChange={(e) => setUseAnscombe(e.target.checked)}
                style={{ accentColor: 'var(--accent-blue)' }}
              />
              Anscombe Stabilized
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', cursor: 'pointer' }}>
              <input 
                type="checkbox"
                checked={showRois}
                onChange={(e) => setShowRois(e.target.checked)}
                style={{ accentColor: 'var(--accent-blue)' }}
              />
              Dynamic 9-Zone ROIs
            </label>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>Loupe Zoom:</span>
              <select 
                className="macos-select"
                style={{ padding: '3px 8px', fontSize: '11px' }}
                value={zoomLevel}
                onChange={(e) => setZoomLevel(parseFloat(e.target.value))}
              >
                <option value="2">2x</option>
                <option value="3">3x</option>
                <option value="4">4x</option>
                <option value="6">6x Ultra</option>
              </select>
            </div>
          </div>
        </div>

        {/* Micrograph Canvas with Interactive Circular Loupe */}
        <div 
          style={{ 
            position: 'relative', 
            width: '100%', 
            height: '520px', 
            background: '#0a0a0c', 
            borderRadius: '12px', 
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'crosshair',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          <img 
            ref={imgRef}
            src={frameUrl}
            alt={`SEM Micrograph Frame ${frameIdx}`}
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />

          {/* Floating Magnifying Loupe Lens */}
          {loupeActive && imgRef.current && (
            <div 
              style={{
                position: 'absolute',
                top: `${loupePos.y - 85}px`,
                left: `${loupePos.x - 85}px`,
                width: '170px',
                height: '170px',
                borderRadius: '50%',
                border: '3px solid #00E5FF',
                boxShadow: '0 0 25px rgba(0, 229, 255, 0.5), inset 0 0 15px rgba(0,0,0,0.4)',
                pointerEvents: 'none',
                overflow: 'hidden',
                background: '#000',
                zIndex: 10
              }}
            >
              <div 
                style={{
                  width: `${loupePos.width * zoomLevel}px`,
                  height: `${loupePos.height * zoomLevel}px`,
                  backgroundImage: `url(${frameUrl})`,
                  backgroundSize: `${loupePos.width * zoomLevel}px ${loupePos.height * zoomLevel}px`,
                  backgroundPosition: `${-loupePos.x * zoomLevel + 85}px ${-loupePos.y * zoomLevel + 85}px`,
                  backgroundRepeat: 'no-repeat'
                }}
              />
              <div style={{
                position: 'absolute',
                bottom: '8px',
                left: '50%',
                transform: 'translateX(-50%)',
                background: 'rgba(0, 0, 0, 0.75)',
                color: '#00E5FF',
                fontSize: '10px',
                fontWeight: '700',
                padding: '2px 8px',
                borderRadius: '10px'
              }}>
                {zoomLevel}x Loupe
              </div>
            </div>
          )}

          {/* Info Badge */}
          <div style={{
            position: 'absolute',
            bottom: '16px',
            right: '16px',
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            padding: '8px 14px',
            borderRadius: '10px',
            fontSize: '11.5px',
            color: '#fff',
            display: 'flex',
            gap: '16px'
          }}>
            <span><b>Resolution:</b> 1024 × 768</span>
            <span><b>Dataset:</b> {currentDataset}</span>
            <span><b>Mode:</b> {useAnscombe ? 'Anscombe Stabilized' : 'Raw Micrograph'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
