// ==============================================================================
// AgriPulse: Global State Store (Zustand)
// ==============================================================================
// WHAT THIS FILE DOES:
// 1. Manages global application state (farm profile, live weather, chat messages).
// 2. Provides actions to load data from the backend and update React components.
// 3. Handles conversation switching, new chats, and real-time streaming updates.
//
// BEGINNER TIP: "Zustand" is a lightweight state manager for React.
// Instead of passing state down through 10 components with props ("prop drilling"),
// any component can directly import `useFarmStore` to read data or trigger actions.
// ==============================================================================

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

/**
 * Interface defining all state variables and action functions
 * available in the store.
 */
interface FarmState {
  // State variables
  profile: FarmProfile | null;         // Current farmer profile (soil, crops, coordinates)
  weather: WeatherData | null;         // Live weather metrics and forecast
  threads: ThreadItem[];               // List of past conversation threads
  activeThreadId: string | null;       // ID of currently opened chat session
  messages: ChatMessage[];             // Messages in the active conversation
  isStreaming: boolean;                // True while the AI is actively generating tokens
  activeTools: ToolExecution[];        // Tools currently executing (shown as pill chips)
  errorMessage: string | null;         // Global error alert banner message

  // Actions (methods that update the state)
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
  // Initial state values
  profile: null,
  weather: null,
  threads: [],
  activeThreadId: null,
  messages: [],
  isStreaming: false,
  activeTools: [],
  errorMessage: null,

  /**
   * Loads the farmer's registered profile from the backend.
   */
  loadProfile: async () => {
    try {
      const profile = await fetchProfile();
      set({ profile });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ errorMessage: `Failed to load profile: ${msg}` });
    }
  },

  /**
   * Saves profile modifications (e.g. soil texture, crops) to the backend.
   */
  saveProfile: async (data: Partial<FarmProfile>) => {
    try {
      const updated = await updateProfile(data);
      set({ profile: updated });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ errorMessage: `Failed to save profile: ${msg}` });
    }
  },

  /**
   * Fetches weather forecast data for coordinates or a specific place name.
   */
  loadWeather: async (params) => {
    try {
      const weather = await fetchWeather(params);
      set({ weather });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ errorMessage: `Failed to load weather: ${msg}` });
    }
  },

  /**
   * Loads the list of past conversation threads for the sidebar.
   */
  loadThreads: async () => {
    try {
      const threads = await fetchThreads();
      set({ threads });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ errorMessage: `Failed to load chat history: ${msg}` });
    }
  },

  /**
   * Switches the active conversation to the selected thread and loads its messages.
   */
  selectThread: async (threadId: string) => {
    try {
      set({ activeThreadId: threadId, isStreaming: false, activeTools: [] });
      const messages = await fetchThreadMessages(threadId);
      set({ messages });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ errorMessage: `Failed to load messages: ${msg}` });
    }
  },

  /**
   * Resets active conversation to start a blank chat session.
   */
  startNewThread: () => {
    set({
      activeThreadId: null,
      messages: [],
      activeTools: [],
      isStreaming: false,
      errorMessage: null,
    });
  },

  /**
   * Deletes a conversation thread and clears the screen if it was currently open.
   */
  deleteThreadItem: async (threadId: string) => {
    try {
      await deleteThread(threadId);
      const threads = get().threads.filter((t) => t.thread_id !== threadId);
      set({ threads });
      if (get().activeThreadId === threadId) {
        get().startNewThread();
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ errorMessage: `Failed to delete thread: ${msg}` });
    }
  },

  /**
   * Submits a farmer message, creates a user bubble, and streams the AI's response.
   */
  sendMessage: async (content: string, overrideLocation?: string) => {
    const trimmed = content.trim();
    if (!trimmed || get().isStreaming) return;

    // 1. Immediately append user's message to the UI
    const userMsg: ChatMessage = {
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    // 2. Prepare an empty assistant placeholder message to receive streaming tokens
    const assistantPlaceholder: ChatMessage = {
      role: 'assistant',
      content: '',
      sources: [],
      timestamp: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, userMsg, assistantPlaceholder],
      isStreaming: true,
      activeTools: [],
      errorMessage: null,
    }));

    const currentThreadId = get().activeThreadId || undefined;

    // 3. Stream response tokens and tool execution events from backend
    await streamChat(
      {
        message: trimmed,
        thread_id: currentThreadId,
        override_location: overrideLocation,
      },
      {
        // On each word/token received from the AI model
        onToken: (token: string) => {
          set((state) => {
            const msgs = [...state.messages];
            const lastIdx = msgs.length - 1;
            if (lastIdx >= 0 && msgs[lastIdx].role === 'assistant') {
              msgs[lastIdx] = {
                ...msgs[lastIdx],
                content: msgs[lastIdx].content + token,
              };
            }
            return { messages: msgs };
          });
        },

        // When the agent begins calling a tool (e.g. "Fetching 7-day forecast...")
        onToolStart: (tool: string, label?: string, input?: Record<string, unknown>) => {
          set((state) => ({
            activeTools: [
              ...state.activeTools.filter((t) => t.tool !== tool),
              {
                tool,
                label: label || `Running ${tool}...`,
                status: 'running',
                input,
              },
            ],
          }));
        },

        // When the tool finishes executing
        onToolEnd: (tool: string) => {
          set((state) => ({
            activeTools: state.activeTools.map((t) =>
              t.tool === tool ? { ...t, status: 'completed' } : t
            ),
          }));
        },

        // When the full message generation is complete
        onDone: (data) => {
          set((state) => {
            const msgs = [...state.messages];
            const lastIdx = msgs.length - 1;
            if (lastIdx >= 0 && msgs[lastIdx].role === 'assistant') {
              msgs[lastIdx] = {
                ...msgs[lastIdx],
                content: data.response || msgs[lastIdx].content,
                sources: data.sources || [],
              };
            }
            return {
              messages: msgs,
              activeThreadId: data.thread_id,
              isStreaming: false,
            };
          });
          // Refresh thread list so new conversations appear in the sidebar
          get().loadThreads();
        },

        // On network error or backend failure
        onError: (err: string) => {
          set({
            isStreaming: false,
            errorMessage: err,
          });
        },
      }
    );
  },

  /**
   * Dismisses the error banner.
   */
  clearError: () => set({ errorMessage: null }),
}));
