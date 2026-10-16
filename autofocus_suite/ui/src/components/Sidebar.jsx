import React from 'react';
import { 
  Sliders, 
  Activity, 
  Trophy, 
  ZoomIn, 
  BookOpen, 
  Folder, 
  FolderPlus,
  Menu,
  HardDrive
} from 'lucide-react';

export default function Sidebar({ 
  currentTab, 
  setCurrentTab, 
  currentDataset, 
  setCurrentDataset, 
  datasets,
  currentDataPath,
  onOpenPathModal
}) {
  return (
    <aside className="matte-nav-rail">
      {/* Brand Header */}
      <div className="matte-rail-brand">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* 5-Bar Focus Peak Equalizer Icon (Rectilinear 0px) */}
          <img 
            src="/app_icon.svg" 
            alt="Autofocus Equalizer" 
            style={{ width: '26px', height: '26px', flexShrink: 0 }} 
          />
          <div>
            <div style={{ fontSize: '15px', fontWeight: '700', letterSpacing: '-0.02em', lineHeight: '1.2', color: 'var(--text-primary)' }}>
              Autofocus
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Lab Suite
            </div>
          </div>
        </div>
        <button 
          className="matte-wireframe-btn" 
          title="Toggle Navigation"
          style={{ width: '28px', height: '28px' }}
        >
          <Menu size={16} strokeWidth={1.25} />
        </button>
      </div>

      {/* Navigation Group: Operations & Views */}
      <div style={{ marginTop: '8px' }}>
        <div className="matte-rail-heading">Autofocus Views</div>
        <nav style={{ display: 'flex', flexDirection: 'column' }}>
          <button 
            className={`matte-rail-item ${currentTab === 'studio' ? 'active' : ''}`}
            onClick={() => setCurrentTab('studio')}
          >
            <Sliders size={16} strokeWidth={1.25} style={{ flexShrink: 0 }} />
            <span>Live Sweep Studio</span>
          </button>

          <button 
            className={`matte-rail-item ${currentTab === 'curves' ? 'active' : ''}`}
            onClick={() => setCurrentTab('curves')}
          >
            <Activity size={16} strokeWidth={1.25} style={{ flexShrink: 0 }} />
            <span>10-FMO Curves</span>
          </button>

          <button 
            className={`matte-rail-item ${currentTab === 'leaderboard' ? 'active' : ''}`}
            onClick={() => setCurrentTab('leaderboard')}
          >
            <Trophy size={16} strokeWidth={1.25} style={{ flexShrink: 0 }} />
            <span>Tournament Leaderboard</span>
          </button>

          <button 
            className={`matte-rail-item ${currentTab === 'inspector' ? 'active' : ''}`}
            onClick={() => setCurrentTab('inspector')}
          >
            <ZoomIn size={16} strokeWidth={1.25} style={{ flexShrink: 0 }} />
            <span>Loupe Inspector (4x)</span>
          </button>

          <button 
            className={`matte-rail-item ${currentTab === 'guide' ? 'active' : ''}`}
            onClick={() => setCurrentTab('guide')}
          >
            <BookOpen size={16} strokeWidth={1.25} style={{ flexShrink: 0 }} />
            <span>Architecture Guide</span>
          </button>
        </nav>
      </div>

      {/* Navigation Group: Focal Stacks */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, marginTop: '12px' }}>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between', 
          paddingRight: '12px' 
        }}>
          <span className="matte-rail-heading">Focal Stacks</span>
          <button 
            className="matte-wireframe-btn"
            onClick={onOpenPathModal}
            title="Select Datasets Directory"
            style={{ width: '22px', height: '22px' }}
          >
            <FolderPlus size={14} strokeWidth={1.25} color="var(--accent-cyan)" />
          </button>
        </div>

        {/* Stack Items List */}
        <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column' }}>
          {datasets.map(ds => {
            const isSelected = ds.id === currentDataset;
            return (
              <button
                key={ds.id}
                onClick={() => setCurrentDataset(ds.id)}
                className={`matte-rail-item ${isSelected ? 'active' : ''}`}
                style={{ justifyContent: 'space-between', paddingRight: '16px' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px', overflow: 'hidden' }}>
                  <Folder 
                    size={16} 
                    strokeWidth={1.25}
                    color={isSelected ? 'var(--accent-cyan)' : 'var(--text-muted)'} 
                    style={{ flexShrink: 0 }}
                  />
                  <div style={{ overflow: 'hidden', textAlign: 'left' }}>
                    <span style={{ 
                      display: 'block', 
                      fontSize: '13px', 
                      fontWeight: isSelected ? '600' : '400',
                      color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                      whiteSpace: 'nowrap',
                      textOverflow: 'ellipsis',
                      overflow: 'hidden'
                    }}>
                      {ds.name || ds.id}
                    </span>
                    <span style={{ 
                      fontSize: '11px', 
                      color: 'var(--text-muted)',
                      display: 'block' 
                    }}>
                      {ds.regime ? ds.regime.split(' ')[0] : 'Stack'}
                    </span>
                  </div>
                </div>
                <span className="mono-metric" style={{ 
                  fontSize: '11px', 
                  color: 'var(--text-muted)',
                  flexShrink: 0
                }}>
                  {ds.num_frames}f
                </span>
              </button>
            );
          })}
        </div>

        {/* Path Selection Action Trigger */}
        <div style={{ padding: '8px 12px 4px' }}>
          <button
            onClick={onOpenPathModal}
            className="matte-rail-item"
            style={{ 
              height: '34px', 
              background: 'var(--bg-surface-hover)', 
              border: '1px solid var(--border-subtle)',
              gap: '10px'
            }}
            title={currentDataPath || 'Select Datasets Directory'}
          >
            <HardDrive size={14} strokeWidth={1.25} color="var(--accent-cyan)" style={{ flexShrink: 0 }} />
            <div style={{ overflow: 'hidden', textAlign: 'left', flex: 1 }}>
              <span style={{ 
                display: 'block', 
                fontSize: '11px', 
                color: 'var(--text-primary)', 
                fontFamily: 'var(--font-mono)',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {currentDataPath ? currentDataPath.replace(/^.*[\\\/]/, '') || currentDataPath : 'Choose Folder...'}
              </span>
            </div>
          </button>
        </div>
      </div>

      {/* Bottom Telemetry Footer */}
      <div className="matte-rail-footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
          <div style={{
            width: '20px',
            height: '20px',
            background: 'var(--bg-surface-active)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--accent-cyan)',
            fontWeight: '700',
            fontSize: '10px',
            flexShrink: 0
          }}>
            AF
          </div>
          <div style={{ overflow: 'hidden' }}>
            <span style={{ display: 'block', fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)' }}>
              SEM Core Active
            </span>
            <span style={{ fontSize: '10.5px', color: 'var(--status-success)', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: '4px', height: '4px', background: 'var(--status-success)', display: 'inline-block' }}></span>
              Port 8000 Ready
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
