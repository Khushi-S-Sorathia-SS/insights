'use client';

import { useState, useRef, useEffect, FormEvent } from 'react';
import ChartDisplay from './ChartDisplay';
import { ChartSchema } from '../utils/api-client';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  chart_schema?: ChartSchema;
  execution_time_ms?: number;
}

interface ChatWindowProps {
  messages: ChatMessage[];
  onSend: (message: string) => Promise<void>;
  disabled?: boolean;
  loading?: boolean;
}

export default function ChatWindow({
  messages,
  onSend,
  disabled = false,
  loading = false,
}: ChatWindowProps) {
  const [draft, setDraft] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedMessage = draft.trim();
    if (!trimmedMessage || disabled || loading) return;

    await onSend(trimmedMessage);
    setDraft('');
  };

  return (
    <div className="flex flex-col h-[500px] min-h-0 glass-card overflow-hidden">
      {/* Header */}
      <div className="px-8 py-5 border-b border-white/5 bg-white/[0.02] flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-2.5 h-2.5 rounded-full bg-secondary shadow-[0_0_8px_rgba(199,188,146,0.5)] animate-pulse"></div>
          <h2 className="text-xs font-black text-primary uppercase tracking-[0.2em]">Neural Cortex Assistant</h2>
        </div>
        <div className="text-[9px] text-slate-500 font-black tracking-widest uppercase">KERNEL: AETHER-V4</div>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 min-h-0 overflow-y-auto p-8 space-y-8 scroll-smooth custom-scrollbar"
      >
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center py-12">
            <div className="w-20 h-20 rounded-[2rem] bg-primary/5 flex items-center justify-center mb-6 border border-primary/10">
              <svg className="w-10 h-10 text-primary opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <p className="text-slate-300 font-black uppercase tracking-widest text-[10px]">Awaiting Instructions</p>
            <p className="text-xs text-slate-500 mt-3 max-w-[200px] leading-relaxed font-medium">Initialize the analysis by ingesting a dataset or querying existing metrics.</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`flex flex-col ${message.role === 'user' ? 'items-end' : 'items-start'} animate-fade-in`}
            >
              <div
                className={`max-w-[90%] rounded-[1.5rem] px-6 py-4 shadow-2xl ${message.role === 'user'
                  ? 'bg-primary/20 text-white border border-primary/30 rounded-tr-none'
                  : 'bg-surface/60 text-slate-100 border border-white/5 rounded-tl-none'
                  }`}
              >
                <div className="text-[9px] opacity-40 font-black uppercase mb-2 tracking-[0.2em]">
                  {message.role === 'user' ? 'Executive Inquiry' : 'Analytical Response'}
                </div>
                <p className="text-[13px] whitespace-pre-line leading-relaxed font-medium">{message.content}</p>

                {message.chart_schema && (
                  <div className="mt-6 -mx-2 h-[300px] rounded-xl overflow-hidden border border-white/5">
                    <ChartDisplay schema={message.chart_schema} />
                  </div>
                )}
              </div>
              {message.execution_time_ms !== undefined && (
                <div className="mt-2 text-[9px] text-slate-600 px-2 font-black tracking-widest">
                  COMPUTE TIME: {message.execution_time_ms}MS
                </div>
              )}
            </div>
          ))
        )}
        {loading && (
          <div className="flex flex-col items-start animate-pulse">
            <div className="bg-slate-900/60 rounded-[1.5rem] rounded-tl-none px-6 py-4 border border-white/5">
              <div className="flex gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce"></div>
                <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:0.2s]"></div>
                <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:0.4s]"></div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-8 border-t border-white/5 bg-white/[0.01]">
        <div className={`relative group transition-all duration-500 ${disabled ? 'opacity-40' : ''}`}>
          <textarea
            className="w-full bg-slate-950/60 border border-white/5 rounded-[1.5rem] p-5 pr-16 resize-none focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/30 transition-all text-slate-100 placeholder-slate-600 text-sm font-medium disabled:cursor-not-allowed"
            placeholder={disabled ? (loading ? 'Processing analysis...' : 'Activate workspace to query...') : 'Query the workforce intelligence...'}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e as any);
              }
            }}
            disabled={disabled || loading}
            rows={2}
          />
          <button
            type="submit"
            className="absolute right-4 bottom-4 p-3 bg-primary/20 hover:bg-primary/30 text-primary border border-primary/30 rounded-xl transition-all disabled:opacity-20 shadow-xl shadow-primary/10 active:scale-90"
            disabled={disabled || loading || !draft.trim()}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        <div className="mt-4 flex items-center justify-center gap-6">
          <p className="text-[9px] text-slate-600 uppercase tracking-widest font-black">Shift + Enter for multi-line</p>
          <div className="w-1 h-1 rounded-full bg-slate-800"></div>
          <p className="text-[9px] text-slate-600 uppercase tracking-widest font-black">Enter to dispatch</p>
        </div>
      </form>
    </div>
  );
}
