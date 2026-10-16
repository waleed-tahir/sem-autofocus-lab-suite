import React, { useState, useRef } from 'react';
import { 
  ZoomIn, 
  Layers, 
  Eye, 
  Maximize2, 
  Sliders, 
  Sparkles,
  ChevronLeft,
  ChevronRight
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
  const [loupePos, setLoupePos] = useState({ x: 0, y: 0, width: 0, height: 0 });

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
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', gap: '32px' }}>
      {/* Zone 2: Hero Header Zone */}
      <section className="matte-hero-zone">
        <div>
          <h1 className="matte-hero-title">
            Loupe Inspector (4x)
          </h1>
          <p className="matte-hero-bio">
            High-magnification pixel-level scrutiny of SEM specimen edges, beam shot Poisson noise, and Anscombe square-root stabilization across focal slices.
          </p>
        </div>

        {/* Action Cluster: Preset Focal Jumps */}
        <div className="matte-action-cluster">
          <div className="matte-action-cluster-tag">
            RAPID FOCAL PLANE PRESETS
          </div>
          <div className="matte-action-icons">
            <button 
              className="matte-btn-secondary"
              onClick={() => setFrameIdx(30)}
              style={{ height: '28px', padding: '0 10px', fontSize: '11px' }}
            >
              Under-Focus (z=30)
            </button>
            <button 
              className="matte-btn-secondary"
              onClick={() => setFrameIdx(75)}
              style={{ height: '28px', padding: '0 10px', fontSize: '11px' }}
            >
              Near-Focus (z=75)
            </button>
            <button 
              className="matte-btn-primary"
              onClick={() => setFrameIdx(96)}
              style={{ height: '28px', padding: '0 10px', fontSize: '11px' }}
            >
              ★ True Peak (z=96)
            </button>
            <button 
              className="matte-btn-secondary"
              onClick={() => setFrameIdx(160)}
              style={{ height: '28px', padding: '0 10px', fontSize: '11px' }}
            >
              Over-Focus (z=160)
            </button>
          </div>
        </div>
      </section>

      {/* Main Inspection Canvas Card (0px Rectilinear Matte Card) */}
      <div className="matte-card">
        {/* Controls Toolbar */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between', 
          flexWrap: 'wrap', 
          gap: '16px', 
          borderBottom: '1px solid var(--border-subtle)', 
          paddingBottom: '14px' 
        }}>
          {/* Continuous Z-Slider (Section 6.2 custom slider: 2px track, 3x14px thumb) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1, minWidth: '320px' }}>
            <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)' }}>
              Focal Slice:
            </span>
            <input 
              type="range"
              min="0"
              max={totalFrames - 1}
              value={frameIdx}
              onChange={(e) => setFrameIdx(parseInt(e.target.value))}
              className="matte-slider"
            />
            <span className="mono-metric" style={{ fontSize: '13px', fontWeight: '600', minWidth: '90px', color: frameIdx === 96 ? 'var(--status-success)' : 'var(--text-primary)' }}>
              z = {frameIdx} {frameIdx === 96 && '★ Peak'}
            </span>
          </div>

          {/* Toggles */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', cursor: 'pointer', color: 'var(--text-secondary)' }}>
              <input 
                type="checkbox"
                checked={useAnscombe}
                onChange={(e) => setUseAnscombe(e.target.checked)}
                style={{ width: '14px', height: '14px', accentColor: 'var(--accent-cyan)' }}
              />
              <span>Anscombe Stabilized</span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', cursor: 'pointer', color: 'var(--text-secondary)' }}>
              <input 
                type="checkbox"
                checked={showRois}
                onChange={(e) => setShowRois(e.target.checked)}
                style={{ width: '14px', height: '14px', accentColor: 'var(--accent-cyan)' }}
              />
              <span>Dynamic 9-Zone ROIs</span>
            </label>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Zoom:</span>
              <select 
                className="matte-select"
                style={{ padding: '3px 20px 3px 8px', fontSize: '11.5px' }}
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

        {/* Micrograph Canvas with Interactive Rectilinear Loupe (Strict 0px Geometry) */}
        <div 
          style={{ 
            position: 'relative', 
            width: '100%', 
            height: '540px', 
            background: '#0E0E10', 
            border: '1px solid var(--border-subtle)',
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'crosshair'
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

          {/* Floating Rectilinear Magnifying Loupe Viewport (Strict 0px Radius, 1px Border) */}
          {loupeActive && imgRef.current && (
            <div 
              style={{
                position: 'absolute',
                top: `${loupePos.y - 90}px`,
                left: `${loupePos.x - 90}px`,
                width: '180px',
                height: '180px',
                border: '1px solid var(--accent-cyan)',
                pointerEvents: 'none',
                overflow: 'hidden',
                background: '#0E0E10',
                zIndex: 10
              }}
            >
              <div 
                style={{
                  width: `${loupePos.width * zoomLevel}px`,
                  height: `${loupePos.height * zoomLevel}px`,
                  backgroundImage: `url(${frameUrl})`,
                  backgroundSize: `${loupePos.width * zoomLevel}px ${loupePos.height * zoomLevel}px`,
                  backgroundPosition: `${-loupePos.x * zoomLevel + 90}px ${-loupePos.y * zoomLevel + 90}px`,
                  backgroundRepeat: 'no-repeat'
                }}
              />
              <div style={{
                position: 'absolute',
                bottom: '6px',
                left: '6px',
                background: 'rgba(24, 24, 25, 0.92)',
                color: 'var(--accent-cyan)',
                fontSize: '10px',
                fontWeight: '600',
                padding: '2px 6px',
                border: '1px solid var(--border-subtle)'
              }} className="tabular-nums">
                {zoomLevel}x LOUPE
              </div>
            </div>
          )}

          {/* Minimal Telemetry Badge (Strict 0px Geometry) */}
          <div style={{
            position: 'absolute',
            bottom: '12px',
            right: '12px',
            background: 'rgba(24, 24, 25, 0.92)',
            border: '1px solid var(--border-subtle)',
            padding: '6px 12px',
            fontSize: '11px',
            color: 'var(--text-secondary)',
            display: 'flex',
            gap: '16px'
          }} className="tabular-nums">
            <span><b>Resolution:</b> 1024 × 768</span>
            <span><b>Dataset:</b> {currentDataset}</span>
            <span><b>Mode:</b> {useAnscombe ? 'Anscombe Stabilized' : 'Raw Micrograph'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
