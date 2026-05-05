import React, { useState } from 'react';
import Head from 'next/head';
import FileUpload from '../components/FileUpload';
import ChatWindow from '../components/ChatWindow';
import Dashboard from '../components/Dashboard';
import { uploadFile, sendMessage, UploadMetadata } from '../utils/api-client';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  chart_url?: string;
  execution_time_ms?: number;
}

interface DashboardWidget {
  id: string;
  title: string;
  type: 'chart' | 'insight';
  content?: string;
  chartUrl?: string;
}

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [datasetMetadata, setDatasetMetadata] = useState<UploadMetadata | null>(null);
  const [defaultChartUrls, setDefaultChartUrls] = useState<string[]>([]);
  const [autoInsights, setAutoInsights] = useState<string>('');
  const [dashboardWidgets, setDashboardWidgets] = useState<DashboardWidget[]>([]);

  const handleUpload = async (file: File) => {
    try {
      setUploadError(null);
      const response = await uploadFile(file);
      setSessionId(response.session_id);
      setDatasetMetadata(response.metadata);
      setDefaultChartUrls(response.default_chart_urls ?? []);
      setAutoInsights(response.auto_insights ?? '');

      const initialWidgets: DashboardWidget[] = [];
      if (response.auto_insights) {
        initialWidgets.push({
          id: 'widget-auto-insights',
          title: 'Auto insights',
          type: 'insight',
          content: response.auto_insights,
        });
      }
      setDashboardWidgets(initialWidgets);

      setMessages([
        {
          role: 'assistant',
          content: `Upload successful. Dataset ${response.metadata.filename} is ready for analysis.`,
        },
      ]);
    } catch (error) {
      setUploadError('Unable to upload dataset. Please check the file and try again.');
      throw error;
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!sessionId) {
      return;
    }

    const nextMessages: ChatMessage[] = [...messages, { role: 'user', content: message }];
    setMessages(nextMessages);
    setChatLoading(true);

    try {
      const response = await sendMessage(sessionId, message);
      const assistantMessage: ChatMessage = {
        role: response.role as ChatMessage['role'],
        content: response.content,
        chart_url: response.chart_url,
        execution_time_ms: response.execution_time_ms,
      };
      setMessages((current) => [
        ...current,
        assistantMessage,
      ]);

      const widgetId = `widget-${Date.now()}`;
      if (response.chart_url) {
        setDashboardWidgets((current) => [
          ...current,
          {
            id: widgetId,
            title: 'Chat chart',
            type: 'chart',
            chartUrl: response.chart_url,
            content: response.content,
          },
        ]);
      } else {
        setDashboardWidgets((current) => [
          ...current,
          {
            id: widgetId,
            title: 'Chat insight',
            type: 'insight',
            content: response.content,
          },
        ]);
      }
    } catch (error) {
      setMessages((current) => [
        ...current,
        { role: 'assistant', content: 'Failed to retrieve an answer. Please try again.' },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>Insights Chatbot | Employee Data Analysis</title>
        <meta
          name="description"
          content="AI-powered chatbot for employee dataset analysis"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <h1 className="text-3xl font-bold text-gray-900">
              📊 Insights Chatbot
            </h1>
            <p className="text-gray-600 mt-1">
              AI-powered analysis for employee datasets
            </p>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <div className="lg:col-span-3">
              <Dashboard
                metadata={datasetMetadata}
                defaultChartUrls={defaultChartUrls}
                autoInsights={autoInsights}
                widgets={dashboardWidgets}
              />
            </div>

            <div className="lg:col-span-1 space-y-6">
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  📁 Upload Dataset
                </h2>
                <FileUpload onUpload={handleUpload} disabled={chatLoading} />
                {uploadError ? (
                  <p className="mt-3 text-sm text-red-600">{uploadError}</p>
                ) : null}
              </div>

              <div className="bg-white rounded-lg shadow-md p-6 h-[600px] flex flex-col">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  💬 Analysis Chat
                </h2>
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
    </>
  );
}
