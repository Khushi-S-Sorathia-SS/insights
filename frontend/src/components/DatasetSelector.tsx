import { useState, useEffect } from 'react';
import { listDatasets, DatasetListItem } from '../utils/api-client';

interface DatasetSelectorProps {
  currentDatasetId: string | null;
  onSelect: (datasetId: string) => void;
  disabled?: boolean;
}

export default function DatasetSelector({ currentDatasetId, onSelect, disabled }: DatasetSelectorProps) {
  const [datasets, setDatasets] = useState<DatasetListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        setLoading(true);
        const data = await listDatasets();
        setDatasets(data);
      } catch (error) {
        console.error('Failed to load datasets', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDatasets();
  }, [currentDatasetId]);

  const currentDataset = datasets.find(d => d.id === currentDatasetId);

  const handleToggle = async () => {
    if (disabled) return;
    const nextOpen = !isOpen;
    setIsOpen(nextOpen);
    if (nextOpen) {
      try {
        setLoading(true);
        const data = await listDatasets();
        setDatasets(data);
      } catch (error) {
        console.error('Failed to refresh datasets', error);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div className="relative">
      <button
        onClick={handleToggle}
        disabled={disabled}
        className={`flex items-center gap-4 px-5 py-3 rounded-xl border transition-all duration-300 ${
          disabled ? 'opacity-50 cursor-not-allowed bg-white/5 border-white/10' : 
          'bg-surface/60 border-primary/30 hover:border-primary/60 hover:shadow-lg hover:shadow-primary/10'
        } backdrop-blur-xl group`}
      >
        <div className="flex flex-col items-start">
          <span className="text-[10px] font-black text-primary uppercase tracking-widest leading-none mb-1">
            Active Workspace
          </span>
          <span className="text-sm font-bold text-slate-100 truncate max-w-[200px]">
            {currentDataset ? (currentDataset.display_name || currentDataset.filename) : 'Select Workspace'}
          </span>
        </div>
        <svg 
          className={`w-5 h-5 text-slate-400 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          ></div>
          <div className="absolute right-0 mt-4 w-72 rounded-2xl bg-background/95 backdrop-blur-2xl border border-white/10 shadow-2xl shadow-black/50 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-300">
            <div className="p-4 border-b border-white/5 bg-white/5">
              <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Recent Workspaces</h4>
            </div>
            <div className="max-h-64 overflow-y-auto scrollbar-thin scrollbar-thumb-primary/20">
              {datasets.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-500 font-medium">No workspaces found.</div>
              ) : (
                datasets.map((dataset) => (
                  <button
                    key={dataset.id}
                    onClick={() => {
                      onSelect(dataset.id);
                      setIsOpen(false);
                    }}
                    className={`w-full flex flex-col items-start px-6 py-4 transition-all duration-200 border-l-2 ${
                      currentDatasetId === dataset.id 
                        ? 'bg-primary/10 border-primary' 
                         : 'border-transparent hover:bg-white/5 hover:border-white/20'
                    }`}
                  >
                    <span className="text-sm font-bold text-slate-100">{dataset.display_name || dataset.filename}</span>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-[10px] text-slate-500 font-medium">
                        {dataset.rows.toLocaleString()} records
                      </span>
                      <span className="w-1 h-1 rounded-full bg-white/10"></span>
                      <span className="text-[10px] text-slate-500 font-medium">
                        {new Date(dataset.uploaded_at).toLocaleDateString()}
                      </span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
