import type {
  FarmProfile,
  WeatherData,
  ThreadItem,
  ChatMessage,
  KnowledgeDoc,
  KnowledgeSearchResult
} from '../types';

const API_BASE = '/api';

export async function fetchProfile(): Promise<FarmProfile> {
  const res = await fetch(`${API_BASE}/profile`);
  if (!res.ok) throw new Error('Failed to fetch farm profile');
  return res.json();
}

export async function updateProfile(data: Partial<FarmProfile>): Promise<FarmProfile> {
  const res = await fetch(`${API_BASE}/profile`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update farm profile');
  return res.json();
}

export async function fetchWeather(params?: {
  lat?: number;
  lon?: number;
  place_name?: string;
  days?: number;
}): Promise<WeatherData> {
  const query = new URLSearchParams();
  if (params?.lat !== undefined) query.set('lat', params.lat.toString());
  if (params?.lon !== undefined) query.set('lon', params.lon.toString());
  if (params?.place_name) query.set('place_name', params.place_name);
  if (params?.days) query.set('days', params.days.toString());

  const url = `${API_BASE}/weather${query.toString() ? `?${query.toString()}` : ''}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch weather data');
  return res.json();
}

export async function fetchThreads(): Promise<ThreadItem[]> {
  const res = await fetch(`${API_BASE}/threads`);
  if (!res.ok) throw new Error('Failed to fetch chat threads');
  return res.json();
}

export async function fetchThreadMessages(threadId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${API_BASE}/threads/${threadId}/messages`);
  if (!res.ok) throw new Error('Failed to fetch thread messages');
  return res.json();
}

export async function deleteThread(threadId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/threads/${threadId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete thread');
}

export async function fetchKBDocuments(): Promise<KnowledgeDoc[]> {
  const res = await fetch(`${API_BASE}/kb/documents`);
  if (!res.ok) throw new Error('Failed to fetch knowledge base documents');
  return res.json();
}

export async function uploadKBDocument(file: File): Promise<{ status: string; filename: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/kb/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('Failed to upload document');
  return res.json();
}

export async function ingestKBDocuments(): Promise<{ status: string; documents_processed: number; chunks_created: number }> {
  const res = await fetch(`${API_BASE}/kb/ingest`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to trigger ingestion');
  return res.json();
}

export async function searchKnowledgeBase(query: string, crop?: string): Promise<KnowledgeSearchResult[]> {
  const res = await fetch(`${API_BASE}/kb/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, crop, top_k: 4 }),
  });
  if (!res.ok) throw new Error('Failed to search knowledge base');
  return res.json();
}

export async function streamChat(
  payload: {
    message: string;
    thread_id?: string;
    override_location?: string;
  },
  callbacks: {
    onToken: (token: string) => void;
    onToolStart: (tool: string, label?: string, input?: Record<string, unknown>) => void;
    onToolEnd: (tool: string) => void;
    onDone: (data: { thread_id: string; response: string; sources: string[] }) => void;
    onError: (err: string) => void;
  }
): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}/chat?stream=true`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const errText = await res.text();
      callbacks.onError(`Chat request failed (${res.status}): ${errText}`);
      return;
    }

    if (!res.body) {
      callbacks.onError('Response body is null');
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const block of lines) {
        const trimmed = block.trim();
        if (!trimmed.startsWith('data:')) continue;
        const jsonStr = trimmed.replace(/^data:\s*/, '');
        if (!jsonStr) continue;

        try {
          const parsed = JSON.parse(jsonStr);
          if (parsed.type === 'token') {
            callbacks.onToken(parsed.token);
          } else if (parsed.type === 'tool_start') {
            callbacks.onToolStart(parsed.tool, parsed.label, parsed.input);
          } else if (parsed.type === 'tool_end') {
            callbacks.onToolEnd(parsed.tool);
          } else if (parsed.type === 'done') {
            callbacks.onDone({
              thread_id: parsed.thread_id,
              response: parsed.response,
              sources: parsed.sources || [],
            });
          } else if (parsed.type === 'error') {
            callbacks.onError(parsed.message || 'Error received from advisor');
          }
        } catch {
          // ignore incomplete json chunk in SSE
        }
      }
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    callbacks.onError(`Network connection error: ${msg}`);
  }
}
