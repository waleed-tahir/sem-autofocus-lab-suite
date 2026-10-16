import React from 'react';
import { 
  BookOpen, 
  Cpu, 
  GitBranch, 
  ShieldAlert, 
  Zap, 
  Layers, 
  CheckCircle2, 
  Compass, 
  Flame 
} from 'lucide-react';

export default function LabGuideView({ metadata }) {
  const fmos = metadata?.fmos || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header Banner */}
      <div className="glass-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 22px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '38px', height: '38px', borderRadius: '10px', background: 'rgba(0, 122, 255, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <BookOpen size={20} color="#0A84FF" />
          </div>
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: '600' }}>Lab Reference & 5-Stage Autofocus Architecture</h2>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Complete engineering specification for SEM/TEM Camera2 HAL3 multi-scale autofocus
            </p>
          </div>
        </div>
      </div>

      {/* 5-Stage Architecture Pipeline (Figure 1.1 in PDF) */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={16} color="#0A84FF" />
          Figure 1.1: Next-Generation Five-Stage Autofocus Pipeline
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px' }}>
          {/* Stage 1 */}
          <div style={{ background: 'rgba(10, 132, 255, 0.08)', border: '1px solid rgba(10, 132, 255, 0.3)', borderRadius: '12px', padding: '14px' }}>
            <span style={{ fontSize: '10px', fontWeight: '700', color: '#0A84FF', textTransform: 'uppercase' }}>Stage 1</span>
            <h4 style={{ fontSize: '13px', fontWeight: '700', margin: '4px 0 6px' }}>1. LAZY Z-LOADER</h4>
            <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
              On-Demand Frame I/O. Fibonacci / coarse step decimation reducing disk reads from O(N) to O(log N) or O(√N).
            </p>
          </div>

          {/* Stage 2 */}
          <div style={{ background: 'rgba(0, 229, 255, 0.08)', border: '1px solid rgba(0, 229, 255, 0.3)', borderRadius: '12px', padding: '14px' }}>
            <span style={{ fontSize: '10px', fontWeight: '700', color: '#00E5FF', textTransform: 'uppercase' }}>Stage 2</span>
            <h4 style={{ fontSize: '13px', fontWeight: '700', margin: '4px 0 6px' }}>2. PRE-CONDITIONER</h4>
            <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
              Anscombe algebraic root transform: <code>2·√(I + 3/8)</code> stabilizes Poisson shot noise into unit-variance Gaussian noise.
            </p>
          </div>

          {/* Stage 3 */}
          <div style={{ background: 'rgba(48, 209, 88, 0.08)', border: '1px solid rgba(48, 209, 88, 0.3)', borderRadius: '12px', padding: '14px' }}>
            <span style={{ fontSize: '10px', fontWeight: '700', color: '#30D158', textTransform: 'uppercase' }}>Stage 3</span>
            <h4 style={{ fontSize: '13px', fontWeight: '700', margin: '4px 0 6px' }}>3. DYNAMIC ROI GATE</h4>
            <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
              3×3 grid metering partitions central 70% FOV. Automatically selects Top-K (K=3) high-SNR patches, rejecting empty vacuum.
            </p>
          </div>

          {/* Stage 4 */}
          <div style={{ background: 'rgba(191, 90, 242, 0.08)', border: '1px solid rgba(191, 90, 242, 0.3)', borderRadius: '12px', padding: '14px' }}>
            <span style={{ fontSize: '10px', fontWeight: '700', color: '#BF5AF2', textTransform: 'uppercase' }}>Stage 4</span>
            <h4 style={{ fontSize: '13px', fontWeight: '700', margin: '4px 0 6px' }}>4. 10-FMO KERNEL</h4>
            <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
              Hybrid coarse-to-fine operator switching: Normalized Variance (M9) for coarse climbing, Scharr (M1) or Tensor (M10) for peak lock.
            </p>
          </div>

          {/* Stage 5 */}
          <div style={{ background: 'rgba(255, 159, 10, 0.08)', border: '1px solid rgba(255, 159, 10, 0.3)', borderRadius: '12px', padding: '14px' }}>
            <span style={{ fontSize: '10px', fontWeight: '700', color: '#FF9F0A', textTransform: 'uppercase' }}>Stage 5</span>
            <h4 style={{ fontSize: '13px', fontWeight: '700', margin: '4px 0 6px' }}>5. PEAK LOCK</h4>
            <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
              3-point Gaussian log-quadratic fit: <code>z* = k* + 0.5(L_-1 - L_+1)/(L_-1 - 2L_0 + L_+1)</code> achieving ±0.03 Δz sub-frame precision.
            </p>
          </div>
        </div>
      </div>

      {/* Specimen Decision Tree (Figure 7.1) */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <GitBranch size={16} color="#30D158" />
          Figure 7.1: Experimental Decision Tree for Electron Microscopy Regimes
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px' }}>
          <div className="glass-card" style={{ padding: '14px', borderLeft: '4px solid #0A84FF' }}>
            <div style={{ fontSize: '12px', fontWeight: '700', color: '#0A84FF', marginBottom: '4px' }}>
              Clean / High SNR SEM
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
              <b>Priority:</b> Maximum Speed Leaderboard
            </div>
            <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)' }}>
              → Use M2 (Multi-Brenner) or M1 (Scharr) + S1 Fibonacci Search (stride = 2)
            </div>
          </div>

          <div className="glass-card" style={{ padding: '14px', borderLeft: '4px solid #FF375F' }}>
            <div style={{ fontSize: '12px', fontWeight: '700', color: '#FF375F', marginBottom: '4px' }}>
              Heavy Shot-Noise / Low-Dose
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
              <b>Priority:</b> Noise Immunity
            </div>
            <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)' }}>
              → Use M10 (Structure Tensor) + Anscombe + S2 Hybrid Sweep
            </div>
          </div>

          <div className="glass-card" style={{ padding: '14px', borderLeft: '4px solid #BF5AF2' }}>
            <div style={{ fontSize: '12px', fontWeight: '700', color: '#BF5AF2', marginBottom: '4px' }}>
              HRTEM / Periodic Lattice
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
              <b>Priority:</b> Phase-Contrast Lock
            </div>
            <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)' }}>
              → Use M8 (FFT Bandpass) or M3 (SML) + 5-Point Savitzky-Golay Fit
            </div>
          </div>

          <div className="glass-card" style={{ padding: '14px', borderLeft: '4px solid #FF9F0A' }}>
            <div style={{ fontSize: '12px', fontWeight: '700', color: '#FF9F0A', marginBottom: '4px' }}>
              Flickering Beam / Drift
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
              <b>Priority:</b> Exposure Invariance
            </div>
            <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)' }}>
              → Use M6 (Haar Wavelet) or M9 (Norm-Variance) + Top-3 Dynamic ROI Gating
            </div>
          </div>
        </div>
      </div>

      {/* 10 Focus Measure Operators Reference Grid */}
      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Cpu size={16} color="#00E5FF" />
          The 10 Production Focus Measure Operators (FMOs)
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '14px' }}>
          {Object.keys(fmos).map(key => {
            const op = fmos[key];
            return (
              <div key={key} style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '10px', padding: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
                    {op.id}: {op.name}
                  </span>
                  <span className="badge-pill badge-blue" style={{ fontSize: '10px' }}>
                    {op.category}
                  </span>
                </div>
                <p style={{ fontSize: '11.5px', color: 'var(--text-secondary)', lineHeight: '1.4', marginBottom: '8px' }}>
                  {op.description}
                </p>
                <div style={{ display: 'flex', gap: '14px', fontSize: '11px', color: 'var(--text-tertiary)' }}>
                  <span><b>Compute:</b> {op.compute_cost}</span>
                  <span><b>Immunity:</b> {op.noise_immunity}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
