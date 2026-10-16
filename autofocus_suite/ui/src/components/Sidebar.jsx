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
  CheckCircle,
  HardDrive,
  Settings
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
    <aside className="groove-sidebar">
      {/* Groove Brand Header */}
      <div className="groove-sidebar-brand">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* 5-Bar Focus Peak Equalizer Icon (Image 2) */}
          <img 
            src="/app_icon.svg" 
            alt="Autofocus Equalizer" 
            style={{ width: '28px', height: '28px', borderRadius: '7px', flexShrink: 0 }} 
          />
          <div>
            <div style={{ fontSize: '15px', fontWeight: '700', letterSpacing: '-0.3px', lineHeight: '1.2' }}>
              Autofocus
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.8px' }}>
              Lab Suite
            </div>
          </div>
        </div>
        <button 
          className="groove-icon-btn" 
          title="Toggle Navigation"
          style={{ width: '32px', height: '32px' }}
        >
          <Menu size={16} />
        </button>
      </div>

      {/* Navigation Group: Operations & Views */}
      <div style={{ marginTop: '8px' }}>
        <div className="groove-sidebar-heading">Autofocus Views</div>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
          <button 
            className={`groove-sidebar-item ${currentTab === 'studio' ? 'active' : ''}`}
            onClick={() => setCurrentTab('studio')}
          >
            <Sliders size={16} className="groove-item-icon" />
            <span>Live Sweep Studio</span>
          </button>

          <button 
            className={`groove-sidebar-item ${currentTab === 'curves' ? 'active' : ''}`}
            onClick={() => setCurrentTab('curves')}
          >
            <Activity size={16} className="groove-item-icon" />
            <span>10-FMO Curves</span>
          </button>

          <button 
            className={`groove-sidebar-item ${currentTab === 'leaderboard' ? 'active' : ''}`}
            onClick={() => setCurrentTab('leaderboard')}
          >
            <Trophy size={16} className="groove-item-icon" />
            <span>Tournament Leaderboard</span>
          </button>

          <button 
            className={`groove-sidebar-item ${currentTab === 'inspector' ? 'active' : ''}`}
            onClick={() => setCurrentTab('inspector')}
          >
            <ZoomIn size={16} className="groove-item-icon" />
            <span>Loupe Inspector (4x)</span>
          </button>

          <button 
            className={`groove-sidebar-item ${currentTab === 'guide' ? 'active' : ''}`}
            onClick={() => setCurrentTab('guide')}
          >
            <BookOpen size={16} className="groove-item-icon" />
            <span>Architecture Guide</span>
          </button>
        </nav>
      </div>

      {/* Navigation Group: Focal Stacks (Groove "Playlists" style with + button) */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, marginTop: '8px' }}>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between', 
          paddingRight: '6px' 
        }}>
          <span className="groove-sidebar-heading">Focal Stacks</span>
          <button 
            className="groove-icon-btn"
            onClick={onOpenPathModal}
            title="Select Datasets Directory"
            style={{ width: '24px', height: '24px' }}
          >
            <FolderPlus size={14} color="var(--accent-cyan)" />
          </button>
        </div>

        {/* Stack Items List */}
        <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '1px' }}>
          {datasets.map(ds => {
            const isSelected = ds.id === currentDataset;
            return (
              <button
                key={ds.id}
                onClick={() => setCurrentDataset(ds.id)}
                className={`groove-sidebar-item ${isSelected ? 'active' : ''}`}
                style={{ justifyContent: 'space-between' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
                  <Folder 
                    size={15} 
                    color={isSelected ? 'var(--accent-cyan)' : 'var(--text-tertiary)'} 
                    style={{ flexShrink: 0 }}
                  />
                  <div style={{ overflow: 'hidden', textAlign: 'left' }}>
                    <span style={{ 
                      display: 'block', 
                      fontSize: '12.5px', 
                      fontWeight: isSelected ? '600' : '400',
                      whiteSpace: 'nowrap',
                      textOverflow: 'ellipsis',
                      overflow: 'hidden'
                    }}>
                      {ds.name || ds.id}
                    </span>
                    <span style={{ 
                      fontSize: '10.5px', 
                      color: isSelected ? 'var(--text-secondary)' : 'var(--text-tertiary)',
                      display: 'block' 
                    }}>
                      {ds.regime ? ds.regime.split(' ')[0] : 'Stack'}
                    </span>
                  </div>
                </div>
                <span style={{ 
                  fontSize: '10px', 
                  fontFamily: 'var(--font-mono)', 
                  opacity: 0.75,
                  flexShrink: 0
                }}>
                  {ds.num_frames}f
                </span>
              </button>
            );
          })}
        </div>

        {/* Path Selection Action Button */}
        <div style={{ padding: '8px 4px 4px' }}>
          <button
            onClick={onOpenPathModal}
            className="groove-path-btn"
            title={currentDataPath || 'Select Datasets Directory'}
          >
            <HardDrive size={13} color="var(--accent-cyan)" style={{ flexShrink: 0 }} />
            <div style={{ overflow: 'hidden', textAlign: 'left', flex: 1 }}>
              <span style={{ display: 'block', fontSize: '11px', fontWeight: '600', color: 'var(--text-primary)' }}>
                Dataset Folder...
              </span>
              <span style={{ 
                display: 'block', 
                fontSize: '9.5px', 
                color: 'var(--text-tertiary)', 
                fontFamily: 'var(--font-mono)',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {currentDataPath ? currentDataPath.replace(/^.*[\\\/]/, '') || currentDataPath : 'Choose Folder'}
              </span>
            </div>
          </button>
        </div>
      </div>

      {/* Bottom Groove User / Status Footer */}
      <div className="groove-sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
          <div style={{
            width: '26px',
            height: '26px',
            borderRadius: '50%',
            background: 'var(--accent-cyan)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#000',
            fontWeight: '700',
            fontSize: '11px',
            flexShrink: 0
          }}>
            AF
          </div>
          <div style={{ overflow: 'hidden' }}>
            <span style={{ display: 'block', fontSize: '11.5px', fontWeight: '600', color: 'var(--text-primary)' }}>
              SEM Core Active
            </span>
            <span style={{ fontSize: '10px', color: '#107C41', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#107C41' }}></span>
              Port 8000 Ready
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
