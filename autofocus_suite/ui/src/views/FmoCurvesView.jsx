import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Compass, 
  BarChart3, 
  Layers, 
  Eye, 
  Check,
  TrendingUp,
  Sliders,
  Filter
} from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const FMO_COLORS = {
  m1_scharr: '#00C3F9',
  m2_brenner: '#40D4FF',
  m3_sml: '#30D158',
  m4_steerable: '#FF9F0A',
  m5_morph: '#FF453A',
  m6_wavelet: '#BF5AF2',
  m7_dct: '#FFD60A',
  m8_fft: '#64D2FF',
  m9_normvar: '#9A9B9E',
  m10_tensor: '#E81123'
};

export default function FmoCurvesView({ 
  currentDataset, 
  metadata, 
  theme 
}) {
  const [selectedVst, setSelectedVst] = useState('anscombe_unbiased');
  const [curveData, setCurveData] = useState(null);
  const [astigData, setAstigData] = useState(null);
  const [isNormalized, setIsNormalized] = useState(true);
  const [activeFmos, setActiveFmos] = useState({
    m1_scharr: true,
    m2_brenner: true,
    m3_sml: false,
    m4_steerable: false,
    m5_morph: false,
    m6_wavelet: true,
    m7_dct: false,
    m8_fft: false,
    m9_normvar: true,
    m10_tensor: true
  });
  const [fmoGroup, setFmoGroup] = useState('all');

  useEffect(() => {
    fetch(`/api/curves/${currentDataset}?vst=${selectedVst}`)
      .then(res => res.json())
      .then(data => setCurveData(data))
      .catch(err => console.error("Failed to load curves:", err));

    fetch(`/api/astigmatism/${currentDataset}`)
      .then(res => res.json())
      .then(data => setAstigData(data))
      .catch(err => console.error("Failed to load astigmatism:", err));
  }, [currentDataset, selectedVst]);

  const toggleFmo = (key) => {
    setActiveFmos(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const selectGroup = (group) => {
    setFmoGroup(group);
    if (group === 'all') {
      const all = {};
      Object.keys(FMO_COLORS).forEach(k => all[k] = true);
      setActiveFmos(all);
    } else if (group === 'spatial') {
      setActiveFmos({
        m1_scharr: true, m2_brenner: true, m3_sml: true, m4_steerable: true, m5_morph: true,
        m6_wavelet: false, m7_dct: false, m8_fft: false, m9_normvar: false, m10_tensor: false
      });
    } else if (group === 'transforms') {
      setActiveFmos({
        m1_scharr: false, m2_brenner: false, m3_sml: false, m4_steerable: false, m5_morph: false,
        m6_wavelet: true, m7_dct: true, m8_fft: true, m9_normvar: true, m10_tensor: true
      });
    }
  };

  const numFrames = curveData ? curveData.num_frames : 200;
  const labels = Array.from({ length: numFrames }, (_, i) => i);

  const datasets = [];
  if (curveData && curveData.curves) {
    Object.keys(curveData.curves).forEach(key => {
      if (!activeFmos[key]) return;
      const raw = curveData.curves[key];
      const maxVal = Math.max(...raw) || 1;
      const dataPoints = isNormalized ? raw.map(v => v / maxVal) : raw;

      datasets.push({
        label: metadata.fmos?.[key]?.name || key,
        data: dataPoints,
        borderColor: FMO_COLORS[key] || '#00C3F9',
        backgroundColor: 'transparent',
        borderWidth: key === 'm1_scharr' || key === 'm10_tensor' ? 2 : 1.25,
        pointRadius: 0,
        tension: 0.15
      });
    });
  }

  const multiChartData = { labels, datasets };

  const multiChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 150 },
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        backgroundColor: '#181819',
        titleColor: '#FFFFFF',
        bodyColor: '#9A9B9E',
        borderWidth: 1,
        borderColor: 'rgba(255, 255, 255, 0.1)',
        cornerRadius: 0
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
        min: isNormalized ? 0 : undefined,
        max: isNormalized ? 1.05 : undefined
      }
    }
  };

  const fmoKeys = Object.keys(FMO_COLORS);
  const psrData = {
    labels: fmoKeys.map(k => metadata.fmos?.[k]?.name?.split(' ')[0] || k),
    datasets: [{
      label: 'Peak Sharpness Ratio (PSR)',
      data: fmoKeys.map(k => curveData?.psr?.[k] || 0),
      backgroundColor: fmoKeys.map(k => FMO_COLORS[k]),
      borderRadius: 0,
      borderSkipped: false
    }]
  };

  const psrOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: '#6E7074', font: { size: 10 } }, grid: { display: false } },
      y: { ticks: { color: '#6E7074', font: { size: 10 } }, grid: { color: 'rgba(255, 255, 255, 0.04)' } }
    }
  };

  const astigChartData = {
    labels,
    datasets: [
      {
        label: 'A_xy(z) Axis Asymmetry',
        data: astigData?.A_xy_series || [],
        borderColor: '#00C3F9',
        borderWidth: 1.25,
        pointRadius: 0
      },
      {
        label: 'A_45(z) Diagonal Asymmetry',
        data: astigData?.A_45_series || [],
        borderColor: '#FF9F0A',
        borderWidth: 1.25,
        pointRadius: 0
      }
    ]
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', gap: '32px' }}>
      {/* Zone 2: Hero Header Zone */}
      <section className="matte-hero-zone">
        <div>
          <h1 className="matte-hero-title">
            10-FMO Focus Curves
          </h1>
          <p className="matte-hero-bio">
            Comparative focus response curves across 200 depth slices on {currentDataset}. Evaluates Full-Width at Half-Maximum (FWHM), peak unimodality, and stigmator asymmetry.
          </p>
        </div>

        {/* Action Cluster */}
        <div className="matte-action-cluster">
          <div className="matte-action-cluster-tag">
            SPECTRAL & SPATIAL KERNELS
          </div>
          <div className="matte-action-icons">
            <div className="matte-segment-bar">
              <button 
                className={`matte-segment-item ${fmoGroup === 'all' ? 'active' : ''}`}
                onClick={() => selectGroup('all')}
              >
                All 10
              </button>
              <button 
                className={`matte-segment-item ${fmoGroup === 'spatial' ? 'active' : ''}`}
                onClick={() => selectGroup('spatial')}
              >
                M1–M5 Spatial
              </button>
              <button 
                className={`matte-segment-item ${fmoGroup === 'transforms' ? 'active' : ''}`}
                onClick={() => selectGroup('transforms')}
              >
                M6–M10 Spectral
              </button>
            </div>

            <button 
              className="matte-btn-secondary"
              onClick={() => setIsNormalized(!isNormalized)}
              style={{ height: '28px', padding: '0 10px', fontSize: '11px' }}
            >
              {isNormalized ? 'Normalized [0, 1]' : 'Raw Scale'}
            </button>
          </div>
        </div>
      </section>

      {/* Main Focus Curves Canvas (0px Rectilinear Matte Card) */}
      <div className="matte-card">
        {/* VST Preconditioning Mode Bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          paddingBottom: '12px',
          borderBottom: '1px solid var(--border-subtle)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Variance Stabilization:
            </span>
            <div className="matte-segment-bar">
              <button 
                className={`matte-segment-item ${selectedVst === 'anscombe_unbiased' ? 'active' : ''}`}
                onClick={() => setSelectedVst('anscombe_unbiased')}
                title="Forward Anscombe + Mäkitalo-Foi exact unbiased inverse (eliminates low-count bias)"
              >
                Anscombe (Mäkitalo-Foi) [Rec]
              </button>
              <button 
                className={`matte-segment-item ${selectedVst === 'msvst' ? 'active' : ''}`}
                onClick={() => setSelectedVst('msvst')}
                title="Dyadic B3-spline à trous multi-scale variance stabilization (PSR 125)"
              >
                MSVST Multi-Scale
              </button>
              <button 
                className={`matte-segment-item ${selectedVst === 'freeman_tukey' ? 'active' : ''}`}
                onClick={() => setSelectedVst('freeman_tukey')}
                title="Freeman-Tukey count normalizer: y = √x + √(x+1)"
              >
                Freeman-Tukey
              </button>
              <button 
                className={`matte-segment-item ${selectedVst === 'anscombe_algebraic' ? 'active' : ''}`}
                onClick={() => setSelectedVst('anscombe_algebraic')}
                title="Direct algebraic inverse: (y/2)²-3/8 (introduces severe -0.25 count distortion)"
              >
                Anscombe (Algebraic Biased)
              </button>
              <button 
                className={`matte-segment-item ${selectedVst === 'none' ? 'active' : ''}`}
                onClick={() => setSelectedVst('none')}
                title="Raw unconditioned sensor counts"
              >
                Raw Counts (No VST)
              </button>
            </div>
          </div>

          <div style={{ fontSize: '11px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            {selectedVst === 'anscombe_unbiased' && (
              <span style={{ color: 'var(--accent-cyan)', fontWeight: '500' }}>
                ★ Golden Rule Active: Exact Unbiased Inverse eliminates low-count bias.
              </span>
            )}
            {selectedVst === 'anscombe_algebraic' && (
              <span style={{ color: '#FF453A', fontWeight: '500' }}>
                ⚠ Biased Baseline: Algebraic inverse ((y/2)²-3/8) incurs -0.25 count bias.
              </span>
            )}
            {selectedVst === 'msvst' && (
              <span style={{ color: 'var(--status-success)', fontWeight: '500' }}>
                ⚡ MSVST Active: Multiscale B3-spline boosts Peak Sharpness Ratio (PSR) up to 124.9.
              </span>
            )}
            {selectedVst === 'freeman_tukey' && (
              <span style={{ color: 'var(--text-secondary)' }}>
                ✓ Freeman-Tukey: Homoscedastic Poisson stabilization: Var(y) ≈ 1.
              </span>
            )}
            {selectedVst === 'none' && (
              <span style={{ color: 'var(--text-muted)' }}>
                ○ Raw Detector: Heteroscedastic electron shot noise active.
              </span>
            )}
          </div>
        </div>

        {/* FMO Toggle Swatches (Strict 0px geometry) */}
        <div style={{ 
          display: 'flex', 
          flexWrap: 'wrap', 
          gap: '8px', 
          padding: '12px 0', 
          borderBottom: '1px solid var(--border-subtle)' 
        }}>
          {Object.keys(FMO_COLORS).map(key => {
            const active = activeFmos[key];
            const meta = metadata.fmos?.[key];
            const color = FMO_COLORS[key];
            return (
              <button
                key={key}
                onClick={() => toggleFmo(key)}
                className="tabular-nums"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '5px 12px',
                  fontSize: '12px',
                  fontWeight: active ? '600' : '400',
                  border: `1px solid ${active ? color : 'var(--border-subtle)'}`,
                  background: active ? 'rgba(255, 255, 255, 0.05)' : 'transparent',
                  color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  transition: 'background 0.1s ease'
                }}
              >
                <span style={{ 
                  width: '8px', 
                  height: '8px', 
                  background: color,
                  display: 'inline-block'
                }} />
                <span>{meta?.name || key}</span>
                {curveData?.ground_truth_peaks?.[key] !== undefined && (
                  <span style={{ 
                    fontSize: '11px',
                    color: active ? 'var(--text-primary)' : 'var(--text-muted)',
                    marginLeft: '4px'
                  }}>
                    z*={curveData.ground_truth_peaks[key]}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Chart Viewport */}
        <div style={{ height: '380px', position: 'relative' }}>
          <Line data={multiChartData} options={multiChartOptions} />
        </div>
      </div>

      {/* Lower Diagnostics Split: PSR Prominence & Directional Astigmatism */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '48px' }}>
        {/* Peak Sharpness Ratio (PSR) Bar Chart */}
        <div className="matte-card">
          <div className="matte-section-h2" style={{ marginBottom: 0 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BarChart3 size={15} strokeWidth={1.25} color="var(--accent-cyan)" />
              Peak Sharpness Ratio (PSR) Prominence
            </span>
            <span className="mono-metric" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              (Φ_max - μ_tail) / σ_tail
            </span>
          </div>

          <div style={{ height: '220px', position: 'relative' }}>
            <Bar data={psrData} options={psrOptions} />
          </div>

          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '18px' }}>
            Higher PSR indicates a steep, noise-resistant focal peak. Wavelet (M6) and Scharr (M1) maintain high PSR even under heavy Poisson shot noise.
          </p>
        </div>

        {/* Free Directional Astigmatism Diagnostic */}
        <div className="matte-card">
          <div className="matte-section-h2" style={{ marginBottom: 0 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Compass size={15} strokeWidth={1.25} color="var(--status-warning)" />
              Directional Astigmatism Diagnostic
            </span>
            {astigData?.has_astigmatism ? (
              <span className="matte-badge matte-badge-amber">Astigmatism Detected</span>
            ) : (
              <span className="matte-badge matte-badge-green">Astigmatism Free</span>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '130px 1fr', gap: '20px', alignItems: 'center' }}>
            {/* Rectilinear Stigmator Vector Box (Strict 0px Geometry) */}
            <div style={{ 
              width: '130px', 
              height: '130px', 
              border: '1px solid var(--border-subtle)', 
              background: '#121214',
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              {/* Coordinate Grid Crosshairs */}
              <div style={{ position: 'absolute', width: '100%', height: '1px', background: 'rgba(255, 255, 255, 0.08)' }} />
              <div style={{ position: 'absolute', height: '100%', width: '1px', background: 'rgba(255, 255, 255, 0.08)' }} />
              
              <span style={{ position: 'absolute', top: '4px', fontSize: '9px', color: 'var(--text-muted)' }}>Y (0°)</span>
              <span style={{ position: 'absolute', right: '4px', fontSize: '9px', color: 'var(--text-muted)' }}>X (90°)</span>
              
              {/* Pointer Needle */}
              <div style={{
                position: 'absolute',
                width: '2px',
                height: '48px',
                background: 'var(--status-warning)',
                transformOrigin: 'bottom center',
                transform: `rotate(${astigData?.stigmator_angle_deg || 0}deg) translateY(-24px)`,
                transition: 'transform 0.4s ease'
              }} />
              <div style={{ width: '4px', height: '4px', background: 'var(--text-primary)', zIndex: 2 }} />
            </div>

            {/* Numerical Diagnostics in Tabular Format */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px' }} className="tabular-nums">
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '4px', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Horizontal Peak (z_x*):</span>
                <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>Frame {astigData?.zx_peak ?? 96}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '4px', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Vertical Peak (z_y*):</span>
                <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>Frame {astigData?.zy_peak ?? 96}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '4px', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Stigmator Error (|Δz*|):</span>
                <span style={{ fontWeight: '600', color: (astigData?.stigmator_error || 0) > 0 ? 'var(--status-warning)' : 'var(--status-success)' }}>
                  {astigData?.stigmator_error ?? 0} frames
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>True Gaussian Focus (z*):</span>
                <span style={{ fontWeight: '600', color: 'var(--accent-cyan)' }}>Frame {astigData?.z_true ?? '96.0'}</span>
              </div>
            </div>
          </div>

          <div style={{ height: '90px', position: 'relative' }}>
            <Line 
              data={astigChartData} 
              options={{ 
                responsive: true, 
                maintainAspectRatio: false, 
                plugins: { legend: { display: false } }, 
                scales: { 
                  x: { display: false }, 
                  y: { ticks: { font: { size: 9 }, color: '#6E7074' }, grid: { color: 'rgba(255, 255, 255, 0.04)' } } 
                } 
              }} 
            />
          </div>
        </div>
      </div>
    </div>
  );
}
