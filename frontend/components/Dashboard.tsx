'use client';

import { useState, useEffect, useRef } from 'react';
import { History, RotateCcw, Maximize2, Move, Clock, ChevronDown, Save, GripVertical } from 'lucide-react';
import ChartDisplay from './ChartDisplay';
import { 
  ChartSchema, 
  DashboardWidgetData, 
  DashboardVersion, 
  getVersions, 
  rollbackDashboard, 
  updateLayout,
  getDashboardById
} from '../utils/api-client';

interface DashboardProps {
  sessionId: string | null;
  metadata?: any | null;
  widgets: DashboardWidgetData[];
  onWidgetsChange?: (widgets: DashboardWidgetData[]) => void;
  defaultChartSchemas?: ChartSchema[];
  autoInsights?: string;
}

export default function Dashboard({
  sessionId,
  metadata,
  widgets,
  onWidgetsChange,
  defaultChartSchemas,
  autoInsights,
}: DashboardProps) {
  const [versions, setVersions] = useState<DashboardVersion[]>([]);
  const [currentVersion, setCurrentVersion] = useState<number>(0);
  const [showHistory, setShowHistory] = useState(false);
  const [isLayoutChanged, setIsLayoutChanged] = useState(false);
  
  const [localWidgets, setLocalWidgets] = useState<DashboardWidgetData[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const dragInfo = useRef<{ id: string; type: 'move' | 'resize'; startX: number; startY: number; initialPos: any; pointerId: number; target: HTMLElement } | null>(null);

  useEffect(() => {
    setLocalWidgets(widgets.map(w => ({
      ...w,
      position: w.position || { x: 0, y: 0, w: 6, h: 4 }
    })));
  }, [widgets]);

  useEffect(() => {
    if (sessionId) {
      getVersions(sessionId).then(data => {
        setVersions(data.versions);
        if (data.versions.length > 0) setCurrentVersion(data.versions[0].version);
      });
    }
  }, [sessionId, widgets]);

  const startDrag = (e: React.PointerEvent, id: string, type: 'move' | 'resize') => {
    const widget = localWidgets.find(w => w.id === id);
    if (!widget) return;

    e.preventDefault();

    const target = e.currentTarget as HTMLElement;
    target.setPointerCapture(e.pointerId);

    dragInfo.current = {
      id,
      type,
      startX: e.clientX,
      startY: e.clientY,
      initialPos: { ...widget.position },
      pointerId: e.pointerId,
      target
    };
    setActiveId(id);
  };

  const handlePointerMove = (e: PointerEvent | React.PointerEvent) => {
    if (!dragInfo.current || !containerRef.current) return;

    const { id, type, startX, startY, initialPos } = dragInfo.current;
    const deltaX = e.clientX - startX;
    const deltaY = e.clientY - startY;

    const colWidth = containerRef.current.offsetWidth / 12;
    const rowHeight = 100;

    const gridDeltaX = deltaX / colWidth;
    const gridDeltaY = deltaY / rowHeight;

    setLocalWidgets(prev => prev.map(w => {
      if (w.id !== id) return w;
      const newPos = { ...w.position! };
      if (type === 'move') {
        newPos.x = Math.max(0, Math.min(12 - newPos.w, initialPos.x + gridDeltaX));
        newPos.y = Math.max(0, initialPos.y + gridDeltaY);
      } else {
        newPos.w = Math.max(2, Math.min(12 - initialPos.x, initialPos.w + gridDeltaX));
        newPos.h = Math.max(2, initialPos.h + gridDeltaY);
      }
      return { ...w, position: newPos };
    }));
    setIsLayoutChanged(true);
  };

  const stopDrag = () => {
    if (!dragInfo.current) return;

    setLocalWidgets(prev => prev.map(w => {
      if (w.id !== dragInfo.current?.id) return w;
      return {
        ...w,
        position: {
          x: Math.round(w.position!.x),
          y: Math.round(w.position!.y),
          w: Math.round(w.position!.w),
          h: Math.round(w.position!.h)
        }
      };
    }));

    if (dragInfo.current.target) {
      dragInfo.current.target.releasePointerCapture(dragInfo.current.pointerId);
    }

    dragInfo.current = null;
    setActiveId(null);
  };

  useEffect(() => {
    const onPointerMove = (event: PointerEvent) => handlePointerMove(event);
    const onPointerUp = () => stopDrag();

    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);

    return () => {
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
    };
  }, [containerRef, localWidgets]);

  const saveLayout = async () => {
    if (!sessionId) return;
    try {
      await updateLayout(sessionId, localWidgets.map(w => ({ id: w.id, position: w.position })));
      setIsLayoutChanged(false);
    } catch (err) { console.error(err); }
  };

  const handleRollback = async (vId: string) => {
    if (!sessionId) return;
    await rollbackDashboard(sessionId, vId);
    const data = await getDashboardById(vId);
    if (onWidgetsChange) onWidgetsChange(data.widgets);
    const versionEntry = versions.find((entry) => entry.id === vId);
    if (versionEntry) {
      setCurrentVersion(versionEntry.version);
    }
    const refreshed = await getVersions(sessionId);
    setVersions(refreshed.versions);
    setShowHistory(false);
  };

  return (
    <div className="space-y-6 pb-20 select-none">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-2xl font-black text-white tracking-tighter">INSIGHTS ENGINE</h2>
          <div className="px-3 py-1 bg-indigo-500/10 border border-indigo-500/20 rounded-full text-[10px] font-bold text-indigo-400 tracking-widest uppercase">Version {currentVersion}</div>
        </div>
        <div className="flex gap-3">
          {isLayoutChanged && (
            <button onClick={saveLayout} className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-all shadow-xl shadow-indigo-500/20 flex items-center gap-2">
              <Save className="w-4 h-4" /> PERSIST CHANGES
            </button>
          )}
          <button onClick={() => setShowHistory(!showHistory)} className="px-5 py-2.5 bg-white/5 border border-white/10 text-slate-300 rounded-xl text-xs font-bold hover:bg-white/10 transition-all flex items-center gap-2">
            <History className="w-4 h-4" /> LOGS
          </button>
        </div>
      </div>

      {showHistory && (
        <div className="glass-card p-5 border border-white/10 bg-slate-950/50">
          <div className="flex items-center justify-between gap-4 mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-[0.2em]">Dashboard history</h3>
              <p className="text-xs text-slate-500">Saved versions can be restored at any time.</p>
            </div>
            <span className="rounded-full bg-slate-900/80 text-[10px] px-3 py-1 uppercase tracking-[0.2em] text-slate-400">{versions.length} versions</span>
          </div>
          <div className="grid gap-3">
            {versions.length === 0 ? (
              <div className="rounded-2xl border border-white/10 p-4 text-sm text-slate-400">No saved versions yet.</div>
            ) : (
              versions.map((version) => (
                <div key={version.id} className={`rounded-2xl border p-4 flex items-center justify-between gap-4 ${version.version === currentVersion ? 'border-indigo-500 bg-indigo-500/10' : 'border-white/10 bg-slate-950/60'}`}>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-100">Version {version.version}</p>
                    <p className="text-xs text-slate-500">{new Date(version.created_at).toLocaleString()}</p>
                  </div>
                  <button
                    onClick={() => handleRollback(version.id)}
                    disabled={version.version === currentVersion}
                    className={`rounded-xl px-3 py-2 text-xs font-semibold transition ${version.version === currentVersion ? 'bg-white/10 text-slate-400 cursor-not-allowed' : 'bg-indigo-600 text-white hover:bg-indigo-500'}`}
                  >
                    {version.version === currentVersion ? 'Active' : 'Rollback'}
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <div 
        ref={containerRef}
        className="relative w-full min-h-[1200px] bg-slate-900/40 rounded-[2.5rem] border border-white/5 p-6 backdrop-blur-3xl touch-none"
      >
        {localWidgets.map((w) => {
          const pos = w.position!;
          return (
            <div
              key={w.id}
              className={`absolute transition-[border-color,background-color] duration-300 ${activeId === w.id ? 'z-50' : 'z-10'}`}
              style={{
                left: `${(pos.x / 12) * 100}%`,
                top: `${pos.y * 100}px`,
                width: `${(pos.w / 12) * 100}%`,
                height: `${pos.h * 100}px`,
                padding: '12px'
              }}
            >
              <div className={`w-full h-full glass-card flex flex-col overflow-hidden group transition-all ${activeId === w.id ? 'ring-2 ring-indigo-500/50 shadow-2xl bg-white/5' : 'bg-white/[0.02]'}`}>
                {/* Drag Handle */}
                <div 
                  onPointerDown={(e) => startDrag(e, w.id, 'move')}
                  onPointerMove={handlePointerMove}
                  onPointerUp={stopDrag}
                  className="px-6 py-4 border-b border-white/5 bg-white/5 flex items-center justify-between cursor-grab active:cursor-grabbing touch-none"
                >
                  <span className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em] truncate">{w.title}</span>
                  <GripVertical className="w-4 h-4 text-slate-600 group-hover:text-indigo-400 transition-colors" />
                </div>

                <div className="flex-1 overflow-hidden relative">
                  {w.type === 'chart' ? (
                    <ChartDisplay schema={w.chartSchema!} />
                  ) : (
                    <div className="text-sm text-slate-300 leading-relaxed overflow-y-auto h-full custom-scrollbar pr-2 pointer-events-auto p-6">
                      {w.content}
                    </div>
                  )}
                </div>

                {/* Resize Handle */}
                <div 
                  onPointerDown={(e) => startDrag(e, w.id, 'resize')}
                  onPointerMove={handlePointerMove}
                  onPointerUp={stopDrag}
                  className="absolute bottom-2 right-2 w-10 h-10 cursor-se-resize flex items-end justify-end p-2 opacity-0 group-hover:opacity-100 transition-opacity touch-none"
                >
                  <div className="w-4 h-4 border-r-2 border-b-2 border-indigo-500/30 rounded-br-sm group-hover:border-indigo-500 transition-colors"></div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
