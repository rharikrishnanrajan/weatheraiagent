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
  const [overrideLocation, setOverrideLocation] = useState('');
  const [showLocationInput, setShowLocationInput] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadProfile();
    loadThreads();
  }, [loadProfile, loadThreads]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, activeTools]);

  const handleSend = async (textToSend?: string) => {
    const text = textToSend || input;
    if (!text.trim() || isStreaming) return;
    setInput('');
    await sendMessage(text, overrideLocation.trim() || undefined);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-stone-100 overflow-hidden">
      {/* Sidebar: Conversation History */}
      <aside className="w-72 bg-white border-r border-stone-200 hidden md:flex flex-col flex-shrink-0">
        <div className="p-4 border-b border-stone-200">
          <button
            onClick={startNewThread}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl bg-farm-600 hover:bg-farm-700 text-white font-semibold text-sm shadow-xs transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>New Advisory Chat</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          <div className="px-3 py-2 text-xs font-bold uppercase tracking-wider text-stone-400">
            Past Advisory Sessions
          </div>
          {threads.length === 0 ? (
            <div className="px-3 py-6 text-center text-xs text-stone-400">
              No conversations yet. Start asking farm questions!
            </div>
          ) : (
            threads.map((t) => (
              <div
                key={t.thread_id}
                onClick={() => selectThread(t.thread_id)}
                className={`group flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium cursor-pointer transition-colors ${
                  activeThreadId === t.thread_id
                    ? 'bg-farm-50 text-farm-900 font-semibold border border-farm-200'
                    : 'text-stone-700 hover:bg-stone-100'
                }`}
              >
                <div className="flex items-center space-x-2 truncate pr-2">
                  <MessageSquare className="w-3.5 h-3.5 text-stone-400 flex-shrink-0" />
                  <span className="truncate">{t.title}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteThreadItem(t.thread_id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 text-stone-400 hover:text-red-600 rounded transition-opacity"
                  title="Delete Session"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>

        {/* Profile Footer */}
        {profile && (
          <div className="p-4 bg-stone-50 border-t border-stone-200 text-xs">
            <div className="font-semibold text-stone-900">{profile.farmer_name}</div>
            <div className="text-stone-500 truncate">{profile.location_name}</div>
            <div className="text-[11px] text-farm-700 font-medium mt-1">
              {profile.crops.slice(0, 3).join(', ')} • {profile.soil_type} Soil
            </div>
          </div>
        )}
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col h-full bg-stone-50 overflow-hidden">
        {/* Chat Header */}
        <div className="px-6 py-3.5 bg-white border-b border-stone-200 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-farm-100 text-farm-700 flex items-center justify-center font-bold">
              <Sprout className="w-5 h-5 text-farm-600" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-stone-900">AgriPulse Agronomy Agent</h2>
              <p className="text-xs text-stone-500">Live Forecast Grounded • RAG Informed</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowLocationInput(!showLocationInput)}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs font-medium transition-colors"
            >
              <MapPin className="w-3.5 h-3.5 text-farm-600" />
              <span>{overrideLocation ? `Override: ${overrideLocation}` : 'Override Location'}</span>
            </button>
          </div>
        </div>

        {/* Location Override Popover/Bar */}
        {showLocationInput && (
          <div className="px-6 py-2 bg-amber-50/80 border-b border-amber-200 flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2 flex-1 max-w-md">
              <span className="font-semibold text-amber-900">Target Location:</span>
              <input
                type="text"
                placeholder="e.g. Salinas, CA or Des Moines, IA"
                value={overrideLocation}
                onChange={(e) => setOverrideLocation(e.target.value)}
                className="flex-1 px-2.5 py-1 rounded border border-amber-300 bg-white text-xs focus:outline-none focus:ring-1 focus:ring-amber-500"
              />
            </div>
            <button
              onClick={() => {
                setOverrideLocation('');
                setShowLocationInput(false);
              }}
              className="text-amber-800 hover:text-amber-950 font-medium ml-3"
            >
              Reset to Profile
            </button>
          </div>
        )}

        {/* Error Alert */}
        {errorMessage && (
          <div className="mx-6 mt-3 p-3 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button onClick={clearError} className="font-bold ml-2">×</button>
          </div>
        )}

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 space-y-6">
          {messages.length === 0 ? (
            <div className="max-w-2xl mx-auto py-8 text-center">
              <div className="w-14 h-14 rounded-2xl bg-farm-100 text-farm-600 flex items-center justify-center mx-auto mb-4 shadow-xs">
                <Sparkles className="w-7 h-7" />
              </div>
              <h3 className="text-lg font-bold text-stone-900">Welcome to your Farm Advisory Hub</h3>
              <p className="text-sm text-stone-600 mt-1 max-w-md mx-auto">
                Ask about irrigation scheduling, spray windows, sowing timing, disease outbreaks, or frost/heat warnings.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-8 text-left">
                {QUICK_PROMPTS.map((qp, idx) => {
                  const Icon = qp.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => handleSend(qp.query)}
                      className="p-3.5 rounded-xl bg-white border border-stone-200 hover:border-farm-400 hover:shadow-xs transition-all text-left group"
                    >
                      <div className="flex items-center space-x-2 text-farm-700 font-bold text-xs mb-1">
                        <Icon className="w-4 h-4 group-hover:scale-110 transition-transform" />
                        <span>{qp.label}</span>
                      </div>
                      <p className="text-xs text-stone-600 line-clamp-2">{qp.query}</p>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={idx}
                  className={`flex items-start space-x-3 max-w-3xl ${
                    isUser ? 'ml-auto flex-row-reverse space-x-reverse' : 'mr-auto'
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-white shadow-xs ${
                      isUser ? 'bg-stone-800' : 'bg-farm-600'
                    }`}
                  >
                    {isUser ? <User className="w-4 h-4" /> : <Sprout className="w-4 h-4" />}
                  </div>

                  <div
                    className={`p-4 rounded-2xl shadow-xs text-sm leading-relaxed ${
                      isUser
                        ? 'bg-stone-900 text-white rounded-tr-none'
                        : 'bg-white border border-stone-200 text-stone-800 rounded-tl-none w-full'
                    }`}
                  >
                    {isUser ? (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    ) : (
                      <>
                        {/* Tool Calls */}
                        {msg.tool_calls && msg.tool_calls.length > 0 && (
                          <ToolCallGroup tools={msg.tool_calls} />
                        )}

                        {/* Markdown Output */}
                        <div className="prose prose-stone prose-sm max-w-none prose-headings:font-bold prose-headings:text-stone-900 prose-p:my-2 prose-ul:my-2 prose-li:my-0.5">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content}
                          </ReactMarkdown>
                        </div>

                        {/* Citations */}
                        {msg.sources && msg.sources.length > 0 && (
                          <SourceCitations sources={msg.sources} />
                        )}
                      </>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {/* Active Live Streaming Tool Execution */}
          {isStreaming && activeTools.length > 0 && (
            <div className="max-w-3xl mr-auto pl-11">
              <ToolCallGroup tools={activeTools} />
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 bg-white border-t border-stone-200">
          <div className="max-w-4xl mx-auto flex items-end space-x-2">
            <div className="flex-1 relative">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about irrigation, spray conditions, sowing, diseases..."
                rows={2}
                disabled={isStreaming}
                className="w-full resize-none px-4 py-3 rounded-xl border border-stone-200 bg-stone-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-farm-500 focus:border-transparent text-sm text-stone-900 placeholder-stone-400 disabled:opacity-50"
              />
            </div>
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isStreaming}
              className="p-3.5 rounded-xl bg-farm-600 hover:bg-farm-700 disabled:bg-stone-300 text-white font-medium shadow-xs transition-colors disabled:cursor-not-allowed flex-shrink-0"
              title="Send Prompt (Enter)"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
          <p className="text-[11px] text-stone-400 text-center mt-2">
            AgriPulse combines Open-Meteo forecasts with curated extension knowledge and NVIDIA NIM reasoning.
          </p>
        </div>
      </main>
    </div>
  );
};
