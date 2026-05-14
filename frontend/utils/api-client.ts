/**
 * API client for backend communication (Dataset-Centric).
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface UploadMetadata {
  filename: string;
  dataset_id: string;
  file_path: string;
  rows: number;
  columns: string[];
  dtypes: Record<string, string>;
  missing_values: Record<string, number>;
  preview_rows: Array<Record<string, string | number | null>>;
  size_bytes: number;
  uploaded_at: string;
}

export interface ChartSchema {
  type: string;
  title?: string;
  data: any[];
  xAxis?: string;
  yAxis?: string;
  w?: number;
  h?: number;
  [key: string]: any;
}

interface UploadResponse {
  session_id: string; // This is the dataset_id in the new system
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
  dashboard_id?: string;
  version?: number;
  error_message?: string;
}

export async function uploadFile(file: File, displayName: string): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('display_name', displayName);

  const response = await fetch(`${API_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Upload failed');
  }

  return response.json();
}

export async function sendMessage(
  datasetId: string,
  message: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: datasetId, // Mapping datasetId to session_id in payload for backward compat
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
  position?: { x: number; y: number; w: number; h: number };
}

export interface DashboardVersion {
  id: string;
  version: number;
  created_at: string;
}

export async function getDashboard(datasetId: string): Promise<{widgets: DashboardWidgetData[], version: number, dashboard_id: string}> {
  const response = await fetch(`${API_URL}/api/dashboard/${datasetId}`);
  if (!response.ok) {
    throw new Error('Dashboard fetch failed');
  }
  return response.json();
}

export async function getDashboardById(dashboardId: string): Promise<{widgets: DashboardWidgetData[], version: number, dashboard_id: string}> {
  const response = await fetch(`${API_URL}/api/dashboard/by-id/${dashboardId}`);
  if (!response.ok) {
    throw new Error('Dashboard fetch failed');
  }
  return response.json();
}

export async function getVersions(datasetId: string): Promise<{ versions: DashboardVersion[] }> {
  const response = await fetch(`${API_URL}/api/dashboard/${datasetId}/versions`);
  if (!response.ok) {
    throw new Error('Failed to fetch versions');
  }
  return response.json();
}

export async function rollbackDashboard(datasetId: string, dashboardId: string): Promise<any> {
  const response = await fetch(`${API_URL}/api/dashboard/${datasetId}/rollback/${dashboardId}`, {
    method: 'POST'
  });
  if (!response.ok) {
    throw new Error('Rollback failed');
  }
  return response.json();
}

export interface DatasetListItem {
  id: string;
  filename: string;
  display_name: string;
  uploaded_at: string;
  rows: number;
}

export async function listDatasets(): Promise<DatasetListItem[]> {
  const response = await fetch(`${API_URL}/api/datasets`);
  if (!response.ok) {
    throw new Error('Failed to list datasets');
  }
  return response.json();
}

export async function getDatasetMetadata(datasetId: string): Promise<UploadMetadata> {
  const response = await fetch(`${API_URL}/api/datasets/${datasetId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch dataset metadata');
  }
  return response.json();
}

export async function getChatHistory(datasetId: string): Promise<any[]> {
  const response = await fetch(`${API_URL}/api/datasets/${datasetId}/history`);
  if (!response.ok) {
    throw new Error('Failed to fetch chat history');
  }
  return response.json();
}

export async function updateLayout(datasetId: string, layout: any[]): Promise<any> {
  const response = await fetch(`${API_URL}/api/dashboard/${datasetId}/layout`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(layout),
  });
  if (!response.ok) {
    throw new Error('Layout update failed');
  }
  return response.json();
}

export async function saveDashboardVersion(datasetId: string, layout: any[]): Promise<{widgets: DashboardWidgetData[], version: number, dashboard_id: string}> {
  const response = await fetch(`${API_URL}/api/dashboard/${datasetId}/save`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(layout),
  });
  if (!response.ok) {
    throw new Error('Failed to save dashboard version');
  }
  return response.json();
}
