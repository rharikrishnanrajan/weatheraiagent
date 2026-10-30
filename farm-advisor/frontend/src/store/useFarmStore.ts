import { create } from 'zustand';
import type {
  FarmProfile,
  WeatherData,
  ThreadItem,
  ChatMessage,
  ToolExecution
} from '../types';
import {
  fetchProfile,
  updateProfile,
  fetchWeather,
  fetchThreads,
  fetchThreadMessages,
  deleteThread,
  streamChat
} from '../api/client';

interface FarmState {
  profile: FarmProfile | null;
  weather: WeatherData | null;
  threads: ThreadItem[];
  activeThreadId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  activeTools: ToolExecution[];
  errorMessage: string | null;

  // Actions
  loadProfile: () => Promise<void>;
  saveProfile: (data: Partial<FarmProfile>) => Promise<void>;
  loadWeather: (params?: { lat?: number; lon?: number; place_name?: string }) => Promise<void>;
  loadThreads: () => Promise<void>;
  selectThread: (threadId: string) => Promise<void>;
  startNewThread: () => void;
  deleteThreadItem: (threadId: string) => Promise<void>;
  sendMessage: (content: string, overrideLocation?: string) => Promise<void>;
  clearError: () => void;
}

export const useFarmStore = create<FarmState>((set, get) => ({
  profile: null,
  weather: null,
  threads: [],
  activeThreadId: null,
  messages: [],
  isStreaming: false,
  activeTools: [],
  errorMessage: null,

  clearError: () => set({ errorMessage: null }),

  loadProfile: async () => {
    try {
      const prof = await fetchProfile();
      set({ profile: prof });
      // If weather is not loaded yet, load weather for profile location
      if (!get().weather && prof.latitude && prof.longitude) {
        get().loadWeather({ lat: prof.latitude, lon: prof.longitude });
      }
    } catch (err: unknown) {
      console.error(err);
    }
  },

  saveProfile: async (data: Partial<FarmProfile>) => {
    try {
      const updated = await updateProfile(data);
      set({ profile: updated });
      if (updated.latitude && updated.longitude) {
        await get().loadWeather({ lat: updated.latitude, lon: updated.longitude });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ errorMessage: `Failed to save profile: ${msg}` });
      throw err;
    }
  },

  loadWeather: async (params) => {
    try {
      const data = await fetchWeather(params);
      set({ weather: data });
    } catch (err: unknown) {
      console.error(err);
    }
  },

  loadThreads: async () => {
    try {
      const threads = await fetchThreads();
      set({ threads });
    } catch (err: unknown) {
      console.error(err);
    }
  },

  selectThread: async (threadId: string) => {
    try {
      set({ activeThreadId: threadId, isStreaming: false, activeTools: [] });
      const msgs = await fetchThreadMessages(threadId);
      set({ messages: msgs });
    } catch (err: unknown) {
      console.error(err);
    }
  },

  startNewThread: () => {
    set({
      activeThreadId: null,
      messages: [],
      isStreaming: false,
      activeTools: [],
    });
  },

  deleteThreadItem: async (threadId: string) => {
    try {
      await deleteThread(threadId);
      const remaining = get().threads.filter((t) => t.thread_id !== threadId);
      set({ threads: remaining });
      if (get().activeThreadId === threadId) {
        get().startNewThread();
      }
    } catch (err: unknown) {
      console.error(err);
    }
  },

  sendMessage: async (content: string, overrideLocation?: string) => {
    const trimmed = content.trim();
    if (!trimmed || get().isStreaming) return;

    const threadId = get().activeThreadId || undefined;
    const userMsg: ChatMessage = {
      role: 'user',
      content: trimmed,
      created_at: new Date().toISOString(),
    };

    // Prepend user message and initialize empty assistant message for streaming
    const currentMessages = [...get().messages, userMsg];
    const assistantIndex = currentMessages.length;
    currentMessages.push({
      role: 'assistant',
      content: '',
      sources: [],
      tool_calls: [],
      created_at: new Date().toISOString(),
    });

    set({
      messages: currentMessages,
      isStreaming: true,
      activeTools: [],
      errorMessage: null,
    });

    let accumulatedText = '';
    const collectedTools: ToolExecution[] = [];

    await streamChat(
      {
        message: trimmed,
        thread_id: threadId,
        override_location: overrideLocation,
      },
      {
        onToken: (token) => {
          accumulatedText += token;
          set((state) => {
            const updated = [...state.messages];
            if (updated[assistantIndex]) {
              updated[assistantIndex] = {
                ...updated[assistantIndex],
                content: accumulatedText,
              };
            }
            return { messages: updated };
          });
        },
        onToolStart: (tool, label, input) => {
          const entry: ToolExecution = {
            tool,
            label: label || `Running ${tool}...`,
            status: 'running',
            input,
          };
          collectedTools.push(entry);
          set({ activeTools: [...collectedTools] });
        },
        onToolEnd: (tool) => {
          const idx = collectedTools.findIndex((t) => t.tool === tool && t.status === 'running');
          if (idx !== -1) {
            collectedTools[idx].status = 'completed';
          }
          set({ activeTools: [...collectedTools] });
        },
        onDone: (data) => {
          set((state) => {
            const updated = [...state.messages];
            if (updated[assistantIndex]) {
              updated[assistantIndex] = {
                ...updated[assistantIndex],
                content: data.response || accumulatedText,
                sources: data.sources || [],
                tool_calls: collectedTools,
              };
            }
            return {
              messages: updated,
              activeThreadId: data.thread_id,
              isStreaming: false,
              activeTools: [],
            };
          });
          get().loadThreads();
        },
        onError: (err) => {
          set({
            isStreaming: false,
            errorMessage: err,
            activeTools: [],
          });
        },
      }
    );
  },
}));
