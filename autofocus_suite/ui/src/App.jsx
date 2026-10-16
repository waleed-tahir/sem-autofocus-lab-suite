import React, { useState, useEffect } from 'react';
import Titlebar from './components/Titlebar';
import Sidebar from './components/Sidebar';
import LiveStudio from './views/LiveStudio';
import FmoCurvesView from './views/FmoCurvesView';
import LeaderboardView from './views/LeaderboardView';
import StackInspector from './views/StackInspector';
import LabGuideView from './views/LabGuideView';
import DatasetPathModal from './components/DatasetPathModal';

export default function App() {
  const [currentTab, setCurrentTab] = useState('studio');
  const [theme, setTheme] = useState('dark');
  const [currentDataset, setCurrentDataset] = useState('pollen.spd1');
  const [datasets, setDatasets] = useState([
    { id: 'pollen.spd1', name: 'pollen.spd1', regime: 'Clean / High SNR SEM', num_frames: 200 },
    { id: 'pollen.spd2', name: 'pollen.spd2', regime: 'Standard SNR SEM', num_frames: 200 },
    { id: 'pollen.spd3', name: 'pollen.spd3', regime: 'Moderate Noise SEM', num_frames: 200 },
    { id: 'pollen.spd5', name: 'pollen.spd5', regime: 'Heavy Shot Noise SEM', num_frames: 200 },
  ]);
  const [metadata, setMetadata] = useState({ fmos: {}, search_algorithms: {} });
  const [serverStatus, setServerStatus] = useState(true);
  const [isPathModalOpen, setIsPathModalOpen] = useState(false);
  const [currentDataPath, setCurrentDataPath] = useState('');

  // Sync theme attribute on document root
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Fetch initial dataset path
  const refreshDatasetPath = () => {
    fetch('/api/dataset-path')
      .then(res => res.json())
      .then(data => {
        if (data && data.path) {
          setCurrentDataPath(data.path);
        }
      })
      .catch(() => {});
  };

  const refreshDatasets = (newPath, newDatasetsList) => {
    if (newPath) setCurrentDataPath(newPath);
    if (newDatasetsList && newDatasetsList.length > 0) {
      setDatasets(newDatasetsList);
      setCurrentDataset(newDatasetsList[0].id);
      return;
    }
    fetch('/api/datasets')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          setDatasets(data);
          if (!data.some(d => d.id === currentDataset)) {
            setCurrentDataset(data[0].id);
          }
        }
      })
      .catch(() => setServerStatus(false));
  };

  useEffect(() => {
    refreshDatasetPath();
    refreshDatasets();

    fetch('/api/metadata')
      .then(res => res.json())
      .then(data => setMetadata(data))
      .catch(() => setServerStatus(false));

    fetch('/api/status')
      .then(res => res.json())
      .then(() => setServerStatus(true))
      .catch(() => setServerStatus(false));
  }, []);

  return (
    <div className="matte-app-shell">
      {/* Dark Matte Command Bar */}
      <Titlebar 
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        theme={theme}
        setTheme={setTheme}
        currentDataset={currentDataset}
        setCurrentDataset={setCurrentDataset}
        datasets={datasets}
        serverStatus={serverStatus}
        onOpenPathModal={() => setIsPathModalOpen(true)}
      />

      {/* Three-Zone Desktop Architecture Work Area */}
      <div className="matte-work-area">
        {/* Zone 1: Left Navigation Rail (240px Fixed, Acrylic) */}
        <Sidebar 
          currentTab={currentTab}
          setCurrentTab={setCurrentTab}
          currentDataset={currentDataset}
          setCurrentDataset={setCurrentDataset}
          datasets={datasets}
          currentDataPath={currentDataPath}
          onOpenPathModal={() => setIsPathModalOpen(true)}
        />

        {/* Zone 2 & 3: Primary Workspace (Hero Zone + Lower Split Workspace) */}
        <main className="matte-primary-workspace">
          {currentTab === 'studio' && (
            <LiveStudio 
              currentDataset={currentDataset}
              metadata={metadata}
              theme={theme}
              onOpenPathModal={() => setIsPathModalOpen(true)}
            />
          )}

          {currentTab === 'curves' && (
            <FmoCurvesView 
              currentDataset={currentDataset}
              metadata={metadata}
              theme={theme}
            />
          )}

          {currentTab === 'leaderboard' && (
            <LeaderboardView 
              currentDataset={currentDataset}
              metadata={metadata}
              theme={theme}
            />
          )}

          {currentTab === 'inspector' && (
            <StackInspector 
              currentDataset={currentDataset}
              theme={theme}
            />
          )}

          {currentTab === 'guide' && (
            <LabGuideView 
              metadata={metadata}
            />
          )}
        </main>
      </div>

      {/* Dataset Directory Path Selection Modal */}
      <DatasetPathModal 
        isOpen={isPathModalOpen}
        onClose={() => setIsPathModalOpen(false)}
        currentPath={currentDataPath}
        onDatasetPathChanged={(newPath, updatedDatasets) => {
          refreshDatasets(newPath, updatedDatasets);
        }}
      />
    </div>
  );
}
