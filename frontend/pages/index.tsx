import { useState, useEffect } from 'react';
import Head from 'next/head';
import { Activity } from 'lucide-react';
import UploadModal from '../components/UploadModal';
import ChatWindow from '../components/ChatWindow';
import Dashboard from '../components/Dashboard';
import DatasetSelector from '../components/DatasetSelector';
import { 
  uploadFile, 
  sendMessage, 
  getDashboard, 
  getDatasetMetadata, 
  getChatHistory,
  UploadMetadata, 
  ChartSchema,
  DashboardWidgetData
} from '../utils/api-client';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  chart_schema?: ChartSchema;
  execution_time_ms?: number;
  timestamp?: string;
}

export default function Home() {
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [datasetMetadata, setDatasetMetadata] = useState<UploadMetadata | null>(null);
  const [dashboardWidgets, setDashboardWidgets] = useState<DashboardWidgetData[]>([]);
  const [currentVersion, setCurrentVersion] = useState<number>(0);

  // Load last active dataset on mount
  useEffect(() => {
    const savedDatasetId = localStorage.getItem('insightai_last_active_dataset_id');
    if (savedDatasetId) {
      handleDatasetChange(savedDatasetId);
    }
  }, []);

  const handleDatasetChange = async (newDatasetId: string) => {
    setDatasetId(newDatasetId);
    localStorage.setItem('insightai_last_active_dataset_id', newDatasetId);
    setChatLoading(true);

    try {
      // 1. Fetch Metadata
      const metadata = await getDatasetMetadata(newDatasetId);
      setDatasetMetadata(metadata);

      // 2. Fetch Chat History
      const history = await getChatHistory(newDatasetId);
      setMessages(history);

      // 3. Fetch Dashboard
      const dashData = await getDashboard(newDatasetId);
      setDashboardWidgets(dashData.widgets);
      setCurrentVersion(dashData.version);

      setUploadError(null);
    } catch (error) {
      console.error('Failed to load workspace', error);
      setUploadError('Failed to load workspace state.');
    } finally {
      setChatLoading(false);
    }
  };

  const handleUpload = async (file: File, displayName: string) => {
    try {
      setIsUploading(true);
      setUploadError(null);
      
      const response = await uploadFile(file, displayName);
      const newId = response.session_id; // backend returns dataset_id as session_id
      
      setDatasetId(newId);
      localStorage.setItem('insightai_last_active_dataset_id', newId);
      
      setDatasetMetadata(response.metadata);
      setDashboardWidgets(response.default_chart_schemas?.map((s, i) => ({
        id: `init-${i}`,
        type: 'chart',
        title: s.title || 'Analysis',
        chartSchema: s,
        position: { x: (i % 2) * 6, y: Math.floor(i / 2) * 4, w: s.w || 6, h: s.h || 4 }
      })) || []);
      
      // Load the full workspace state to ensure everything is synced
      await handleDatasetChange(newId);
      setIsUploadModalOpen(false);
    } catch (error: any) {
      const msg = error.message || 'Data ingestion failed. Ensure the CSV format is valid.';
      setUploadError(msg);
      throw error;
    } finally {
      setIsUploading(false);
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!datasetId) return;

    const userMessage: ChatMessage = { role: 'user', content: message, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMessage]);
    setChatLoading(true);

    try {
      const response = await sendMessage(datasetId, message);
      const assistantMessage: ChatMessage = {
        role: response.role as ChatMessage['role'],
        content: response.content,
        chart_schema: response.chart_schema,
        execution_time_ms: response.execution_time_ms,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, assistantMessage]);

      if (response.version !== undefined) {
        setCurrentVersion(response.version);
      }

      // Refresh dashboard to show new charts
      const dashData = await getDashboard(datasetId);
      setDashboardWidgets(dashData.widgets);
    } catch (error) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Statistical retrieval failed. Please refine your query.' }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const isLocked = chatLoading || isUploading;

  return (
    <div className="flex flex-col min-h-screen">
      <Head>
        <title>InsightAI | Workforce Intelligence</title>
        <meta name="description" content="Premium AI-powered workforce intelligence and data analysis." />
      </Head>

      {/* Header */}
      <header className="px-10 py-8 flex items-center justify-between border-b border-white/5 bg-background/60 backdrop-blur-xl sticky top-0 z-50">
        <div className="flex items-center gap-6">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[#cad2fd] to-[#c7bc92] flex items-center justify-center shadow-lg shadow-primary/20">
            <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-black text-primary tracking-tighter leading-none">InsightAI</h1>
            <p className="text-[11px] text-secondary font-black uppercase tracking-[0.3em] mt-2">Workforce Intelligence Engine</p>
          </div>
        </div>
        
        <div className="flex items-center gap-8">
          <DatasetSelector 
            currentDatasetId={datasetId} 
            onSelect={handleDatasetChange} 
            disabled={isLocked}
          />
          <div className="hidden md:flex flex-col items-end">
            <span className="text-[10px] text-slate-500 uppercase font-black tracking-widest mb-1">System Load</span>
            <span className="text-xs text-emerald-400 font-bold flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)] ${isLocked ? 'animate-ping' : 'animate-pulse'}`}></span>
              {isLocked ? 'Processing...' : 'Ready'}
            </span>
          </div>
        </div>
      </header>

      <main className="flex-1 px-6 md:px-10 py-12 bg-transparent overflow-x-hidden">
        <div className="max-w-[1600px] mx-auto space-y-16">
          
          <div className="w-full">
            {!datasetId ? (
              <div className="glass-card h-[600px] flex flex-col items-center justify-center text-center p-12 border-dashed border-white/10">
                <div className="w-20 h-20 rounded-3xl bg-indigo-500/10 flex items-center justify-center mb-8 border border-indigo-500/20">
                  <svg className="w-10 h-10 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.58 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.58 4 8 4s8-1.79 8-4M4 7c0-2.21 3.58-4 8-4s8 1.79 8 4m0 5c0 2.21-3.58 4-8 4s-8-1.79-8-4" />
                  </svg>
                </div>
                <h2 className="text-3xl font-black text-slate-100 tracking-tighter mb-4">No Workspace Active</h2>
                <p className="text-slate-500 max-w-md mx-auto mb-10 font-medium">
                  Please upload a dataset or select an existing workspace from the dropdown to begin your intelligence analysis.
                </p>
                <button
                  onClick={() => setIsUploadModalOpen(true)}
                  className="px-8 py-4 bg-indigo-600 text-white rounded-2xl text-sm font-black uppercase tracking-widest hover:bg-indigo-500 transition-all shadow-lg shadow-indigo-500/25"
                >
                  Create New Workspace
                </button>
              </div>
            ) : (
              <Dashboard
                sessionId={datasetId}
                widgets={dashboardWidgets}
                onWidgetsChange={setDashboardWidgets}
                currentVersion={currentVersion}
                onVersionChange={setCurrentVersion}
                kpiPanel={
                  datasetMetadata && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                      {[
                        { label: 'Total Records', value: datasetMetadata.rows.toLocaleString(), trend: 'Dataset Size' },
                        { label: 'Data Variables', value: datasetMetadata.columns.length.toString(), trend: 'Dimensions', isVariable: true },
                        { label: 'Data Quality', value: `${Math.max(0, 100 - Object.values(datasetMetadata.missing_values).reduce((a, b) => a + b, 0))}%`, trend: 'Completeness' },
                        { label: 'Ingestion Time', value: datasetMetadata.size_bytes > 1024 * 1024 ? `${(datasetMetadata.size_bytes / (1024 * 1024)).toFixed(1)}MB` : `${(datasetMetadata.size_bytes / 1024).toFixed(1)}KB`, trend: 'Payload' }
                      ].map((kpi, i) => (
                        <div key={i} className="relative bg-white/[0.03] border border-white/5 rounded-3xl p-6 flex flex-col justify-between h-32 group hover:bg-white/[0.05] transition-all">
                          <div className="flex items-center justify-between">
                            <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest">{kpi.label}</span>
                            <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 uppercase tracking-tighter">
                              {kpi.trend}
                            </span>
                          </div>
                          <div className="flex items-end justify-between">
                            <span className="text-3xl font-black text-white tracking-tighter">{kpi.value}</span>
                            <div className="w-1.5 h-1.5 rounded-full bg-indigo-500/40 group-hover:bg-indigo-400 transition-all"></div>
                          </div>

                          {/* Hover Tooltip for Data Variables */}
                          {(kpi as any).isVariable && (
                            <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-4 w-64 p-5 bg-slate-950/90 border border-white/10 rounded-[2rem] backdrop-blur-2xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-300 z-[100] shadow-2xl scale-95 group-hover:scale-100 pointer-events-none">
                              <div className="text-[9px] font-black text-indigo-400 uppercase tracking-[0.2em] mb-3 pb-2 border-b border-white/5">Available Variables</div>
                              <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto custom-scrollbar pr-1">
                                {datasetMetadata.columns.map((col, idx) => (
                                  <span key={idx} className="px-2.5 py-1 bg-white/5 border border-white/5 rounded-lg text-[10px] text-slate-300 font-medium">
                                    {col}
                                  </span>
                                ))}
                              </div>
                              {/* Tooltip Arrow */}
                              <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-l-[8px] border-l-transparent border-r-[8px] border-r-transparent border-t-[8px] border-t-slate-950/90"></div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )
                }
                chatPanel={
                  <ChatWindow
                    messages={messages}
                    onSend={handleSendMessage}
                    disabled={!datasetId || isLocked}
                    loading={chatLoading}
                  />
                }
                uploadPanel={
                  <div className={`p-6 bg-white/5 rounded-3xl border border-white/10 transition-all ${isLocked ? 'opacity-50' : ''}`}>
                    <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.3em] mb-4 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.6)]"></span>
                      Intelligence Hub
                    </h3>
                    <p className="text-[11px] text-slate-400 mb-6 font-medium leading-relaxed">
                      Deploy new data vectors.
                    </p>
                    <button
                      onClick={() => setIsUploadModalOpen(true)}
                      disabled={isLocked}
                      className="w-full py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl flex items-center justify-center gap-2 text-white text-[10px] font-black uppercase tracking-widest transition-all"
                    >
                      <Activity className="w-4 h-4" />
                      Upload Dataset
                    </button>
                    {uploadError && <p className="mt-4 text-[10px] text-rose-400 font-bold">{uploadError}</p>}
                  </div>
                }
              />
            )}
          </div>
        </div>
      </main>

      <UploadModal 
        isOpen={isUploadModalOpen} 
        onClose={() => setIsUploadModalOpen(false)} 
        onUpload={handleUpload}
        isUploading={isUploading}
      />
    </div>
  );
}
