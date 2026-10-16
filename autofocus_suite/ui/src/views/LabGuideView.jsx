import React from 'react';
import { 
  BookOpen, 
  Cpu, 
  GitBranch, 
  Layers, 
  Sparkles,
  Compass, 
  Check
} from 'lucide-react';

export default function LabGuideView({ metadata }) {
  const fmos = metadata?.fmos || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', gap: '32px' }}>
      {/* Zone 2: Hero Header Zone */}
      <section className="matte-hero-zone">
        <div>
          <h1 className="matte-hero-title">
            Architecture Guide
          </h1>
          <p className="matte-hero-bio">
            Complete technical specification for the 5-stage electron microscope autofocus architecture, mathematical operators, and noise regime decision trees.
          </p>
        </div>

        {/* Action Cluster */}
        <div className="matte-action-cluster">
          <div className="matte-action-cluster-tag">
            MICROSCOPY PIPELINE ARCHITECTURE
          </div>
          <div className="matte-action-icons">
            <span className="matte-badge matte-badge-cyan">
              HAL3 / CAMERA2 COMPLIANT
            </span>
          </div>
        </div>
      </section>

      {/* 5-Stage Architecture Pipeline (Strict 0px Geometry with Micro-Accent Tops) */}
      <div>
        <div className="matte-section-h2">
          <span>Figure 1.1 — Five-Stage Sub-Frame Autofocus Pipeline</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '16px' }}>
          {/* Stage 1 */}
          <div className="matte-card" style={{ borderTop: '3px solid var(--accent-cyan)', gap: '8px' }}>
            <span style={{ fontSize: '10px', fontWeight: '700', color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              STAGE 01
            </span>
            <h3 className="matte-context-title" style={{ fontSize: '13px' }}>
              LAZY Z-LOADER
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '17px' }}>
              On-Demand Frame I/O. Fibonacci and coarse bracket decimation cutting disk reads from O(N) to O(log N), eliminating 86% of disk throughput.
            </p>
          </div>

          {/* Stage 2 */}
          <div className="matte-card" style={{ borderTop: '3px solid #40D4FF', gap: '8px' }}>
            <span style={{ fontSize: '10px', fontWeight: '700', color: '#40D4FF', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              STAGE 02
            </span>
            <h3 className="matte-context-title" style={{ fontSize: '13px' }}>
              PRE-CONDITIONER
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '17px' }}>
              Anscombe algebraic root transform: <code>2·√(I + 3/8)</code>. Normalizes non-linear Poisson shot noise into unit-variance Gaussian noise.
            </p>
          </div>

          {/* Stage 3 */}
          <div className="matte-card" style={{ borderTop: '3px solid #30D158', gap: '8px' }}>
            <span style={{ fontSize: '10px', fontWeight: '700', color: '#30D158', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              STAGE 03
            </span>
            <h3 className="matte-context-title" style={{ fontSize: '13px' }}>
              DYNAMIC ROI GATE
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '17px' }}>
              3×3 grid partitions central 70% FOV. Automatically selects Top-K (K=3) high-entropy patches, rejecting blank vacuum regions.
            </p>
          </div>

          {/* Stage 4 */}
          <div className="matte-card" style={{ borderTop: '3px solid #BF5AF2', gap: '8px' }}>
            <span style={{ fontSize: '10px', fontWeight: '700', color: '#BF5AF2', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              STAGE 04
            </span>
            <h3 className="matte-context-title" style={{ fontSize: '13px' }}>
              10-FMO ENGINE
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '17px' }}>
              Dual coarse-fine operator dispatch: Normalized Variance (M9) for coarse climbing, Scharr (M1) or Tensor (M10) for peak lock.
            </p>
          </div>

          {/* Stage 5 */}
          <div className="matte-card" style={{ borderTop: '3px solid #FF9F0A', gap: '8px' }}>
            <span style={{ fontSize: '10px', fontWeight: '700', color: '#FF9F0A', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              STAGE 05
            </span>
            <h3 className="matte-context-title" style={{ fontSize: '13px' }}>
              PEAK INTERPOLATOR
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '17px' }}>
              3-point Gaussian log-quadratic fit: <code>z* = k* + 0.5(L_-1 - L_+1)/(L_-1 - 2L_0 + L_+1)</code> achieving ±0.027 Δz sub-slice precision.
            </p>
          </div>
        </div>
      </div>

      {/* Specimen Regime Decision Tree (Strict 0px Geometry) */}
      <div>
        <div className="matte-section-h2">
          <span>Figure 7.1 — Experimental Decision Tree for Electron Microscopy Regimes</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
          <div className="matte-card" style={{ borderLeft: '3px solid var(--accent-cyan)', gap: '8px' }}>
            <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--accent-cyan)' }}>
              Clean / High SNR SEM
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Target: Maximum Speed (Sub-10ms)
            </div>
            <div style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--text-primary)', marginTop: '4px' }}>
              → M2 Brenner or M1 Scharr + S1 Fibonacci Lattice (stride=2)
            </div>
          </div>

          <div className="matte-card" style={{ borderLeft: '3px solid var(--status-danger)', gap: '8px' }}>
            <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--status-danger)' }}>
              Heavy Shot-Noise / Low-Dose
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Target: Robust Noise Immunity
            </div>
            <div style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--text-primary)', marginTop: '4px' }}>
              → M10 Structure Tensor + Anscombe + S2 Hybrid Sweep
            </div>
          </div>

          <div className="matte-card" style={{ borderLeft: '3px solid #BF5AF2', gap: '8px' }}>
            <div style={{ fontSize: '12px', fontWeight: '700', color: '#BF5AF2' }}>
              HRTEM / Periodic Lattice
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Target: Phase-Contrast Peak Lock
            </div>
            <div style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--text-primary)', marginTop: '4px' }}>
              → M8 FFT Bandpass or M3 SML + 5-Point Savitzky-Golay Fit
            </div>
          </div>

          <div className="matte-card" style={{ borderLeft: '3px solid var(--status-warning)', gap: '8px' }}>
            <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--status-warning)' }}>
              Flickering Beam / Thermal Drift
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Target: Intensity Invariance
            </div>
            <div style={{ fontSize: '12.5px', fontWeight: '600', color: 'var(--text-primary)', marginTop: '4px' }}>
              → M6 Haar Wavelet or M9 Norm-Variance + Top-3 ROI Gating
            </div>
          </div>
        </div>
      </div>

      {/* 10 Focus Measure Operators Reference Grid */}
      <div>
        <div className="matte-section-h2">
          <span>The 10 Production Focus Measure Operators (FMOs)</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
          {Object.keys(fmos).map(key => {
            const op = fmos[key];
            return (
              <div key={key} className="matte-card" style={{ gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
                    {op.id}: {op.name}
                  </span>
                  <span className="matte-badge matte-badge-cyan" style={{ fontSize: '10px' }}>
                    {op.category}
                  </span>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '17px' }}>
                  {op.description}
                </p>
                <div style={{ display: 'flex', gap: '18px', fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  <span><b>Compute Cost:</b> {op.compute_cost}</span>
                  <span><b>Noise Immunity:</b> {op.noise_immunity}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
