/**
 * Stub API client for backend communication.
 * To be implemented in Phase 8.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface UploadMetadata {
  filename: string;
  file_path: string;
  rows: number;
  columns: string[];
  dtypes: Record<string, string>;
  missing_values: Record<string, number>;
  preview_rows: Array<Record<string, string | number | null>>;
}

export interface ChartSchema {
  type: string;
  title?: string;
  data: any[];
  xAxis?: string;
  yAxis?: string;
  [key: string]: any;
}

interface UploadResponse {
  session_id: string;
  dashboard_id?: string;
  message: string;
  metadata: UploadMetadata;
  default_chart_schemas?: ChartSchema[];
  auto_insights?: string;
}

interface ChatResponse {
  role: string;
  content: string;
  chart_schema?: ChartSchema;
  execution_time_ms?: number;
  error_message?: string;
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Upload failed');
  }

  return response.json();
}

export async function sendMessage(
  sessionId: string,
  message: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      message,
    }),
  });

  if (!response.ok) {
    throw new Error('Chat failed');
  }

  return response.json();
}

export interface DashboardWidgetData {
  id: string;
  type: 'chart' | 'insight';
  title: string;
  content?: string;
  chartSchema?: ChartSchema;
}

export async function getDashboard(sessionId: string): Promise<{widgets: DashboardWidgetData[]}> {
  const response = await fetch(`${API_URL}/api/dashboard/${sessionId}`);
  if (!response.ok) {
    throw new Error('Dashboard fetch failed');
  }
  return response.json();
}

export async function getDashboardById(dashboardId: string): Promise<{widgets: DashboardWidgetData[]}> {
  const response = await fetch(`${API_URL}/api/dashboard/by-id/${dashboardId}`);
  if (!response.ok) {
    throw new Error('Dashboard fetch failed');
  }
  return response.json();
}
