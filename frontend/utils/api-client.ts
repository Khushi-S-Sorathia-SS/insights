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
  execution_time_ms?: number;  dashboard_id?: string;
  version?: number;  error_message?: string;
}

export interface ParsedCommand {
  intent: 'direct' | 'analysis' | 'replace' | 'create' | 'modify';
  params: {
    source_type?: string;
    target_type?: string;
    chart_type?: string;
    target_title?: string;
    [key: string]: any;
  };
}

export function parseChatCommand(message: string): ParsedCommand {
  const text = message.toLowerCase().trim();
  
  // Check for replace commands
  const replacePatterns = [
    /replace\s+(\w+)\s+chart\s+with\s+(\w+)\s+chart/i,
    /change\s+(\w+)\s+chart\s+to\s+(\w+)\s+chart/i,
    /swap\s+(\w+)\s+chart\s+for\s+(\w+)\s+chart/i,
    /switch\s+(\w+)\s+chart\s+with\s+(\w+)\s+chart/i
  ];
  
  for (const pattern of replacePatterns) {
    const match = text.match(pattern);
    if (match) {
      return {
        intent: 'replace',
        params: {
          source_type: match[1],
          target_type: match[2]
        }
      };
    }
  }
  
  // Check for create commands
  const createPatterns = [
    /create\s+a\s+(\w+)\s+chart/i,
    /add\s+a\s+(\w+)\s+chart/i,
    /show\s+me\s+a\s+(\w+)\s+chart/i,
    /make\s+a\s+(\w+)\s+chart/i
  ];
  
  for (const pattern of createPatterns) {
    const match = text.match(pattern);
    if (match) {
      return {
        intent: 'create',
        params: {
          chart_type: match[1]
        }
      };
    }
  }
  
  // Check for analysis commands
  if (/\b(chart|plot|graph|visualize|show)\b/.test(text)) {
    const chartTypes = ['pie', 'bar', 'line', 'area', 'scatter', 'radar', 'histogram'];
    for (const chartType of chartTypes) {
      if (text.includes(chartType)) {
        return {
          intent: 'analysis',
          params: {
            chart_type: chartType
          }
        };
      }
    }
    return {
      intent: 'analysis',
      params: {}
    };
  }
  
  // Check for direct questions
  const directKeywords = ['how many', 'what is', 'who', 'where', 'when', 'missing', 'duplicate', 'summary', 'count'];
  if (directKeywords.some(keyword => text.includes(keyword))) {
    return {
      intent: 'direct',
      params: {}
    };
  }
  
  // Default to analysis
  return {
    intent: 'analysis',
    params: {}
  };
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
  const parsedCommand = parseChatCommand(message);
  
  const response = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      parsed_command: parsedCommand,
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

export async function getDashboard(sessionId: string): Promise<{widgets: DashboardWidgetData[], version: number, dashboard_id: string}> {
  const response = await fetch(`${API_URL}/api/dashboard/${sessionId}`);
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

export async function getVersions(sessionId: string): Promise<{versions: DashboardVersion[]}> {
  const response = await fetch(`${API_URL}/api/dashboard/${sessionId}/versions`);
  if (!response.ok) {
    throw new Error('Versions fetch failed');
  }
  return response.json();
}

export async function rollbackDashboard(sessionId: string, dashboardId: string): Promise<any> {
  const response = await fetch(`${API_URL}/api/dashboard/${sessionId}/rollback/${dashboardId}`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Rollback failed');
  }
  return response.json();
}

export async function updateLayout(sessionId: string, layout: any[]): Promise<any> {
  const response = await fetch(`${API_URL}/api/dashboard/${sessionId}/layout`, {
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
