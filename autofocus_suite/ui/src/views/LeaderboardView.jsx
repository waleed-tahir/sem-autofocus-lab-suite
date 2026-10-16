import React, { useState, useEffect } from 'react';
import { 
  Trophy, 
  ArrowUpDown, 
  Check, 
  AlertTriangle, 
  Clock, 
  Sparkles,
  Search,
  Filter,
  CheckCircle2
} from 'lucide-react';

export default function LeaderboardView({ 
  currentDataset, 
  metadata, 
  theme 
}) {
  const [benchmarkData, setBenchmarkData] = useState(null);
  const [selectedDataset, setSelectedDataset] = useState('all');
  const [filterZeroError, setFilterZeroError] = useState(false);
  const [filterSearch, setFilterSearch] = useState('all');
  const [filterFmo, setFilterFmo] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('wall_clock_ms');
  const [sortOrder, setSortOrder] = useState('asc');

  useEffect(() => {
    fetch('/api/benchmark-matrix')
      .then(res => res.json())
      .then(data => setBenchmarkData(data))
      .catch(err => console.error("Failed to load benchmark:", err));
  }, []);

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  let runs = [];
  if (benchmarkData && benchmarkData.datasets) {
    if (selectedDataset === 'all') {
      Object.keys(benchmarkData.datasets).forEach(ds => {
        runs = runs.concat(benchmarkData.datasets[ds].runs || []);
      });
    } else if (benchmarkData.datasets[selectedDataset]) {
      runs = benchmarkData.datasets[selectedDataset].runs || [];
    }
  }

  const filteredRuns = runs.filter(run => {
    if (filterZeroError && run.discrete_error !== 0) return false;
    if (filterSearch !== 'all' && run.search_method !== filterSearch) return false;
    if (filterFmo !== 'all' && run.fmo !== filterFmo) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchName = run.search_name.toLowerCase().includes(q) || run.fmo_name.toLowerCase().includes(q) || run.dataset.toLowerCase().includes(q);
      if (!matchName) return false;
    }
    return true;
  });

  filteredRuns.sort((a, b) => {
    let valA = a[sortBy];
    let valB = b[sortBy];
    if (sortBy === 'wall_clock_ms' || sortBy === 'discrete_error' || sortBy === 'frames_read' || sortBy === 'subframe_error') {
      return sortOrder === 'asc' ? valA - valB : valB - valA;
    } else {
      return sortOrder === 'asc' ? valB - valA : valA - valB;
    }
  });

  const recommendations = benchmarkData?.recommendations || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', gap: '32px' }}>
      {/* Zone 2: Hero Header Zone */}
      <section className="matte-hero-zone">
        <div>
          <h1 className="matte-hero-title">
            Tournament Leaderboard
          </h1>
          <p className="matte-hero-bio">
            Ablation tournament benchmarking 40 algorithm combinations across all 4 SEM noise regimes (Clean to Heavy Shot Noise). Ranks search latency, I/O decimation, and sub-frame accuracy.
          </p>
        </div>

        {/* Action Cluster */}
        <div className="matte-action-cluster">
          <div className="matte-action-cluster-tag">
            ABLATION BENCHMARK MATRIX
          </div>
          <div className="matte-action-icons">
            <span className="matte-badge matte-badge-cyan tabular-nums">
              <Sparkles size={12} strokeWidth={1.25} />
              {filteredRuns.length} COMBINATIONS EVALUATED
            </span>
          </div>
        </div>
      </section>

      {/* Recommended Winning Strategies Across Regimes (Strict 0px geometry) */}
      <div>
        <div className="matte-section-h2">
          <span>Architectural Recommendations by SEM Regime</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
          {Object.keys(recommendations).map(ds => {
            const rec = recommendations[ds];
            const isCurrent = ds === currentDataset;
            return (
              <div 
                key={ds} 
                className="matte-card" 
                style={{ 
                  borderLeft: isCurrent ? '3px solid var(--accent-cyan)' : '1px solid var(--border-card)',
                  background: '#1C1D20',
                  gap: '8px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '11px', fontWeight: '600', color: isCurrent ? 'var(--accent-cyan)' : 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    {rec.regime}
                  </span>
                  {isCurrent && <span className="matte-badge matte-badge-cyan" style={{ fontSize: '10px' }}>Active</span>}
                </div>
                
                <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
                  {metadata.search_algorithms?.[rec.winning_search]?.name?.split(' ')[0] || rec.winning_search} + {metadata.fmos?.[rec.winning_fmo]?.name?.split(' ')[0] || rec.winning_fmo}
                </div>

                <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }} className="tabular-nums">
                  Anscombe: <b style={{ color: rec.recommended_anscombe ? 'var(--accent-cyan)' : 'inherit' }}>{rec.recommended_anscombe ? 'Enabled' : 'Bypassed'}</b>
                </div>

                <p style={{ fontSize: '11.5px', color: 'var(--text-muted)', lineHeight: '16px' }}>
                  {rec.rationale}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Filter & Search Bar (Flat Matte Controls, 0px Radius) */}
      <div className="matte-card" style={{ padding: '12px 16px', flexDirection: 'row', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: '220px' }}>
          <Search size={14} strokeWidth={1.25} color="var(--text-muted)" />
          <input 
            type="text" 
            placeholder="Search strategy, FMO, or dataset..."
            className="matte-input"
            style={{ width: '100%', fontSize: '12px' }}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <select 
          className="matte-select"
          value={selectedDataset}
          onChange={(e) => setSelectedDataset(e.target.value)}
        >
          <option value="all">All Datasets (Combined)</option>
          <option value="pollen.spd1">pollen.spd1 (Clean SEM)</option>
          <option value="pollen.spd2">pollen.spd2 (Standard SEM)</option>
          <option value="pollen.spd3">pollen.spd3 (Moderate Noise)</option>
          <option value="pollen.spd5">pollen.spd5 (Heavy Shot Noise)</option>
        </select>

        <select 
          className="matte-select"
          value={filterSearch}
          onChange={(e) => setFilterSearch(e.target.value)}
        >
          <option value="all">All Search Methods</option>
          <option value="s1_fibonacci">S1: Fibonacci Lattice</option>
          <option value="s2_hybrid">S2: Hybrid Coarse-to-Fine</option>
          <option value="s3_pyramid">S3: Pyramid Bracket</option>
          <option value="s4_speculative">S4: Speculative Parallel</option>
          <option value="golden_section">Golden Section</option>
          <option value="baseline_global">Global Full Scan</option>
        </select>

        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', cursor: 'pointer', color: 'var(--text-secondary)' }}>
          <input 
            type="checkbox"
            checked={filterZeroError}
            onChange={(e) => setFilterZeroError(e.target.checked)}
            style={{ width: '14px', height: '14px', accentColor: 'var(--accent-cyan)' }}
          />
          <span>Zero Error Only</span>
        </label>
      </div>

      {/* Main Results Table (Strictly 0px, Zero Horizontal Dividers, Tabular Nums) */}
      <div className="matte-card" style={{ padding: 0 }}>
        <div style={{ maxHeight: '520px', overflowY: 'auto' }}>
          <table className="matte-table tabular-nums">
            <thead style={{ background: '#141416', position: 'sticky', top: 0, zIndex: 1 }}>
              <tr style={{ height: '36px', borderBottom: '1px solid var(--border-subtle)' }}>
                <th onClick={() => handleSort('search_name')} style={{ cursor: 'pointer', textAlign: 'left', padding: '0 14px', fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Search Strategy <ArrowUpDown size={11} strokeWidth={1.25} style={{ display: 'inline', marginLeft: '4px' }} />
                </th>
                <th onClick={() => handleSort('fmo_name')} style={{ cursor: 'pointer', textAlign: 'left', padding: '0 14px', fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Focus Measure (FMO) <ArrowUpDown size={11} strokeWidth={1.25} style={{ display: 'inline', marginLeft: '4px' }} />
                </th>
                <th style={{ textAlign: 'left', padding: '0 14px', fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Anscombe</th>
                <th style={{ textAlign: 'left', padding: '0 14px', fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Dataset</th>
                <th onClick={() => handleSort('discrete_error')} style={{ cursor: 'pointer', textAlign: 'right', padding: '0 14px', fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Error <ArrowUpDown size={11} strokeWidth={1.25} style={{ display: 'inline', marginLeft: '4px' }} />
                </th>
                <th onClick={() => handleSort('subframe_error')} style={{ cursor: 'pointer', textAlign: 'right', padding: '0 14px', fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Subframe Δz <ArrowUpDown size={11} strokeWidth={1.25} style={{ display: 'inline', marginLeft: '4px' }} />
                </th>
                <th onClick={() => handleSort('frames_read')} style={{ cursor: 'pointer', textAlign: 'right', padding: '0 14px', fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Reads (I/O Cut) <ArrowUpDown size={11} strokeWidth={1.25} style={{ display: 'inline', marginLeft: '4px' }} />
                </th>
                <th onClick={() => handleSort('wall_clock_ms')} style={{ cursor: 'pointer', textAlign: 'right', padding: '0 14px', fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Latency <ArrowUpDown size={11} strokeWidth={1.25} style={{ display: 'inline', marginLeft: '4px' }} />
                </th>
                <th onClick={() => handleSort('psr')} style={{ cursor: 'pointer', textAlign: 'right', padding: '0 14px', fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  PSR <ArrowUpDown size={11} strokeWidth={1.25} style={{ display: 'inline', marginLeft: '4px' }} />
                </th>
                <th style={{ textAlign: 'center', padding: '0 14px', fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredRuns.map((r, i) => {
                const isAccurate = r.discrete_error === 0;
                return (
                  <tr key={i} className="matte-table-row">
                    <td className="matte-table-primary" style={{ padding: '0 14px' }}>
                      {r.search_name}
                    </td>
                    <td className="matte-table-secondary" style={{ padding: '0 14px' }}>
                      <span className="matte-badge matte-badge-cyan" style={{ fontSize: '10.5px' }}>
                        {r.fmo_name}
                      </span>
                    </td>
                    <td style={{ padding: '0 14px', fontSize: '12px' }}>
                      {r.use_anscombe ? (
                        <span style={{ color: 'var(--accent-cyan)', fontWeight: '500' }}>Active</span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>Off</span>
                      )}
                    </td>
                    <td style={{ padding: '0 14px', fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                      {r.dataset}
                    </td>
                    <td style={{ padding: '0 14px', textAlign: 'right', fontSize: '12px' }}>
                      <span style={{ color: isAccurate ? '#30D158' : 'var(--status-warning)', fontWeight: '600' }}>
                        {r.discrete_error} frames
                      </span>
                    </td>
                    <td style={{ padding: '0 14px', textAlign: 'right', fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                      {r.subframe_error} Δz
                    </td>
                    <td style={{ padding: '0 14px', textAlign: 'right', fontSize: '12px' }}>
                      <b>{r.frames_read}</b> <span style={{ color: 'var(--text-muted)' }}>({r.io_reduction_pct}% cut)</span>
                    </td>
                    <td style={{ padding: '0 14px', textAlign: 'right', fontSize: '12px' }}>
                      <span style={{ color: r.wall_clock_ms < 15 ? '#30D158' : 'var(--text-primary)', fontWeight: '600' }}>
                        {r.wall_clock_ms} ms
                      </span>
                    </td>
                    <td style={{ padding: '0 14px', textAlign: 'right', fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {r.psr}
                    </td>
                    <td style={{ padding: '0 14px', textAlign: 'center' }}>
                      {isAccurate ? (
                        <span className="matte-badge matte-badge-green" style={{ fontSize: '10px' }}>
                          <Check size={11} strokeWidth={1.5} /> LOCKED
                        </span>
                      ) : (
                        <span className="matte-badge matte-badge-amber" style={{ fontSize: '10px' }}>
                          <AlertTriangle size={11} strokeWidth={1.5} /> OFF BY {r.discrete_error}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
