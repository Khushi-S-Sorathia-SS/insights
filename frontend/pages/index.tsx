import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import FileUpload from '../components/FileUpload';
import ChatWindow from '../components/ChatWindow';
import Dashboard from '../components/Dashboard';
import { uploadFile, sendMessage, getDashboard, getDashboardById, UploadMetadata, ChartSchema } from '../utils/api-client';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  chart_schema?: ChartSchema;
  execution_time_ms?: number;
}

interface DashboardWidget {
  id: string;
  title: string;
  type: 'chart' | 'insight';
  content?: string;
  chartSchema?: ChartSchema;
}

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [datasetMetadata, setDatasetMetadata] = useState<UploadMetadata | null>(null);
  const [defaultChartSchemas, setDefaultChartSchemas] = useState<ChartSchema[]>([]);
  const [autoInsights, setAutoInsights] = useState<string>('');
  const [dashboardWidgets, setDashboardWidgets] = useState<DashboardWidget[]>([]);

  useEffect(() => {
    const savedSessionId = localStorage.getItem('insightai_session_id');
    const savedDashboardId = localStorage.getItem('insightai_dashboard_id');

    if (savedSessionId) setSessionId(savedSessionId);

    // Prefer fetching by dashboard_id — works even after backend restarts
    if (savedDashboardId) {
      getDashboardById(savedDashboardId)
        .then((data) => {
          if (data && data.widgets && data.widgets.length > 0) {
            setDashboardWidgets(data.widgets as DashboardWidget[]);
          }
        })
        .catch(console.error);
    } else if (savedSessionId) {
      // Fallback: try session-based fetch (only works if backend still has session in memory)
      getDashboard(savedSessionId)
        .then((data) => {
          if (data && data.widgets && data.widgets.length > 0) {
            setDashboardWidgets(data.widgets as DashboardWidget[]);
          }
        })
        .catch(console.error);
    }
  }, []);

  const handleUpload = async (file: File) => {
    try {
      setUploadError(null);
      const response = await uploadFile(file);
      setSessionId(response.session_id);
      localStorage.setItem('insightai_session_id', response.session_id);
      if (response.dashboard_id) {
        localStorage.setItem('insightai_dashboard_id', response.dashboard_id);
      }
      setDatasetMetadata(response.metadata);
      setDefaultChartSchemas(response.default_chart_schemas ?? []);
      setAutoInsights(response.auto_insights ?? '');

      const initialWidgets: DashboardWidget[] = [];
      if (response.auto_insights) {
        initialWidgets.push({
          id: 'widget-auto-insights',
          title: 'Autonomous Data Ingestion',
          type: 'insight',
          content: response.auto_insights,
        });
      }
      setDashboardWidgets(initialWidgets);

      setMessages([
        {
          role: 'assistant',
          content: `Ingestion complete. Dataset "${response.metadata.filename}" has been indexed. I am ready for advanced analytical queries.`,
        },
      ]);
    } catch (error) {
      setUploadError('Data ingestion failed. Ensure the CSV format is valid.');
      throw error;
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!sessionId) return;

    const nextMessages: ChatMessage[] = [...messages, { role: 'user', content: message }];
    setMessages(nextMessages);
    setChatLoading(true);

    try {
      const response = await sendMessage(sessionId, message);
      const assistantMessage: ChatMessage = {
        role: response.role as ChatMessage['role'],
        content: response.content,
        chart_schema: response.chart_schema,
        execution_time_ms: response.execution_time_ms,
      };
      setMessages((current) => [...current, assistantMessage]);

      const widgetId = `widget-${Date.now()}`;
      if (response.chart_schema) {
        setDashboardWidgets((current) => [
          ...current,
          {
            id: widgetId,
            title: `Analysis: ${message.slice(0, 30)}...`,
            type: 'chart',
            chartSchema: response.chart_schema,
            content: response.content,
          },
        ]);
      } else {
        setDashboardWidgets((current) => [
          ...current,
          {
            id: widgetId,
            title: 'Statistical Insight',
            type: 'insight',
            content: response.content,
          },
        ]);
      }
    } catch (error) {
      setMessages((current) => [
        ...current,
        { role: 'assistant', content: 'Statistical retrieval failed. Please refine your query.' },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Head>
        <title>InsightAI | Workforce Intelligence</title>
        <meta name="description" content="Premium AI-powered workforce intelligence and data analysis." />
      </Head>

      {/* Header */}
      <header className="px-8 py-6 flex items-center justify-between border-b border-white/5 bg-[#0b1326]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">InsightAI</h1>
            <p className="text-[10px] text-indigo-400 font-bold uppercase tracking-[0.2em] leading-none mt-1">Workforce Intelligence Platform</p>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="hidden md:flex flex-col items-end">
            <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">System Status</span>
            <span className="text-xs text-emerald-400 font-medium flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Operational
            </span>
          </div>
        </div>
      </header>

      <main className="flex-1 px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 max-w-[1600px] mx-auto">
          {/* Main Dashboard Section */}
          <div className="lg:col-span-8 space-y-8">
            <Dashboard
              metadata={datasetMetadata}
              defaultChartSchemas={defaultChartSchemas}
              autoInsights={autoInsights}
              widgets={dashboardWidgets}
            />
          </div>

          {/* Sidebar Section */}
          <div className="lg:col-span-4 space-y-8 flex flex-col h-[calc(100vh-160px)] sticky top-28">
            {/* Upload Area */}
            <div className="glass-card p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-sm font-bold text-slate-100 uppercase tracking-widest">Data Ingestion</h2>
                <div className="px-2 py-1 bg-indigo-500/10 border border-indigo-500/20 rounded text-[10px] text-indigo-400 font-bold">CSV/XLSX</div>
              </div>
              <FileUpload onUpload={handleUpload} disabled={chatLoading} />
              {uploadError && (
                <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-3">
                  <svg className="w-4 h-4 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-xs text-red-400">{uploadError}</p>
                </div>
              )}
            </div>

            {/* Chat Assistant */}
            <div className="flex-1 min-h-0">
              <ChatWindow
                messages={messages}
                onSend={handleSendMessage}
                disabled={!sessionId}
                loading={chatLoading}
              />
            </div>
          </div>
        </div>
      </main>


    </div>
  );
}
