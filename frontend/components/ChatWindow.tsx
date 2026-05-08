'use client';

import React, { useState, useRef, useEffect } from 'react';
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
    <div className="flex flex-col h-full glass-card overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/5 bg-white/5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
          <h2 className="text-sm font-bold text-slate-100 uppercase tracking-widest">InsightAI Assistant</h2>
        </div>
        <div className="text-[10px] text-slate-500 font-mono">MODEL: AGENTIC-ANALYZER-V1</div>
      </div>

      {/* Messages */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth"
      >
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center opacity-40 py-12">
            <div className="w-16 h-16 rounded-full bg-indigo-500/10 flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <p className="text-slate-300 font-medium">Ready for analysis</p>
            <p className="text-xs text-slate-500 mt-2 max-w-xs">Upload your dataset and ask questions like "Compare average salary by department" or "Show attrition trends".</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`flex flex-col ${message.role === 'user' ? 'items-end' : 'items-start'} animate-fade-in`}
            >
              <div 
                className={`max-w-[90%] rounded-2xl px-5 py-3.5 shadow-lg ${
                  message.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-tr-none'
                    : 'bg-slate-800 text-slate-100 border border-white/5 rounded-tl-none'
                }`}
              >
                <div className="text-[10px] opacity-60 font-bold uppercase mb-1 tracking-tighter">
                  {message.role}
                </div>
                <p className="text-sm whitespace-pre-line leading-relaxed">{message.content}</p>
                
                {message.chart_schema && (
                  <div className="mt-4 -mx-2">
                    <ChartDisplay schema={message.chart_schema} />
                  </div>
                )}
              </div>
              {message.execution_time_ms !== undefined && (
                <div className="mt-1.5 text-[9px] text-slate-500 px-2 font-mono">
                  PROCESSED IN {message.execution_time_ms}MS
                </div>
              )}
            </div>
          ))
        )}
        {loading && (
          <div className="flex flex-col items-start animate-pulse">
            <div className="bg-slate-800 rounded-2xl rounded-tl-none px-5 py-3.5 border border-white/5">
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce"></div>
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce [animation-delay:0.2s]"></div>
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce [animation-delay:0.4s]"></div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-6 border-t border-white/5 bg-white/5">
        <div className="relative group">
          <textarea
            className="w-full bg-slate-900/50 border border-white/10 rounded-xl p-4 pr-14 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 transition-all text-slate-100 placeholder-slate-600 text-sm"
            placeholder={disabled ? 'Upload a dataset to activate analysis...' : 'Ask InsightAI about your data...'}
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
            className="absolute right-3 bottom-3 p-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors disabled:opacity-30 disabled:hover:bg-indigo-600 shadow-lg shadow-indigo-500/20"
            disabled={disabled || loading || !draft.trim()}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        <p className="mt-3 text-[10px] text-center text-slate-500 uppercase tracking-widest font-medium">
          Shift + Enter for new line · Press Enter to analyze
        </p>
      </form>
    </div>
  );
}
