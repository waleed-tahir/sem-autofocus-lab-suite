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
  Minus,
  Square,
  X
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
    <header className="matte-command-bar">
      {/* Pivot View Tabs (Flat, 2px underline indicator) */}
      <nav className="matte-nav-tabs">
        <button 
          className={`matte-nav-tab ${currentTab === 'studio' ? 'active' : ''}`}
          onClick={() => setCurrentTab('studio')}
        >
          <Sliders size={14} strokeWidth={1.25} />
          <span>Studio</span>
        </button>
        <button 
          className={`matte-nav-tab ${currentTab === 'curves' ? 'active' : ''}`}
          onClick={() => setCurrentTab('curves')}
        >
          <Activity size={14} strokeWidth={1.25} />
          <span>10-FMO Curves</span>
        </button>
        <button 
          className={`matte-nav-tab ${currentTab === 'leaderboard' ? 'active' : ''}`}
          onClick={() => setCurrentTab('leaderboard')}
        >
          <Trophy size={14} strokeWidth={1.25} />
          <span>Leaderboard</span>
        </button>
        <button 
          className={`matte-nav-tab ${currentTab === 'inspector' ? 'active' : ''}`}
          onClick={() => setCurrentTab('inspector')}
        >
          <ZoomIn size={14} strokeWidth={1.25} />
          <span>Loupe</span>
        </button>
        <button 
          className={`matte-nav-tab ${currentTab === 'guide' ? 'active' : ''}`}
          onClick={() => setCurrentTab('guide')}
        >
          <BookOpen size={14} strokeWidth={1.25} />
          <span>Guide</span>
        </button>
      </nav>

      {/* Right Controls: Choose Folder, Dataset Switcher, Status, Theme */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Dataset Path Selector Link */}
        <button 
          className="matte-link-cyan"
          onClick={onOpenPathModal}
          title="Select Datasets Directory / Path"
        >
          <FolderOpen size={13} strokeWidth={1.25} />
          <span>Datasets Path</span>
        </button>

        {/* Dataset Switcher Dropdown */}
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <select 
            className="matte-select" 
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

        {/* Server Status Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--text-secondary)' }}>
          <span style={{ 
            width: '6px', 
            height: '6px', 
            background: serverStatus ? 'var(--status-success)' : 'var(--status-danger)' 
          }} />
          <span className="mono-metric">{serverStatus ? 'Ready' : 'Offline'}</span>
        </div>

        {/* Theme Toggle Wireframe Button */}
        <button 
          className="matte-wireframe-btn"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          title={theme === 'dark' ? "Switch to Light Mode" : "Switch to Dark Mode"}
          style={{ width: '28px', height: '28px' }}
        >
          {theme === 'dark' ? <Sun size={14} strokeWidth={1.25} color="var(--status-warning)" /> : <Moon size={14} strokeWidth={1.25} color="var(--accent-cyan)" />}
        </button>

        {/* Chromeless Window Management Controls (Section 1.1 & 4) */}
        <div className="matte-window-controls">
          <button 
            className="matte-win-btn" 
            title="Minimize"
            onClick={() => {}}
          >
            <Minus size={13} strokeWidth={1.25} />
          </button>
          <button 
            className="matte-win-btn" 
            title="Maximize"
            onClick={() => {}}
          >
            <Square size={11} strokeWidth={1.25} />
          </button>
          <button 
            className="matte-win-btn matte-win-btn-close" 
            title="Close"
            onClick={() => {}}
          >
            <X size={14} strokeWidth={1.25} />
          </button>
        </div>
      </div>
    </header>
  );
}
