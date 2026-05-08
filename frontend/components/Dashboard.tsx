'use client';

import ChartDisplay from './ChartDisplay';
import { ChartSchema } from '../utils/api-client';

interface DashboardWidget {
  id: string;
  title: string;
  type: 'chart' | 'insight';
  content?: string;
  chartSchema?: ChartSchema;
}

interface MetadataPreview {
  filename: string;
  rows: number;
  columns: string[];
  dtypes: Record<string, string>;
  missing_values: Record<string, number>;
  preview_rows: Array<Record<string, string | number | null>>;
}

interface DashboardProps {
  metadata?: MetadataPreview | null;
  defaultChartSchemas: ChartSchema[];
  autoInsights?: string;
  widgets: DashboardWidget[];
}

export default function Dashboard({
  metadata,
  defaultChartSchemas,
  autoInsights,
  widgets,
}: DashboardProps) {
  const totalMissing = metadata
    ? Object.values(metadata.missing_values).reduce((sum, value) => sum + value, 0)
    : 0;

  const numericColumns = metadata
    ? metadata.columns.filter((column) => {
        const dtype = metadata.dtypes[column]?.toLowerCase() || '';
        return ['int', 'float', 'double', 'number'].some((token) => dtype.includes(token));
      })
    : [];

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      {/* KPI Section */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="glass-card p-5 bg-indigo-500/5">
          <p className="text-[10px] font-bold text-indigo-300 uppercase tracking-widest">Total Records</p>
          <p className="mt-2 text-3xl font-black text-white">{metadata?.rows || 0}</p>
          <p className="mt-1 text-[10px] text-slate-400 truncate">{metadata?.filename || 'Pending upload'}</p>
        </div>
        <div className="glass-card p-5 bg-cyan-500/5">
          <p className="text-[10px] font-bold text-cyan-300 uppercase tracking-widest">Dimensions</p>
          <p className="mt-2 text-3xl font-black text-white">{metadata?.columns.length || 0}</p>
          <p className="mt-1 text-[10px] text-slate-400">Data features identified</p>
        </div>
        <div className="glass-card p-5 bg-emerald-500/5">
          <p className="text-[10px] font-bold text-emerald-300 uppercase tracking-widest">Quality Score</p>
          <p className="mt-2 text-3xl font-black text-white">
            {metadata ? Math.max(0, 100 - Math.round((totalMissing / (metadata.rows * metadata.columns.length || 1)) * 100)) : 0}%
          </p>
          <p className="mt-1 text-[10px] text-slate-400">Inference reliability</p>
        </div>
        <div className="glass-card p-5 bg-amber-500/5">
          <p className="text-[10px] font-bold text-amber-300 uppercase tracking-widest">Metric Depth</p>
          <p className="mt-2 text-3xl font-black text-white">{numericColumns.length}</p>
          <p className="mt-1 text-[10px] text-slate-400">Continuous variables</p>
        </div>
      </div>

      {/* AI Intelligence Summary */}
      <div className="glass-card p-6 border-l-4 border-l-indigo-500 bg-indigo-500/10">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></div>
          <h2 className="text-xs font-black text-indigo-200 uppercase tracking-widest">AI Analytical Synthesis</h2>
        </div>
        <div className="text-sm text-slate-100 leading-relaxed font-medium">
          {autoInsights || (metadata ? "Ingesting workforce vectors and identifying latent patterns..." : "Upload a dataset to activate the neural analysis engine.")}
        </div>
      </div>

      {/* Main Charts Section */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">Autonomous Visualizations</h2>
          {(metadata || widgets.length > 0) && <span className="text-[10px] font-bold text-indigo-400 bg-indigo-400/10 px-2 py-1 rounded">LIVE ENGINE</span>}
        </div>

        {/* Insight / text widgets shown first */}
        {widgets.filter(w => w.type === 'insight').map((widget) => (
          <div key={widget.id} className="glass-card p-6 border-l-4 border-l-cyan-500 bg-cyan-500/5">
            <p className="text-xs font-bold text-cyan-300 uppercase tracking-widest mb-2">{widget.title}</p>
            <p className="text-sm text-slate-100 leading-relaxed whitespace-pre-line">{widget.content}</p>
          </div>
        ))}

        {/* Chart widgets — combine defaultChartSchemas + DB-restored chart widgets */}
        {(() => {
          const schemaCharts = defaultChartSchemas.map((schema, i) => ({ id: `default-${i}`, chartSchema: schema, title: schema.title || 'Chart' }));
          const dbCharts = widgets.filter(w => w.type === 'chart' && w.chartSchema);
          const allCharts = [...schemaCharts, ...dbCharts];

          return allCharts.length > 0 ? (
            <div className="grid gap-6 md:grid-cols-2">
              {allCharts.map((item) => (
                <div key={item.id} className="glass-card overflow-hidden">
                  <div className="px-6 py-3 border-b border-white/5 bg-white/5">
                    <h3 className="text-xs font-bold text-indigo-300 uppercase tracking-widest">{item.title}</h3>
                  </div>
                  <div className="p-4">
                    <ChartDisplay schema={item.chartSchema!} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="glass-card p-16 text-center">
              <p className="text-slate-500 text-sm font-medium">No visualizations generated. Ingest data to populate this workspace.</p>
            </div>
          );
        })()}
      </div>

      {/* Data Architecture & Preview (Simplified) */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="glass-card p-6">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6">Data Schema</h2>
          {metadata ? (
            <div className="grid grid-cols-2 gap-x-4 gap-y-2">
              {Object.entries(metadata.dtypes).slice(0, 16).map(([col, type]) => (
                <div key={col} className="flex items-center justify-between py-1.5 border-b border-white/5">
                  <span className="text-[11px] text-slate-300 font-medium truncate pr-2">{col}</span>
                  <span className="text-[9px] font-mono text-indigo-400">{type}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500 italic">No schema detected.</p>
          )}
        </div>
        
        <div className="glass-card p-6">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6">Vector Samples</h2>
          {metadata && metadata.preview_rows.length > 0 ? (
            <div className="space-y-3">
              {metadata.preview_rows.slice(0, 4).map((row, i) => (
                <div key={i} className="text-[10px] text-slate-400 bg-black/20 p-2 rounded border border-white/5 font-mono">
                  {Object.values(row).slice(0, 5).join(' | ')}...
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500 italic">No samples available.</p>
          )}
        </div>
      </div>
    </div>
  );
}
