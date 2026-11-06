// ==============================================================================
// AgriPulse: Chat Page Component
// ==============================================================================
// WHAT THIS FILE DOES:
// 1. Renders the main conversational interface between the farmer and AgriPulse.
// 2. Features a conversation sidebar (past threads, new chat button, delete thread).
// 3. Displays quick-start prompt chips for common tasks (Irrigation, Spraying, Disease, Sowing).
// 4. Shows live tool execution pill chips as the agent decides to query tools.
// 5. Renders formatted Markdown answers with citations and source document links.
//
// BEGINNER TIP: This is the primary screen users interact with. It automatically
// handles autoscrolling to the bottom as new words stream in from the server.
// ==============================================================================

import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Send,
  Plus,
  Trash2,
  MapPin,
  Sprout,
  User,
  AlertCircle,
  Sparkles,
  Droplets,
  Wind,
  ShieldAlert,
  Calendar,
  MessageSquare,
} from 'lucide-react';
import { useFarmStore } from '../store/useFarmStore';
import { ToolCallGroup } from '../components/ToolExecutionChip';
import { SourceCitations } from '../components/SourceCitations';

// Pre-defined quick prompt buttons to help beginners test key capabilities
const QUICK_PROMPTS = [
  {
    icon: Droplets,
    label: 'Irrigation Advice',
    query: 'Should I irrigate my crops today based on the 3-day rainfall forecast and soil moisture?',
  },
  {
    icon: Wind,
    label: 'Spray Window',
    query: 'Is there a safe spraying window in the next 36 hours for fungicide application?',
  },
  {
    icon: ShieldAlert,
    label: 'Disease Risk',
    query: 'What is our current fungal and blight disease risk given recent temperature and humidity?',
  },
  {
    icon: Calendar,
    label: 'Sowing Calendar',
    query: 'What are the critical soil temperature and moisture thresholds for sowing my crops?',
  },
];

