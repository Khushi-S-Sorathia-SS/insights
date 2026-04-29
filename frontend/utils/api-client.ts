/**
 * Stub API client for backend communication.
 * To be implemented in Phase 8.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface UploadResponse {
  session_id: string;
  message: string;
  metadata: Record<string, any>;
}

interface ChatResponse {
  role: string;
  content: string;
  chart_url?: string;
  execution_time_ms?: number;
  error_message?: string;
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_URL}/upload`, {
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
  const response = await fetch(`${API_URL}/chat`, {
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
