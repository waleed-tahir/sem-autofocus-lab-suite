import React from 'react';
import { 
  Sliders, 
  Activity, 
  Trophy, 
  ZoomIn, 
  BookOpen, 
  Sun, 
  Moon, 
  ChevronDown,
  FolderOpen,
  Search
} from 'lucide-react';

export default function Titlebar({ 
  currentTab, 
  setCurrentTab, 
  theme, 
  setTheme, 
  currentDataset, 
  setCurrentDataset,
  datasets,
  serverStatus,
  onOpenPathModal
}) {
  return (
    <header className="groove-header">
      {/* Groove Pivot View Tabs (Horizontal line indicator) */}
      <nav className="groove-tabs">
        <button 
          className={`groove-tab ${currentTab === 'studio' ? 'active' : ''}`}
          onClick={() => setCurrentTab('studio')}
        >
          <Sliders size={14} />
          Studio
        </button>
        <button 
          className={`groove-tab ${currentTab === 'curves' ? 'active' : ''}`}
          onClick={() => setCurrentTab('curves')}
        >
          <Activity size={14} />
          10-FMO Curves
        </button>
        <button 
          className={`groove-tab ${currentTab === 'leaderboard' ? 'active' : ''}`}
          onClick={() => setCurrentTab('leaderboard')}
        >
          <Trophy size={14} />
          Leaderboard
        </button>
        <button 
          className={`groove-tab ${currentTab === 'inspector' ? 'active' : ''}`}
          onClick={() => setCurrentTab('inspector')}
        >
          <ZoomIn size={14} />
          Loupe
        </button>
        <button 
          className={`groove-tab ${currentTab === 'guide' ? 'active' : ''}`}
          onClick={() => setCurrentTab('guide')}
        >
          <BookOpen size={14} />
          Guide
        </button>
      </nav>

      {/* Right Controls: Choose Folder, Dataset Switcher, Status, Theme */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {/* Choose Dataset Folder Button */}
        <button 
          className="groove-btn-action"
          onClick={onOpenPathModal}
          title="Select Datasets Directory / Path"
        >
          <FolderOpen size={13} color="var(--accent-cyan)" />
          <span>Datasets Path</span>
        </button>

        {/* Dataset Switcher Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <select 
              className="groove-select" 
              value={currentDataset}
              onChange={(e) => setCurrentDataset(e.target.value)}
            >
              {datasets.map(ds => (
                <option key={ds.id} value={ds.id}>
                  {ds.name} ({ds.regime ? ds.regime.split(' ')[0] : 'Stack'})
                </option>
              ))}
            </select>
            <ChevronDown 
              size={12} 
              color="var(--text-secondary)" 
              style={{ position: 'absolute', right: '8px', pointerEvents: 'none' }} 
            />
          </div>
        </div>

        {/* Server Status Indicator */}
        <div className={`badge-pill ${serverStatus ? 'badge-green' : 'badge-amber'}`} style={{ fontSize: '11px', padding: '3px 8px' }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: serverStatus ? '#107C41' : '#D83B01' }} />
          {serverStatus ? 'Ready' : 'Offline'}
        </div>

        {/* Theme Toggle */}
        <button 
          className="groove-icon-btn"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          title={theme === 'dark' ? "Switch to Light Mode" : "Switch to Dark Mode"}
          style={{ width: '30px', height: '30px' }}
        >
          {theme === 'dark' ? <Sun size={13} color="#D83B01" /> : <Moon size={13} color="#00B7C3" />}
        </button>
      </div>
    </header>
  );
}
