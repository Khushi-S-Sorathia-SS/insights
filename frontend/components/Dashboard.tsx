'use client';

import ChartDisplay from './ChartDisplay';

interface DashboardWidget {
  id: string;
  title: string;
  type: 'chart' | 'insight';
  content?: string;
  chartUrl?: string;
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
  defaultChartUrls: string[];
  autoInsights?: string;
  widgets: DashboardWidget[];
}

export default function Dashboard({
  metadata,
  defaultChartUrls,
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
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row">
        <div className="bg-white rounded-2xl shadow-sm p-6 flex-1">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Dashboard overview</h2>
          {metadata ? (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-gray-200 p-4">
                <p className="text-sm text-gray-500">Rows</p>
                <p className="mt-2 text-3xl font-semibold text-gray-900">{metadata.rows}</p>
              </div>
              <div className="rounded-2xl border border-gray-200 p-4">
                <p className="text-sm text-gray-500">Columns</p>
                <p className="mt-2 text-3xl font-semibold text-gray-900">{metadata.columns.length}</p>
              </div>
              <div className="rounded-2xl border border-gray-200 p-4">
                <p className="text-sm text-gray-500">Missing values</p>
                <p className="mt-2 text-3xl font-semibold text-gray-900">{totalMissing}</p>
              </div>
              <div className="rounded-2xl border border-gray-200 p-4">
                <p className="text-sm text-gray-500">Numeric columns</p>
                <p className="mt-2 text-3xl font-semibold text-gray-900">{numericColumns.length}</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-500">Upload a dataset to see KPI cards and data preview.</p>
          )}
        </div>

        <div className="bg-white rounded-2xl shadow-sm p-6 flex-1">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Auto insights</h2>
          {metadata ? (
            <div className="space-y-3">
              <div className="rounded-2xl border border-gray-200 p-4 bg-gray-50">
                <p className="text-sm text-gray-500">Dataset</p>
                <p className="mt-2 text-sm text-gray-700">
                  {metadata.filename} · {metadata.rows} rows · {metadata.columns.length} columns
                </p>
              </div>
              <div className="rounded-2xl border border-gray-200 p-4 bg-gray-50">
                <p className="text-sm text-gray-500">Column types</p>
                <p className="mt-2 text-sm text-gray-700">
                  {Object.entries(metadata.dtypes)
                    .map(([key, dtype]) => `${key}: ${dtype}`)
                    .slice(0, 3)
                    .join(', ')}
                </p>
              </div>
              <div className="rounded-2xl border border-gray-200 p-4 bg-gray-50 text-sm text-gray-700">
                {autoInsights ? autoInsights : 'Initializing default insights and charts...'}
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-500">Default insights appear after upload.</p>
          )}
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2 space-y-4">
          <div className="bg-white rounded-2xl shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Charts</h2>
            </div>
            {defaultChartUrls.length > 0 ? (
              <div className="grid gap-4 md:grid-cols-2">
                {defaultChartUrls.map((chartUrl, index) => (
                  <ChartDisplay key={`default-chart-${index}`} base64Image={chartUrl} title={`Default chart ${index + 1}`} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">Default charts will appear here once the dataset is uploaded.</p>
            )}
          </div>

          <div className="bg-white rounded-2xl shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Dashboard widgets</h2>
            {widgets.length === 0 ? (
              <p className="text-sm text-gray-500">Chat responses with charts or insights will be added here.</p>
            ) : (
              <div className="space-y-4">
                {widgets.map((widget) => (
                  <div key={widget.id} className="rounded-2xl border border-gray-200 p-4 bg-gray-50">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-semibold text-gray-900">{widget.title}</h3>
                      <span className="text-xs text-gray-500">{widget.type}</span>
                    </div>
                    {widget.chartUrl ? (
                      <ChartDisplay base64Image={widget.chartUrl} title={widget.title} />
                    ) : (
                      <p className="text-sm text-gray-700 whitespace-pre-line">{widget.content}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Data preview</h2>
          {metadata && metadata.preview_rows.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm text-gray-700">
                <thead className="border-b border-gray-200 bg-gray-50">
                  <tr>
                    {metadata.columns.map((column) => (
                      <th key={column} className="px-3 py-2 font-medium text-gray-900">{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {metadata.preview_rows.map((row, rowIndex) => (
                    <tr key={rowIndex} className={rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      {metadata.columns.map((column) => (
                        <td key={`${rowIndex}-${column}`} className="px-3 py-2 align-top">
                          {String(row[column] ?? '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-500">A preview table will appear after dataset upload.</p>
          )}
        </div>
      </div>
    </div>
  );
}
