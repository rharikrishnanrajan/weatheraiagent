// ==============================================================================
// AgriPulse: Frontend HTTP & SSE API Client
// ==============================================================================
// WHAT THIS FILE DOES:
// 1. Centralizes all network requests from the React frontend to the FastAPI backend.
// 2. Implements standard REST calls for profile, weather, chat threads, and knowledge base.
// 3. Implements Server-Sent Events (SSE) streaming reader (`streamChat`) to display AI
//    tokens and tool execution chips in real-time as they arrive from the backend.
//
// BEGINNER TIP: This file acts as the bridge between the user interface in the browser
// and the Python server. Any time a React page needs data, it calls a function here.
// ==============================================================================

import type {
  FarmProfile,
  WeatherData,
  ThreadItem,
  ChatMessage,
  KnowledgeDoc,
  KnowledgeSearchResult
} from '../types';

// The base path for all backend endpoints (proxied by Vite to http://localhost:8000)
const API_BASE = '/api';


// ------------------------------------------------------------------------------
// FARM PROFILE API CALLS
// ------------------------------------------------------------------------------

/**
 * Loads the farmer's current profile from GET /api/profile.
 * Returns location, crops grown, soil type, and irrigation system.
 */
export async function fetchProfile(): Promise<FarmProfile> {
  const res = await fetch(`${API_BASE}/profile`);
  if (!res.ok) throw new Error('Failed to fetch farm profile');
  return res.json();
}

/**
 * Updates farm profile settings via PUT /api/profile.
 * Accepts partial fields so you can update just soil, just crops, etc.
 */
export async function updateProfile(data: Partial<FarmProfile>): Promise<FarmProfile> {
  const res = await fetch(`${API_BASE}/profile`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update farm profile');
  return res.json();
}


// ------------------------------------------------------------------------------
// WEATHER API CALLS
// ------------------------------------------------------------------------------

/**
 * Fetches real-time weather, 7-day forecast, and severe alerts from GET /api/weather.
 * If no coordinates or place_name are provided, backend defaults to the farm profile.
 */
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


// ------------------------------------------------------------------------------
// CONVERSATION THREAD API CALLS
// ------------------------------------------------------------------------------

/**
 * Retrieves the list of all past conversation sessions from GET /api/threads.
 */
export async function fetchThreads(): Promise<ThreadItem[]> {
  const res = await fetch(`${API_BASE}/threads`);
  if (!res.ok) throw new Error('Failed to fetch chat threads');
  return res.json();
}

/**
 * Retrieves all past messages for a specific conversation session from
 * GET /api/threads/{threadId}/messages.
 */
export async function fetchThreadMessages(threadId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${API_BASE}/threads/${threadId}/messages`);
  if (!res.ok) throw new Error('Failed to fetch thread messages');
  return res.json();
}

/**
 * Permanently deletes a conversation thread and its messages via
 * DELETE /api/threads/{threadId}.
 */
export async function deleteThread(threadId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/threads/${threadId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete thread');
}


// ------------------------------------------------------------------------------
// KNOWLEDGE BASE (RAG) API CALLS
// ------------------------------------------------------------------------------

/**
 * Lists all indexed agronomy documents from GET /api/kb/documents.
 */
export async function fetchKBDocuments(): Promise<KnowledgeDoc[]> {
  const res = await fetch(`${API_BASE}/kb/documents`);
  if (!res.ok) throw new Error('Failed to fetch knowledge base documents');
  return res.json();
}

/**
 * Uploads a new document file (.md, .txt, .pdf) to POST /api/kb/upload.
 * The backend automatically chunks and embeds the document into ChromaDB.
 */
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

/**
 * Manually triggers re-indexing of all knowledge base files into ChromaDB
 * via POST /api/kb/ingest.
 */
export async function ingestKBDocuments(): Promise<{ status: string; documents_processed: number; chunks_created: number }> {
  const res = await fetch(`${API_BASE}/kb/ingest`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to trigger ingestion');
  return res.json();
}

/**
 * Runs semantic vector similarity search against the knowledge base
 * via POST /api/kb/search.
 */
export async function searchKnowledgeBase(query: string, crop?: string): Promise<KnowledgeSearchResult[]> {
  const res = await fetch(`${API_BASE}/kb/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, crop, top_k: 4 }),
  });
  if (!res.ok) throw new Error('Failed to search knowledge base');
  return res.json();
}


// ------------------------------------------------------------------------------
// REAL-TIME SERVER-SENT EVENTS (SSE) STREAMING CHAT
// ------------------------------------------------------------------------------

/**
 * Sends a user message to the AI agent and listens for streaming events over HTTP.
 * 
 * Events processed:
 * - 'token': An individual word or token chunk generated by the AI model.
 * - 'tool_start': Fired when the agent begins executing a tool (shows a pill chip).
 * - 'tool_end': Fired when the tool completes.
 * - 'done': Final message containing full response, thread ID, and cited sources.
 * - 'error': Error message if something fails during generation.
 */
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
    // Initiate POST request with stream=true to receive text/event-stream
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

    // Set up a streaming reader to read raw byte chunks from the server
    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // Decode bytes to text and append to our line buffer
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || ''; // Keep partial line in buffer

      for (const block of lines) {
        const trimmed = block.trim();
        if (!trimmed.startsWith('data:')) continue;
        const jsonStr = trimmed.replace(/^data:\s*/, '');
        if (!jsonStr) continue;

        try {
          const parsed = JSON.parse(jsonStr);

          // Route the event to the appropriate callback handler
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
          // Ignore incomplete JSON chunk; it will be completed in next read
        }
      }
    }
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    callbacks.onError(`Network connection error: ${msg}`);
  }
}
