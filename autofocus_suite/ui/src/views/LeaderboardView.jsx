import React, { useState, useEffect } from 'react';
import { 
  Trophy, 
  Filter, 
  ArrowUpDown, 
  CheckCircle2, 
  XCircle, 
  Zap, 
  Clock, 
  HardDrive, 
  ShieldCheck, 
  Sparkles,
  Search
} from 'lucide-react';

export default function LeaderboardView({ 
  currentDataset, 
  metadata, 
  theme 
}) {
  const [benchmarkData, setBenchmarkData] = useState(null);
  const [selectedDataset, setSelectedDataset] = useState(currentDataset);
  const [filterZeroError, setFilterZeroError] = useState(false);
  const [filterSearch, setFilterSearch] = useState('all');
  const [filterFmo, setFilterFmo] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('wall_clock_ms'); // 'wall_clock_ms', 'discrete_error', 'frames_read', 'psr'
  const [sortOrder, setSortOrder] = useState('asc'); // 'asc' or 'desc'

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

  // Extract runs for the selected dataset
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

  // Filter runs
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

  // Sort runs
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header Banner */}
      <div className="glass-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 22px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '38px', height: '38px', borderRadius: '10px', background: 'rgba(255, 214, 10, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Trophy size={20} color="#FFD60A" />
          </div>
          <div>
            <h2 style={{ fontSize: '16px', fontWeight: '600' }}>Autofocus Ablation Tournament & Benchmark Leaderboard</h2>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Comprehensive performance matrix across all 4 datasets (Clean SEM to Heavy Noise SEM)
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span className="badge-pill badge-green" style={{ fontSize: '12px', padding: '4px 10px' }}>
            <Sparkles size={13} /> {filteredRuns.length} Combinations Evaluated
          </span>
        </div>
      </div>

      {/* Recommended Winning Strategies Across Regimes */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px' }}>
        {Object.keys(recommendations).map(ds => {
          const rec = recommendations[ds];
          const isCurrent = ds === currentDataset;
          return (
            <div 
              key={ds} 
              className="glass-card" 
              style={{ 
                padding: '16px', 
                border: isCurrent ? '1.5px solid var(--accent-blue)' : '1px solid var(--border-subtle)',
                background: isCurrent ? 'rgba(10, 132, 255, 0.08)' : 'var(--bg-card)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--accent-blue)', textTransform: 'uppercase' }}>
                  {rec.regime}
                </span>
                {isCurrent && <span className="badge-pill badge-blue" style={{ fontSize: '10px' }}>Active</span>}
              </div>
              <div style={{ fontSize: '14px', fontWeight: '700', marginBottom: '4px' }}>
                {metadata.search_algorithms?.[rec.winning_search]?.name?.split(' ')[0] || rec.winning_search} + {metadata.fmos?.[rec.winning_fmo]?.name?.split(' ')[0] || rec.winning_fmo}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                Anscombe: <b>{rec.recommended_anscombe ? 'Enabled' : 'Disabled'}</b>
              </div>
              <p style={{ fontSize: '11px', color: 'var(--text-tertiary)', lineHeight: '1.4' }}>
                {rec.rationale}
              </p>
            </div>
          );
        })}
      </div>

      {/* Filter & Search Bar */}
      <div className="glass-card" style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 18px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flex: 1, minWidth: '200px' }}>
          <Search size={14} color="var(--text-tertiary)" />
          <input 
            type="text" 
            placeholder="Search method, FMO, or dataset..."
            className="macos-input"
            style={{ width: '100%', fontSize: '12px' }}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <select 
          className="macos-select"
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
          className="macos-select"
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

        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', cursor: 'pointer', color: 'var(--text-secondary)' }}>
          <input 
            type="checkbox"
            checked={filterZeroError}
            onChange={(e) => setFilterZeroError(e.target.checked)}
            style={{ accentColor: 'var(--accent-blue)' }}
          />
          Zero Discrete Error Only
        </label>
      </div>

      {/* Main Results Table */}
      <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ maxHeight: '480px', overflowY: 'auto' }}>
          <table className="macos-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('search_name')} style={{ cursor: 'pointer' }}>
                  Search Strategy <ArrowUpDown size={11} style={{ display: 'inline' }} />
                </th>
                <th onClick={() => handleSort('fmo_name')} style={{ cursor: 'pointer' }}>
                  Focus Measure (FMO) <ArrowUpDown size={11} style={{ display: 'inline' }} />
                </th>
                <th>Anscombe</th>
                <th>Dataset</th>
                <th onClick={() => handleSort('discrete_error')} style={{ cursor: 'pointer' }}>
                  Discrete Err <ArrowUpDown size={11} style={{ display: 'inline' }} />
                </th>
                <th onClick={() => handleSort('subframe_error')} style={{ cursor: 'pointer' }}>
                  Subframe Err <ArrowUpDown size={11} style={{ display: 'inline' }} />
                </th>
                <th onClick={() => handleSort('frames_read')} style={{ cursor: 'pointer' }}>
                  Reads (I/O Cut) <ArrowUpDown size={11} style={{ display: 'inline' }} />
                </th>
                <th onClick={() => handleSort('wall_clock_ms')} style={{ cursor: 'pointer' }}>
                  Latency <ArrowUpDown size={11} style={{ display: 'inline' }} />
                </th>
                <th onClick={() => handleSort('psr')} style={{ cursor: 'pointer' }}>
                  PSR <ArrowUpDown size={11} style={{ display: 'inline' }} />
                </th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredRuns.map((r, i) => {
                const isAccurate = r.discrete_error === 0;
                return (
                  <tr key={i}>
                    <td style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                      {r.search_name}
                    </td>
                    <td>
                      <span className="badge-pill badge-blue" style={{ fontSize: '11px' }}>
                        {r.fmo_name}
                      </span>
                    </td>
                    <td>
                      {r.use_anscombe ? (
                        <span style={{ color: '#00E5FF', fontWeight: '500' }}>Enabled</span>
                      ) : (
                        <span style={{ color: 'var(--text-tertiary)' }}>Off</span>
                      )}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11.5px' }}>
                      {r.dataset}
                    </td>
                    <td>
                      <b style={{ color: isAccurate ? '#30D158' : '#FF9F0A' }}>
                        {r.discrete_error} frames
                      </b>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      {r.subframe_error} Δz
                    </td>
                    <td>
                      <b>{r.frames_read}</b> frames ({r.io_reduction_pct}% cut)
                    </td>
                    <td>
                      <b style={{ color: r.wall_clock_ms < 15 ? '#30D158' : '#0A84FF' }}>
                        {r.wall_clock_ms} ms
                      </b>
                    </td>
                    <td>
                      {r.psr}
                    </td>
                    <td>
                      {isAccurate ? (
                        <span className="badge-pill badge-green" style={{ fontSize: '10.5px' }}>
                          <CheckCircle2 size={11} /> Locked
                        </span>
                      ) : (
                        <span className="badge-pill badge-amber" style={{ fontSize: '10.5px' }}>
                          <XCircle size={11} /> Off by {r.discrete_error}
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
