import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Compass, 
  BarChart3, 
  Layers, 
  Eye, 
  CheckCircle2, 
  AlertCircle 
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
  m1_scharr: '#0A84FF',
  m2_brenner: '#00E5FF',
  m3_sml: '#30D158',
  m4_steerable: '#FF9F0A',
  m5_morph: '#FF375F',
  m6_wavelet: '#BF5AF2',
  m7_dct: '#FFD60A',
  m8_fft: '#64D2FF',
  m9_normvar: '#AC8E68',
  m10_tensor: '#FF453A'
};

export default function FmoCurvesView({ 
  currentDataset, 
  metadata, 
  theme 
}) {
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
  const [fmoGroup, setFmoGroup] = useState('all'); // 'all', 'spatial', 'transforms'

  // Fetch Curves & Astigmatism
  useEffect(() => {
    fetch(`/api/curves/${currentDataset}`)
      .then(res => res.json())
      .then(data => setCurveData(data))
      .catch(err => console.error("Failed to load curves:", err));

    fetch(`/api/astigmatism/${currentDataset}`)
      .then(res => res.json())
      .then(data => setAstigData(data))
      .catch(err => console.error("Failed to load astigmatism:", err));
  }, [currentDataset]);

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

  // Build Multi-Line Chart Data
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
        borderColor: FMO_COLORS[key] || '#0A84FF',
        backgroundColor: 'transparent',
        borderWidth: key === 'm1_scharr' || key === 'm10_tensor' ? 2.5 : 1.5,
        pointRadius: 0,
        tension: 0.15
      });
    });
  }

  const multiChartData = { labels, datasets };

  const multiChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        backgroundColor: theme === 'dark' ? 'rgba(20, 22, 28, 0.95)' : 'rgba(255, 255, 255, 0.95)',
        titleColor: theme === 'dark' ? '#fff' : '#000',
        bodyColor: theme === 'dark' ? '#9898A0' : '#444',
        borderWidth: 1,
        borderColor: 'rgba(255, 255, 255, 0.1)'
      }
    },
    scales: {
      x: {
        grid: { color: theme === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)' },
        ticks: { color: theme === 'dark' ? '#63636E' : '#A1A1A6', font: { size: 10 } }
      },
      y: {
        grid: { color: theme === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)' },
        ticks: { color: theme === 'dark' ? '#63636E' : '#A1A1A6', font: { size: 10 } },
        min: isNormalized ? 0 : undefined,
        max: isNormalized ? 1.05 : undefined
      }
    }
  };

  // Bar Chart Data for PSR
  const fmoKeys = Object.keys(FMO_COLORS);
  const psrData = {
    labels: fmoKeys.map(k => metadata.fmos?.[k]?.name?.split(' ')[0] || k),
    datasets: [{
      label: 'Peak Sharpness Ratio (PSR)',
      data: fmoKeys.map(k => curveData?.psr?.[k] || 0),
      backgroundColor: fmoKeys.map(k => FMO_COLORS[k]),
      borderRadius: 6
    }]
  };

  const psrOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: theme === 'dark' ? '#63636E' : '#A1A1A6', font: { size: 10 } }, grid: { display: false } },
      y: { ticks: { color: theme === 'dark' ? '#63636E' : '#A1A1A6', font: { size: 10 } }, grid: { color: 'rgba(255, 255, 255, 0.05)' } }
    }
  };

  // Astigmatism Chart
  const astigChartData = {
    labels,
    datasets: [
      {
        label: 'A_xy(z) Axis Asymmetry',
        data: astigData?.A_xy_series || [],
        borderColor: '#0A84FF',
        borderWidth: 1.5,
        pointRadius: 0
      },
      {
        label: 'A_45(z) Diagonal Asymmetry',
        data: astigData?.A_45_series || [],
        borderColor: '#FF9F0A',
        borderWidth: 1.5,
        pointRadius: 0
      }
    ]
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header Card */}
      <div className="glass-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 22px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '38px', height: '38px', borderRadius: '10px', background: 'rgba(191, 90, 242, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Activity size={20} color="#BF5AF2" />
          </div>
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: '600' }}>10-FMO Focus Curves & Astigmatism Diagnostics</h2>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Evaluate Full-Width at Half-Maximum (FWHM), noise immunity, and directional stigmator asymmetry
            </p>
          </div>
        </div>

        {/* View mode toggle */}
        <div style={{ display: 'flex', gap: '10px' }}>
          <div className="segmented-pill-bar">
            <button 
              className={`segmented-pill-item ${fmoGroup === 'all' ? 'active' : ''}`}
              onClick={() => selectGroup('all')}
            >
              All 10 FMOs
            </button>
            <button 
              className={`segmented-pill-item ${fmoGroup === 'spatial' ? 'active' : ''}`}
              onClick={() => selectGroup('spatial')}
            >
              M1-M5 Spatial
            </button>
            <button 
              className={`segmented-pill-item ${fmoGroup === 'transforms' ? 'active' : ''}`}
              onClick={() => selectGroup('transforms')}
            >
              M6-M10 Tensor/Spectral
            </button>
          </div>

          <button 
            className={`btn-macos-secondary ${isNormalized ? 'active' : ''}`}
            onClick={() => setIsNormalized(!isNormalized)}
          >
            {isNormalized ? 'Normalized [0, 1]' : 'Raw Scale'}
          </button>
        </div>
      </div>

      {/* Main Focus Curves Canvas */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', paddingBottom: '10px', borderBottom: '1px solid var(--border-subtle)' }}>
          {Object.keys(FMO_COLORS).map(key => {
            const active = activeFmos[key];
            const meta = metadata.fmos?.[key];
            const color = FMO_COLORS[key];
            return (
              <button
                key={key}
                onClick={() => toggleFmo(key)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '7px',
                  padding: '6px 14px',
                  borderRadius: '20px',
                  fontSize: '12px',
                  fontWeight: active ? '600' : '500',
                  border: `1.5px solid ${active ? color : 'var(--border-subtle)'}`,
                  background: active 
                    ? (theme === 'light' ? `${color}18` : `${color}25`) 
                    : (theme === 'light' ? 'rgba(0, 0, 0, 0.03)' : 'rgba(255, 255, 255, 0.03)'),
                  color: active 
                    ? (theme === 'light' ? '#111827' : '#F9FAFB') 
                    : 'var(--text-secondary)',
                  boxShadow: active ? `0 2px 8px ${color}33` : 'none',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <span style={{ 
                  width: '9px', 
                  height: '9px', 
                  borderRadius: '50%', 
                  background: color,
                  boxShadow: active ? `0 0 8px ${color}` : 'none'
                }} />
                <span style={{
                  color: active 
                    ? (theme === 'light' ? '#111827' : '#F9FAFB') 
                    : 'var(--text-secondary)'
                }}>
                  {meta?.name || key}
                </span>
                {curveData?.ground_truth_peaks?.[key] !== undefined && (
                  <span style={{ 
                    fontSize: '10.5px',
                    fontWeight: '700',
                    padding: '1px 6px',
                    borderRadius: '8px',
                    background: active 
                      ? (theme === 'light' ? `${color}25` : `${color}40`) 
                      : (theme === 'light' ? 'rgba(0, 0, 0, 0.06)' : 'rgba(255, 255, 255, 0.08)'),
                    color: active 
                      ? (theme === 'light' ? '#111827' : '#FFFFFF') 
                      : 'var(--text-tertiary)'
                  }}>
                    {curveData.ground_truth_peaks[key]}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        <div style={{ height: '360px', position: 'relative' }}>
          <Line data={multiChartData} options={multiChartOptions} />
        </div>
      </div>

      {/* 2-Column: Peak Sharpness vs Astigmatism Diagnostic */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Peak Sharpness Ratio (PSR) Bar Chart */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '13px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <BarChart3 size={15} color="#30D158" />
              Peak Sharpness Ratio (PSR) Prominence
            </span>
            <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
              (Φ_max - μ_tail) / σ_tail
            </span>
          </div>
          <div style={{ height: '220px', position: 'relative' }}>
            <Bar data={psrData} options={psrOptions} />
          </div>
          <p style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            Higher PSR indicates a razor-sharp peak with zero risk of false bracketing on noisy micrographs.
          </p>
        </div>

        {/* Bonus Astigmatism Detection Compass Card */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '13px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Compass size={15} color="#FF9F0A" />
              Free Astigmatism Diagnostic (Section 3 Bonus)
            </span>
            {astigData?.has_astigmatism ? (
              <span className="badge-pill badge-amber">Astigmatism Detected</span>
            ) : (
              <span className="badge-pill badge-green">Astigmatism Free</span>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '130px 1fr', gap: '16px', alignItems: 'center' }}>
            {/* Polar Compass Widget */}
            <div style={{ 
              width: '130px', 
              height: '130px', 
              borderRadius: '50%', 
              border: '2px dashed var(--border-subtle)', 
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'radial-gradient(circle, rgba(255, 159, 10, 0.1) 0%, transparent 70%)'
            }}>
              <span style={{ position: 'absolute', top: '4px', fontSize: '9px', color: 'var(--text-tertiary)' }}>0° Y</span>
              <span style={{ position: 'absolute', right: '4px', fontSize: '9px', color: 'var(--text-tertiary)' }}>90° X</span>
              
              {/* Pointer Needle */}
              <div style={{
                position: 'absolute',
                width: '4px',
                height: '45px',
                background: 'linear-gradient(to top, transparent, #FF9F0A)',
                borderRadius: '4px',
                transformOrigin: 'bottom center',
                transform: `rotate(${astigData?.stigmator_angle_deg || 0}deg) translateY(-22px)`,
                transition: 'transform 0.5s ease'
              }} />
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#FF9F0A' }} />
            </div>

            {/* Numerical Diagnostics */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Horizontal Peak (z_x*):</span>
                <b>Frame {astigData?.zx_peak || '96'}</b>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Vertical Peak (z_y*):</span>
                <b>Frame {astigData?.zy_peak || '96'}</b>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Stigmator Error (|z_x* - z_y*|):</span>
                <b style={{ color: (astigData?.stigmator_error || 0) > 0 ? '#FF9F0A' : '#30D158' }}>
                  {astigData?.stigmator_error || 0} frames
                </b>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>True Gaussian Focus (z_true*):</span>
                <b style={{ color: '#0A84FF' }}>Frame {astigData?.z_true || '96.0'}</b>
              </div>
            </div>
          </div>

          <div style={{ height: '90px', position: 'relative' }}>
            <Line data={astigChartData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { ticks: { font: { size: 9 } } } } }} />
          </div>
        </div>
      </div>
    </div>
  );
}