export const ChatPage = () => {
  // Pull state variables and actions from the Zustand farm store
  const {
    profile,
    threads,
    activeThreadId,
    messages,
    isStreaming,
    activeTools,
    errorMessage,
    loadProfile,
    loadThreads,
    selectThread,
    startNewThread,
    deleteThreadItem,
    sendMessage,
    clearError,
  } = useFarmStore();

  const [input, setInput] = useState('');
  const [overrideLoc, setOverrideLoc] = useState('');
  const [showOverrideInput, setShowOverrideInput] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initial data loading when the page mounts
  useEffect(() => {
    loadProfile();
    loadThreads();
  }, [loadProfile, loadThreads]);

  // Smooth autoscroll to the latest message whenever messages or active tools update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, activeTools]);

  /**
   * Handles user submission via button click or Enter key.
   */
  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || isStreaming) return;

    const locOverride = overrideLoc.trim() ? overrideLoc.trim() : undefined;
    setInput('');
    await sendMessage(textToSend, locOverride);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] max-w-7xl mx-auto p-4 gap-4">
      {/* ---------------------------------------------------------------------- */}
      {/* LEFT SIDEBAR: Conversation History & Farm Context Snapshot              */}
      {/* ---------------------------------------------------------------------- */}
      <aside className="w-80 flex flex-col bg-white rounded-xl border border-stone-200 shadow-sm p-4 hidden md:flex">
        {/* New Chat Button */}
        <button
          onClick={startNewThread}
          className="w-full flex items-center justify-center gap-2 bg-emerald-700 hover:bg-emerald-800 text-white font-medium py-2.5 px-4 rounded-lg transition-colors shadow-sm mb-4"
        >
          <Plus className="w-4 h-4" />
          <span>New Advisory Chat</span>
        </button>

        {/* Farm Profile Snapshot Pill */}
        {profile && (
          <div className="bg-stone-50 border border-stone-200/80 rounded-lg p-3 mb-4 text-xs">
            <div className="flex items-center gap-1.5 text-emerald-800 font-semibold mb-1">
              <MapPin className="w-3.5 h-3.5" />
              <span>{profile.location_name}</span>
            </div>
            <div className="text-stone-600 flex items-center gap-1 mb-1">
              <Sprout className="w-3.5 h-3.5 text-stone-500" />
              <span>{profile.crops.join(', ')}</span>
            </div>
            <div className="text-stone-500">
              Soil: <span className="font-medium text-stone-700">{profile.soil_type}</span> | System:{' '}
              <span className="font-medium text-stone-700">{profile.irrigation_type}</span>
            </div>
          </div>
        )}

        {/* Conversation Sessions List */}
        <div className="flex-1 overflow-y-auto space-y-1 pr-1">
          <div className="text-xs font-semibold text-stone-400 uppercase tracking-wider px-2 py-1">
            Recent Conversations
          </div>
          {threads.length === 0 ? (
            <div className="text-center py-8 text-stone-400 text-sm">
              <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-40" />
              No past conversations yet
            </div>
          ) : (
            threads.map((thread) => (
              <div
                key={thread.thread_id}
                onClick={() => selectThread(thread.thread_id)}
                className={`group flex items-center justify-between p-2.5 rounded-lg cursor-pointer text-sm transition-colors ${
                  activeThreadId === thread.thread_id
                    ? 'bg-emerald-50 text-emerald-950 font-medium border border-emerald-200/60'
                    : 'text-stone-700 hover:bg-stone-100'
                }`}
              >
                <div className="truncate flex-1 pr-2">
                  <div className="truncate">{thread.title || 'Advisory Session'}</div>
                  <div className="text-[11px] text-stone-400">
                    {new Date(thread.updated_at).toLocaleDateString([], {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteThreadItem(thread.thread_id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-600 transition-opacity"
                  title="Delete conversation"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* ---------------------------------------------------------------------- */}
      {/* MAIN CHAT AREA: Message Log & Input Box                                */}
      {/* ---------------------------------------------------------------------- */}
      <main className="flex-1 flex flex-col bg-white rounded-xl border border-stone-200 shadow-sm overflow-hidden">
        {/* Error Notification Banner */}
        {errorMessage && (
          <div className="bg-amber-50 border-b border-amber-200 p-3 px-4 flex items-center justify-between text-sm text-amber-900">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={clearError}
              className="text-amber-700 hover:text-amber-900 text-xs font-semibold uppercase px-2 py-1"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Message History View */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto py-8">
              <div className="w-16 h-16 rounded-2xl bg-emerald-100 flex items-center justify-center text-emerald-700 mb-4 shadow-inner">
                <Sparkles className="w-8 h-8" />
              </div>
              <h2 className="text-xl font-bold text-stone-800 mb-2">
                AgriPulse Weather & Agronomy Advisory
              </h2>
              <p className="text-sm text-stone-600 mb-6 leading-relaxed">
                Ask questions about your crops, schedule irrigation based on live rain forecasts,
                check safe pesticide spray windows, or evaluate disease pressure.
              </p>

              {/* Quick Prompt Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full text-left">
                {QUICK_PROMPTS.map((prompt, idx) => {
                  const Icon = prompt.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => handleSend(prompt.query)}
                      className="p-3.5 border border-stone-200 rounded-xl hover:border-emerald-500 hover:bg-emerald-50/40 transition-all text-xs flex flex-col gap-1.5 shadow-sm group"
                    >
                      <div className="flex items-center gap-2 font-semibold text-stone-800 group-hover:text-emerald-800">
                        <Icon className="w-4 h-4 text-emerald-600" />
                        <span>{prompt.label}</span>
                      </div>
                      <span className="text-stone-500 line-clamp-2 leading-relaxed">
                        {prompt.query}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {/* Assistant Avatar */}
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-full bg-emerald-700 text-white flex items-center justify-center shrink-0 text-xs font-bold shadow-sm">
                    🌾
                  </div>
                )}

                {/* Message Bubble */}
                <div
                  className={`max-w-[85%] md:max-w-[75%] rounded-2xl p-4 shadow-sm text-sm ${
                    msg.role === 'user'
                      ? 'bg-emerald-700 text-white rounded-tr-none'
                      : 'bg-stone-50 border border-stone-200/80 text-stone-800 rounded-tl-none'
                  }`}
                >
                  {msg.role === 'user' ? (
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                  ) : (
                    <div className="space-y-3">
                      {/* Formatted Markdown Body */}
                      <div className="prose prose-sm prose-stone max-w-none prose-headings:font-semibold prose-headings:text-stone-900 prose-a:text-emerald-700 prose-strong:text-stone-900 leading-relaxed">
                        {msg.content ? (
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content}
                          </ReactMarkdown>
                        ) : (
                          isStreaming && (
                            <span className="inline-flex gap-1 items-center text-stone-400 py-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse delay-75" />
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse delay-150" />
                            </span>
                          )
                        )}
                      </div>

                      {/* Reference Document Citations */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="pt-2 border-t border-stone-200/60 mt-3">
                          <SourceCitations sources={msg.sources} />
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* User Avatar */}
                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-stone-300 text-stone-700 flex items-center justify-center shrink-0 shadow-sm">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))
          )}

          {/* Active Tool Execution Chips (Displayed while agent is thinking) */}
          {isStreaming && activeTools.length > 0 && (
            <div className="ml-11">
              <ToolCallGroup tools={activeTools} />
            </div>
          )}

          {/* Invisible target element for autoscroll */}
          <div ref={messagesEndRef} />
        </div>

        {/* -------------------------------------------------------------------- */}
        {/* BOTTOM INPUT BAR: Textarea, Location Override, & Send Button          */}
        {/* -------------------------------------------------------------------- */}
        <div className="p-4 border-t border-stone-200 bg-stone-50/50">
          {/* Optional Location Override Toggle */}
          <div className="flex items-center justify-between mb-2 text-xs">
            <button
              type="button"
              onClick={() => setShowOverrideInput(!showOverrideInput)}
              className="text-stone-500 hover:text-emerald-700 flex items-center gap-1 font-medium transition-colors"
            >
              <MapPin className="w-3.5 h-3.5" />
              <span>
                {showOverrideInput ? 'Hide location override' : 'Query a different location?'}
              </span>
            </button>
            {overrideLoc && (
              <span className="text-emerald-700 font-medium">Overriding to: {overrideLoc}</span>
            )}
          </div>

          {/* Location Override Input Field */}
          {showOverrideInput && (
            <div className="mb-2">
              <input
                type="text"
                placeholder="Enter city or district (e.g., Fresno, CA or Nashik, India)..."
                value={overrideLoc}
                onChange={(e) => setOverrideLoc(e.target.value)}
                className="w-full text-xs px-3 py-1.5 bg-white border border-stone-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-emerald-600"
              />
            </div>
          )}

          {/* Main Input Textarea & Send Button */}
          <div className="flex gap-2 items-end">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask AgriPulse about your crops, irrigation, or weather conditions..."
              rows={2}
              className="flex-1 resize-none bg-white border border-stone-300 rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-transparent transition-shadow shadow-sm"
              disabled={isStreaming}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isStreaming}
              className="h-11 px-4 bg-emerald-700 hover:bg-emerald-800 disabled:opacity-40 disabled:hover:bg-emerald-700 text-white rounded-xl flex items-center justify-center transition-colors shadow-sm shrink-0"
              title="Send message"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};
