import React, { useState, useEffect } from 'react';
import { 
  Play, 
  RotateCcw, 
  ChevronLeft, 
  ChevronRight, 
  FolderOpen,
  Eye, 
  TrendingUp,
  Clock,
  Sparkles,
  Compass,
  Check
} from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function LiveStudio({ 
  currentDataset, 
  metadata,
  theme,
  onOpenPathModal
}) {
  const [searchMethod, setSearchMethod] = useState('s2_hybrid');
  const [fmo, setFmo] = useState('m1_scharr');
  const [useAnscombe, setUseAnscombe] = useState(false);
  const [topK, setTopK] = useState(3);
  const [isRunning, setIsRunning] = useState(false);

  const [searchResult, setSearchResult] = useState(null);
  const [currentStepIdx, setCurrentStepIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [groundTruthCurve, setGroundTruthCurve] = useState([]);
  const [gtPeak, setGtPeak] = useState(96);
  const [showMetadata, setShowMetadata] = useState(false);

  // Load ground truth curve for the dataset & FMO
  useEffect(() => {
    fetch(`/api/curves/${currentDataset}`)
      .then(res => res.json())
      .then(data => {
        if (data.curves && data.curves[fmo]) {
          setGroundTruthCurve(data.curves[fmo]);
        }
        if (data.ground_truth_peaks && data.ground_truth_peaks[fmo] !== undefined) {
          setGtPeak(data.ground_truth_peaks[fmo]);
        }
      })
      .catch(err => console.error("Could not load curves:", err));
  }, [currentDataset, fmo]);

  // Execute Search
  const runAutofocus = async () => {
    setIsRunning(true);
    setIsPlaying(false);
    try {
      const res = await fetch('/api/run-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset: currentDataset,
          fmo: fmo,
          search_method: searchMethod,
          top_k_rois: topK,
          use_anscombe: useAnscombe
        })
      });
      const data = await res.json();
      setSearchResult(data);
      if (data.history && data.history.length > 0) {
        setCurrentStepIdx(data.history.length - 1);
      }
    } catch (err) {
      console.error("Autofocus run failed:", err);
    } finally {
      setIsRunning(false);
    }
  };

  // Playback timer
  useEffect(() => {
    let timer = null;
    if (isPlaying && searchResult && searchResult.history) {
      timer = setInterval(() => {
        setCurrentStepIdx(prev => {
          if (prev >= searchResult.history.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 300);
    }
    return () => clearInterval(timer);
  }, [isPlaying, searchResult]);

  // Current frame being viewed
  const currentStep = searchResult && searchResult.history && searchResult.history[currentStepIdx];
  const viewedFrameIdx = currentStep ? currentStep.idx : (searchResult ? searchResult.discrete_peak : gtPeak);

  // Prepare chart data
  const totalFrames = groundTruthCurve.length || 200;
  const labels = Array.from({ length: totalFrames }, (_, i) => i);

  // Normalized reference curve
  const maxRefVal = groundTruthCurve.length > 0 ? Math.max(...groundTruthCurve) : 1;
  const normalizedRefCurve = groundTruthCurve.map(v => v / (maxRefVal || 1));

  // Trajectory points up to current step
  const trajectoryPoints = Array(totalFrames).fill(null);
  if (searchResult && searchResult.history) {
    searchResult.history.slice(0, currentStepIdx + 1).forEach(step => {
      trajectoryPoints[step.idx] = normalizedRefCurve[step.idx] || 0.5;
    });
  }

  const chartData = {
    labels,
    datasets: [
      {
        label: 'Focus Profile Curve Φ(z)',
        data: normalizedRefCurve,
        borderColor: 'rgba(255, 255, 255, 0.2)',
        borderWidth: 1.25,
        pointRadius: 0,
        fill: true,
        backgroundColor: 'rgba(255, 255, 255, 0.02)',
        tension: 0.15
      },
      {
        label: 'Search Probes',
        data: trajectoryPoints,
        borderColor: '#00C3F9',
        backgroundColor: '#00C3F9',
        borderWidth: 1.5,
        pointRadius: (ctx) => {
          const idx = ctx.dataIndex;
          if (currentStep && currentStep.idx === idx) return 6;
          return ctx.raw !== null ? 3.5 : 0;
        },
        pointHoverRadius: 6,
        pointBackgroundColor: (ctx) => {
          const idx = ctx.dataIndex;
          if (currentStep && currentStep.idx === idx) return '#00C3F9';
          if (searchResult && idx === searchResult.discrete_peak) return '#107C41';
          return '#FFFFFF';
        },
        showLine: true
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 150 },
    plugins: {
      legend: {
        display: true,
        labels: {
          color: '#9A9B9E',
          font: { size: 11, family: 'Segoe UI' },
          boxWidth: 12
        }
      },
      tooltip: {
        backgroundColor: 'rgba(24, 24, 25, 0.95)',
        titleColor: '#FFFFFF',
        bodyColor: '#9A9B9E',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        callbacks: {
          label: (ctx) => `Frame ${ctx.dataIndex}: ${(ctx.raw * 100).toFixed(1)}% score`
        }
      }
    },
    scales: {
      x: {
        grid: { color: 'rgba(255, 255, 255, 0.04)' },
        ticks: { color: '#6E7074', font: { size: 10 } }
      },
      y: {
        grid: { color: 'rgba(255, 255, 255, 0.04)' },
        ticks: { color: '#6E7074', font: { size: 10 } },
        min: 0,
        max: 1.05
      }
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
      {/* ------------------------------------------------------------- */}
      {/* ZONE 2: HERO HEADER ZONE (Section 4.2)                        */}
      {/* ------------------------------------------------------------- */}
      <section className="matte-hero-zone">
        <div>
          {/* H1 Hero Title (42px bold, -0.02em tracking) */}
          <h1 className="matte-hero-title">
            {currentDataset}
          </h1>

          {/* Multi-line Description / Bio Copy */}
          <p className="matte-hero-bio">
            Scanning Electron Microscopy focal stack across 200 depth slices. Evaluates 10 Focus Measure Operators and 4 sub-linear search schemes with Gaussian log-quadratic sub-frame peak interpolation.
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px' }}>
            <button 
              className="matte-link-cyan"
              onClick={() => setShowMetadata(!showMetadata)}
            >
              {showMetadata ? 'HIDE METADATA' : 'MORE METADATA'}
            </button>
            {showMetadata && (
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }} className="mono-metric">
                Target z*={gtPeak} • PSF Gaussian Fit • Top-K={topK} ROIs
              </span>
            )}
          </div>
        </div>

        {/* Header Action Cluster (Right Side) */}
        <div className="matte-action-cluster">
          <div className="matte-action-cluster-tag">
            SEM / SCANNING ELECTRON MICROSCOPY
          </div>
          
          <div className="matte-action-icons">
            {/* Wireframe Run Autofocus (Play) */}
            <button 
              className="matte-wireframe-btn"
              onClick={runAutofocus}
              disabled={isRunning}
              title={isRunning ? "Optimizing..." : "Execute Autofocus Sweep"}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}
            >
              {isRunning ? <Clock size={16} strokeWidth={1.25} className="animate-spin" /> : <Play size={16} strokeWidth={1.25} />}
              <span>{isRunning ? 'Optimizing' : 'Run'}</span>
            </button>

            {/* Wireframe Reset */}
            <button 
              className="matte-wireframe-btn"
              onClick={() => {
                setSearchResult(null);
                setCurrentStepIdx(0);
              }}
              title="Reset Search State"
            >
              <RotateCcw size={16} strokeWidth={1.25} />
            </button>

            {/* Wireframe Folder Open */}
            {onOpenPathModal && (
              <button 
                className="matte-wireframe-btn"
                onClick={onOpenPathModal}
                title="Select Datasets Directory"
              >
                <FolderOpen size={16} strokeWidth={1.25} />
              </button>
            )}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* ZONE 3: LOWER SPLIT WORKSPACE (Section 4.3, 48px gutter)       */}
      {/* ------------------------------------------------------------- */}
      <div className="matte-split-workspace">
        {/* Primary Content Column (Left, Fluid 65%-70%) */}
        <div className="matte-primary-column">
          {/* Module 1: In Library — Micrograph Inspection */}
          <div>
            <div className="matte-section-h2">
              <span>In Library — Micrograph Inspection</span>
              <span className="mono-metric" style={{ fontSize: '12px', fontWeight: '400', color: viewedFrameIdx === gtPeak ? 'var(--status-success)' : 'var(--text-muted)' }}>
                Frame z = {viewedFrameIdx} / {totalFrames - 1} {viewedFrameIdx === gtPeak ? '(True Peak)' : ''}
              </span>
            </div>

            {/* Strict 0px Rectilinear Micrograph Viewport */}
            <div style={{ 
              position: 'relative', 
              width: '100%', 
              height: '380px', 
              background: '#0E0E10', 
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden'
            }}>
              <img 
                src={`/api/frame/${currentDataset}/${viewedFrameIdx}?overlay_rois=true&top_k=${topK}&anscombe=${useAnscombe}`}
                alt={`Micrograph Frame ${viewedFrameIdx}`}
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />

              {/* Minimal Telemetry Overlay */}
              <div style={{
                position: 'absolute',
                bottom: '10px',
                left: '10px',
                background: 'rgba(24, 24, 25, 0.88)',
                padding: '4px 10px',
                border: '1px solid var(--border-subtle)',
                fontSize: '11px',
                color: 'var(--text-secondary)',
                display: 'flex',
                gap: '14px'
              }} className="tabular-nums">
                <span><b>Slice:</b> {viewedFrameIdx}</span>
                <span><b>ROIs:</b> Top-{topK} Locked</span>
                <span><b>Anscombe:</b> {useAnscombe ? 'On' : 'Off'}</span>
                <span><b>Stage:</b> {currentStep ? currentStep.stage : 'Idle'}</span>
              </div>
            </div>

            {/* Trajectory Playback Scrubber (Custom 2px track slider) */}
            {searchResult && searchResult.history && (
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '16px', 
                padding: '8px 0', 
                marginTop: '4px' 
              }}>
                <button 
                  className="matte-wireframe-btn"
                  onClick={() => setIsPlaying(!isPlaying)}
                  style={{ width: '28px', height: '28px' }}
                >
                  <Play size={14} strokeWidth={1.25} />
                </button>

                <button 
                  className="matte-wireframe-btn"
                  onClick={() => setCurrentStepIdx(Math.max(0, currentStepIdx - 1))}
                  disabled={currentStepIdx === 0}
                  style={{ width: '24px', height: '24px', opacity: currentStepIdx === 0 ? 0.3 : 1 }}
                >
                  <ChevronLeft size={14} strokeWidth={1.25} />
                </button>

                <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '12px' }}>
                  {/* Adjustment Slider: 2px track, 3px x 14px thumb */}
                  <input 
                    type="range"
                    min="0"
                    max={searchResult.history.length - 1}
                    value={currentStepIdx}
                    onChange={(e) => setCurrentStepIdx(parseInt(e.target.value))}
                    className="matte-slider"
                  />
                  <span className="mono-metric" style={{ fontSize: '11.5px', color: 'var(--text-muted)', minWidth: '75px', textAlign: 'right' }}>
                    Step {currentStepIdx + 1} / {searchResult.history.length}
                  </span>
                </div>

                <button 
                  className="matte-wireframe-btn"
                  onClick={() => setCurrentStepIdx(Math.min(searchResult.history.length - 1, currentStepIdx + 1))}
                  disabled={currentStepIdx === searchResult.history.length - 1}
                  style={{ width: '24px', height: '24px', opacity: currentStepIdx === searchResult.history.length - 1 ? 0.3 : 1 }}
                >
                  <ChevronRight size={14} strokeWidth={1.25} />
                </button>
              </div>
            )}
          </div>

          {/* Module 2: Focus Profile Curve & Search Probes */}
          <div>
            <div className="matte-section-h2">
              <span>Focus Profile Curve & Trajectory</span>
              <span className="mono-metric" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Peak Target: Frame {gtPeak}
              </span>
            </div>
            
            <div style={{ height: '220px', width: '100%', position: 'relative' }}>
              <Line data={chartData} options={chartOptions} />
            </div>
          </div>

          {/* Module 3: Numbered Table Rows (Section 4.3 & 6.1) */}
          {/* Zero horizontal divider lines, vertical whitespace separation */}
          {searchResult && searchResult.history && (
            <div>
              <div className="matte-section-h2">
                <span>Probe Iteration Log</span>
                <span className="mono-metric" style={{ fontSize: '11px', color: 'var(--accent-cyan)' }}>
                  {searchResult.frames_read} reads ({(100 - searchResult.frames_read / 1.99).toFixed(1)}% cut)
                </span>
              </div>

              {(() => {
                const maxHistScore = Math.max(...searchResult.history.map(s => s.score || 0), 1e-6);
                return (
                  <table className="matte-table tabular-nums">
                    <tbody>
                      {searchResult.history.map((step, idx) => {
                        const isActive = currentStepIdx === idx;
                        const pct = ((step.score / maxHistScore) * 100).toFixed(0);
                        return (
                          <tr 
                            key={idx}
                            onClick={() => setCurrentStepIdx(idx)}
                            className={`matte-table-row ${isActive ? 'active' : ''}`}
                          >
                            <td className="matte-table-index">
                              {idx + 1}
                            </td>
                            <td className="matte-table-primary">
                              Frame {step.idx}
                            </td>
                            <td className="matte-table-secondary">
                              {step.stage}
                            </td>
                            <td className="matte-table-value" style={{ color: step.idx === gtPeak ? 'var(--status-success)' : 'inherit' }}>
                              {pct}% score
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                );
              })()}
            </div>
          )}
        </div>

        {/* ------------------------------------------------------------- */}
        {/* RIGHT CONTEXT RAIL (Section 4.3, Fixed 290px)                  */}
        {/* 64x64 Square Preview + Title/Subtitle Stack                   */}
        {/* ------------------------------------------------------------- */}
        <aside className="matte-context-rail">
          {/* Section Header */}
          <div className="matte-section-h2">
            <span>Algorithm Presets</span>
          </div>

          {/* Stacked 64x64 Media / Preset Cards */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Preset 1: Universal Champion */}
            <button 
              className={`matte-context-item ${searchMethod === 's2_hybrid' && fmo === 'm1_scharr' ? 'active' : ''}`}
              onClick={() => {
                setSearchMethod('s2_hybrid');
                setFmo('m1_scharr');
                setUseAnscombe(false);
              }}
            >
              <img 
                src={`/api/frame/${currentDataset}/${gtPeak}?overlay_rois=false`} 
                alt="S2 Scharr" 
                className="matte-context-thumb"
              />
              <div className="matte-context-meta">
                <span className="matte-context-title">S2: Hybrid + M1 Scharr</span>
                <span className="matte-context-subtitle">100% Zero-Error • 28f • 30.9ms</span>
              </div>
            </button>

            {/* Preset 2: High-Speed Scout */}
            <button 
              className={`matte-context-item ${searchMethod === 's1_fibonacci' && fmo === 'm9_normvar' ? 'active' : ''}`}
              onClick={() => {
                setSearchMethod('s1_fibonacci');
                setFmo('m9_normvar');
                setUseAnscombe(false);
              }}
            >
              <div className="matte-context-thumb" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Sparkles size={24} strokeWidth={1.25} color="var(--accent-cyan)" />
              </div>
              <div className="matte-context-meta">
                <span className="matte-context-title">S1: Fibonacci + M9</span>
                <span className="matte-context-subtitle">12 frames read • 6.9ms Scout</span>
              </div>
            </button>

            {/* Preset 3: Extreme Noise Cryo-EM */}
            <button 
              className={`matte-context-item ${searchMethod === 's2_hybrid' && fmo === 'm10_tensor' ? 'active' : ''}`}
              onClick={() => {
                setSearchMethod('s2_hybrid');
                setFmo('m10_tensor');
                setUseAnscombe(true);
              }}
            >
              <div className="matte-context-thumb" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Eye size={24} strokeWidth={1.25} color="var(--status-warning)" />
              </div>
              <div className="matte-context-meta">
                <span className="matte-context-title">S2: Hybrid + M10 Tensor</span>
                <span className="matte-context-subtitle">Anscombe Poisson • ±0.027 Δz</span>
              </div>
            </button>

            {/* Preset 4: Batched Camera SDKs */}
            <button 
              className={`matte-context-item ${searchMethod === 's4_speculative' ? 'active' : ''}`}
              onClick={() => {
                setSearchMethod('s4_speculative');
                setFmo('m1_scharr');
                setUseAnscombe(false);
              }}
            >
              <div className="matte-context-thumb" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <TrendingUp size={24} strokeWidth={1.25} color="#8764B8" />
              </div>
              <div className="matte-context-meta">
                <span className="matte-context-title">S4: Speculative Parallel</span>
                <span className="matte-context-subtitle">2-burst I/O batch • 23f</span>
              </div>
            </button>
          </div>

          {/* Parameters Group (Section 6.2) */}
          <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div className="matte-group-header">
              <span>PARAMETER CONTROLS</span>
            </div>

            {/* Search Strategy */}
            <div>
              <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Search Strategy
              </label>
              <select 
                className="matte-select" 
                style={{ width: '100%' }}
                value={searchMethod}
                onChange={(e) => setSearchMethod(e.target.value)}
              >
                <option value="s1_fibonacci">S1 — Fibonacci Lattice (~12 reads)</option>
                <option value="s2_hybrid">S2 — Hybrid Coarse-Fine (Universal)</option>
                <option value="s3_pyramid">S3 — Pyramid Bracket (Decimation)</option>
                <option value="s4_speculative">S4 — Speculative (2 Batches)</option>
                <option value="baseline_global">Global Scan (200 frames baseline)</option>
              </select>
            </div>

            {/* Focus Measure Operator */}
            <div>
              <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Focus Measure Operator
              </label>
              <select 
                className="matte-select" 
                style={{ width: '100%' }}
                value={fmo}
                onChange={(e) => setFmo(e.target.value)}
              >
                <option value="m1_scharr">M1: Scharr-Tenengrad (Universal)</option>
                <option value="m2_brenner">M2: Denoised Brenner (Fastest)</option>
                <option value="m3_sml">M3: Modified Laplacian (SML)</option>
                <option value="m4_steerable">M4: Steerable G1 (Orientation)</option>
                <option value="m5_morph">M5: Top-Hat Morph (Spikes)</option>
                <option value="m6_wavelet">M6: 2D Haar Wavelet (PSR)</option>
                <option value="m7_dct">M7: DCT Mid-Band AC</option>
                <option value="m8_fft">M8: Fourier Radial CTF</option>
                <option value="m9_normvar">M9: Normalized Variance (Wide)</option>
                <option value="m10_tensor">M10: Structure Tensor (Heavy Noise)</option>
              </select>
            </div>

            {/* Anscombe Stabilization */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 0' }}>
              <div>
                <span style={{ fontSize: '12px', fontWeight: '500', display: 'block', color: 'var(--text-primary)' }}>Anscombe Stabilization</span>
                <span style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>Poisson 2·√(I+3/8) filter</span>
              </div>
              <input 
                type="checkbox" 
                checked={useAnscombe}
                onChange={(e) => setUseAnscombe(e.target.checked)}
                style={{ width: '14px', height: '14px', accentColor: 'var(--accent-cyan)', cursor: 'pointer' }}
              />
            </div>

            {/* Top-K ROI Zones Slider */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '2px' }}>
                <span>Dynamic ROI Zones</span>
                <span className="mono-metric" style={{ color: 'var(--accent-cyan)' }}>Top-K = {topK}</span>
              </div>
              <input 
                type="range"
                min="1"
                max="5"
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value))}
                className="matte-slider"
              />
            </div>
          </div>

          {/* Stigmator Telemetry Card */}
          <div style={{ marginTop: '12px', padding: '12px', background: '#1C1D20', border: '1px solid var(--border-card)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <Compass size={14} strokeWidth={1.25} color="var(--accent-cyan)" />
              <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)' }}>Lens Astigmatism</span>
            </div>
            <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }} className="tabular-nums">
              <div>Status: <b>Aligned</b></div>
              <div>True Plane: <b>z* = {gtPeak}.0</b></div>
              <div>Asymmetry Error: <b>0.0 frames</b></div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
