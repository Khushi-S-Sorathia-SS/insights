import { useState, useEffect, useRef, useCallback } from 'react';
import { History, GripVertical, Edit2, X, Activity } from 'lucide-react';
import ChartDisplay from './ChartDisplay';
import { ResponsiveGridLayout, useContainerWidth, type Layout } from 'react-grid-layout';

// Define Layouts locally since it's not exported by the version of react-grid-layout in use
type Layouts = Partial<Record<string, Layout>>;

import { 
  ChartSchema, 
  DashboardWidgetData, 
  DashboardVersion, 
  getVersions, 
  rollbackDashboard, 
  updateLayout,
  getDashboardById,
  saveDashboardVersion
} from '../utils/api-client';

interface DashboardProps {
  sessionId: string | null; // This is the datasetId
  widgets: DashboardWidgetData[];
  onWidgetsChange?: (widgets: DashboardWidgetData[]) => void;
  currentVersion: number;
  chatPanel?: React.ReactNode;
  uploadPanel?: React.ReactNode;
  kpiPanel?: React.ReactNode;
}

export default function Dashboard({
  sessionId,
  widgets,
  onWidgetsChange,
  currentVersion,
  chatPanel,
  uploadPanel,
  kpiPanel
}: DashboardProps) {
  const [versions, setVersions] = useState<DashboardVersion[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [localWidgets, setLocalWidgets] = useState<DashboardWidgetData[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);
  
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);
  const { width, containerRef, mounted } = useContainerWidth({ measureBeforeMount: true });

  // Sync local widgets with props when they change (e.g. new analysis)
  useEffect(() => {
    if (widgets) {
      setLocalWidgets(widgets);
    }
  }, [widgets]);

  // Load versions
  useEffect(() => {
    if (sessionId) {
      getVersions(sessionId).then(data => {
        setVersions(data.versions);
      }).catch(console.error);
    }
  }, [sessionId, currentVersion]);

  // Debounced auto-save function
  const debouncedSaveLayout = useCallback((updatedWidgets: DashboardWidgetData[]) => {
    if (!sessionId) return;

    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }

    autoSaveTimerRef.current = setTimeout(async () => {
      try {
        setIsSyncing(true);
        const layoutData = updatedWidgets.map(w => ({
          id: w.id,
          position: w.position
        }));
        await updateLayout(sessionId, layoutData);
        console.log('Layout persisted successfully');
      } catch (error) {
        console.error('Failed to auto-save layout', error);
      } finally {
        setIsSyncing(false);
      }
    }, 1500); // 1.5s debounce
  }, [sessionId]);

  const onLayoutChange = (newLayout: Layout, allLayouts: Layouts) => {
    if (!isEditMode) return;

    setLocalWidgets(prev => {
      let changed = false;
      const updated = prev.map(w => {
        const item = (newLayout as any[]).find(l => l.i === w.id);
        if (item) {
          const newPos = { x: item.x, y: item.y, w: item.w, h: item.h };
          if (
            w.position?.x !== newPos.x || 
            w.position?.y !== newPos.y || 
            w.position?.w !== newPos.w || 
            w.position?.h !== newPos.h
          ) {
            changed = true;
            return { ...w, position: newPos };
          }
        }
        return w;
      });

      if (changed) {
        debouncedSaveLayout(updated);
        return updated;
      }
      return prev;
    });
  };

  const handleRollback = async (vId: string) => {
    if (!sessionId) return;
    try {
      await rollbackDashboard(sessionId, vId);
      const data = await getDashboardById(vId);
      if (onWidgetsChange) onWidgetsChange(data.widgets);
      setShowHistory(false);
    } catch (err) {
      console.error('Rollback failed', err);
    }
  };

  const gridItems = localWidgets.map(w => ({
    i: w.id,
    x: w.position?.x || 0,
    y: w.position?.y || 0,
    w: w.position?.w || 6,
    h: w.position?.h || 4,
    minW: 2,
    minH: 2
  }));

  const layouts = {
    lg: gridItems,
    md: gridItems,
    sm: gridItems,
    xs: gridItems,
    xxs: gridItems
  };
  
  const handleSaveVersion = async () => {
    if (!sessionId) return;
    try {
      setIsSyncing(true);
      const layoutData = localWidgets.map(w => ({
        id: w.id,
        position: w.position
      }));
      const data = await saveDashboardVersion(sessionId, layoutData);
      if (onWidgetsChange) onWidgetsChange(data.widgets);
      setIsEditMode(false);
      console.log('New version saved successfully');
    } catch (error) {
      console.error('Failed to save dashboard version', error);
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div className="space-y-6 pb-20 select-none">
      <div className="relative w-full min-h-[800px] bg-slate-950/20 rounded-[3rem] border border-white/5 p-12 backdrop-blur-3xl overflow-hidden">
        {/* Dashboard Content Grid */}
        <div className="flex flex-col xl:flex-row gap-12 h-full">
          
          {/* Main Visual Section */}
          <div className="flex-1 flex flex-col gap-10">
            {/* Unified Header Inside Glass */}
            <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex items-center gap-6">
                <div className="flex flex-col">
                  <h2 className="text-5xl font-black text-white tracking-tighter leading-none">ENGINE</h2>
                  <div className="flex items-center gap-3 mt-3">
                    <span className="text-[11px] font-black text-indigo-400 tracking-[0.4em] uppercase">Autonomous Intelligence</span>
                    <div className="px-3 py-1 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-[9px] font-black text-indigo-400 tracking-widest uppercase">
                      WORKSPACE V{currentVersion} {isSyncing && '• SYNCING...'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Layout Management Hierarchy */}
              <div className="flex items-center gap-2 p-1.5 bg-white/5 rounded-[2rem] border border-white/5 backdrop-blur-md">
                {!isEditMode ? (
                  <>
                    <button 
                      onClick={() => setIsEditMode(true)} 
                      className="px-6 py-3 bg-indigo-600 text-white hover:bg-indigo-500 rounded-2xl text-[10px] font-black tracking-widest transition-all flex items-center gap-3 active:scale-95 shadow-lg shadow-indigo-500/25"
                    >
                      <Edit2 className="w-4 h-4" /> EDIT LAYOUT
                    </button>
                    <button 
                      onClick={() => setShowHistory(!showHistory)} 
                      className="px-6 py-3 text-slate-400 hover:text-white rounded-2xl text-[10px] font-black tracking-widest transition-all flex items-center gap-3 active:scale-95"
                    >
                      <History className="w-4 h-4" /> REVISIONS
                    </button>
                  </>
                ) : (
                  <div className="flex items-center gap-2 animate-in slide-in-from-right-4">
                    <span className="px-4 text-[9px] font-black text-indigo-400 uppercase tracking-[0.2em] border-r border-white/10 mr-2">Config Mode</span>
                    <button 
                      onClick={handleSaveVersion}
                      disabled={isSyncing}
                      className="px-5 py-2.5 bg-emerald-600 text-white hover:bg-emerald-500 rounded-xl text-[9px] font-black tracking-widest transition-all flex items-center gap-2 shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                    >
                      <Activity className="w-3.5 h-3.5" /> SAVE
                    </button>
                    <button 
                      onClick={() => setIsEditMode(false)}
                      className="px-5 py-2.5 bg-white/5 text-slate-300 hover:bg-white/10 rounded-xl text-[9px] font-black tracking-widest transition-all flex items-center gap-2"
                    >
                      <X className="w-3.5 h-3.5" /> CANCEL
                    </button>
                  </div>
                )}
              </div>
            </div>

            {kpiPanel && (
              <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                {kpiPanel}
              </div>
            )}

            {showHistory && (
              <div className="glass-card p-8 border border-white/10 bg-slate-950/40 animate-fade-in mb-10">
                <div className="flex items-center justify-between gap-6 mb-8">
                  <div>
                    <h3 className="text-xs font-black text-slate-100 uppercase tracking-[0.3em] ">Temporal Registry</h3>
                    <p className="text-xs text-slate-500 mt-1">Select a previous state to restore the workspace topology.</p>
                  </div>
                  <span className="rounded-xl bg-slate-900/80 text-[10px] px-4 py-1.5 font-black uppercase tracking-[0.2em] text-slate-400 border border-white/5">{versions.length} REVISIONS</span>
                </div>
                <div className="grid gap-4 max-h-[300px] overflow-y-auto custom-scrollbar pr-2">
                  {versions.map((version) => (
                    <div key={version.id} className={`rounded-2xl border p-5 flex items-center justify-between gap-6 transition-all ${version.version === currentVersion ? 'border-indigo-500/50 bg-indigo-500/10 shadow-lg shadow-indigo-500/5' : 'border-white/5 bg-slate-950/40 hover:bg-slate-950/60'}`}>
                      <div className="min-w-0">
                        <p className="text-sm font-black text-slate-100 tracking-tight">Revision {version.version}</p>
                        <p className="text-[11px] text-slate-500 mt-1 font-medium">{new Date(version.created_at).toLocaleString()}</p>
                      </div>
                      <button
                        onClick={() => handleRollback(version.id)}
                        disabled={version.version === currentVersion}
                        className={`rounded-xl px-5 py-2.5 text-[11px] font-black tracking-widest uppercase transition ${
                          version.version === currentVersion
                          ? 'bg-white/5 text-slate-500 cursor-not-allowed' 
                          : 'bg-indigo-600 text-white hover:bg-indigo-500'
                        }`}
                      >
                        {version.version === currentVersion ? 'Current' : 'Restore'}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex-1 min-h-[600px]" ref={containerRef as any}>
              {mounted && (
                <ResponsiveGridLayout
                  className="layout"
                  layouts={layouts}
                  width={width}
                  breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
                  cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
                  rowHeight={100}
                  onLayoutChange={onLayoutChange}
                  {...({ draggableHandle: ".drag-handle" } as any)}
                  margin={[20, 20]}
                  useCSSTransforms={true}
                  isDraggable={isEditMode}
                  isResizable={isEditMode}
                  compactType="vertical"
                  verticalCompact={true}
                  preventCollision={false}
                  droppingItem={{ i: 'dropping', x: 0, y: 0, w: 2, h: 2 }}
                >
                  {localWidgets.map((w) => (
                    <div key={w.id} className={`glass-card flex flex-col overflow-hidden group transition-all bg-slate-900/40 border-white/[0.08] ${isEditMode ? 'hover:shadow-indigo-500/10 ring-1 ring-indigo-500/20' : ''}`}>
                      <div className={`drag-handle px-6 py-4 border-b border-white/5 bg-white/[0.03] flex items-center justify-between backdrop-blur-md ${isEditMode ? 'cursor-grab active:cursor-grabbing bg-indigo-500/5' : 'cursor-default'}`}>
                        <span className="text-[10px] font-black text-slate-300 uppercase tracking-[0.3em] truncate">{w.title}</span>
                        <div className="flex items-center gap-4">
                          <div className="w-1.5 h-1.5 rounded-full bg-indigo-500/60 group-hover:bg-indigo-400 transition-all shadow-[0_0_8px_rgba(99,102,241,0.4)]"></div>
                          {isEditMode && <GripVertical className="w-4 h-4 text-slate-600 group-hover:text-indigo-400 transition-colors" />}
                        </div>
                      </div>

                      <div className="flex-1 overflow-hidden relative p-6">
                        {w.type === 'chart' ? (
                          <div className="w-full h-full">
                            <ChartDisplay schema={w.chartSchema!} />
                          </div>
                        ) : (
                          <div className="text-sm text-slate-300 leading-relaxed overflow-y-auto h-full custom-scrollbar pr-2 p-4 font-medium">
                            {w.content}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </ResponsiveGridLayout>
              )}
            </div>
          </div>

          {/* Sidebar Section Inside Glass */}
          <div className="xl:w-[400px] flex flex-col gap-8 border-l border-white/5 pl-12 sticky top-12 h-fit max-h-[calc(100vh-100px)]">
            <div className="flex-shrink-0">
              {uploadPanel}
            </div>
            <div className="h-[500px] flex flex-col">
              {chatPanel}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
