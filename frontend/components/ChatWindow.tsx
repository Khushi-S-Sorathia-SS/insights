'use client';

import React, { useState } from 'react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  chart_url?: string;
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

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedMessage = draft.trim();
    if (!trimmedMessage || disabled) {
      return;
    }

    await onSend(trimmedMessage);
    setDraft('');
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto mb-4 space-y-4 pr-2">
        {messages.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            <p>No messages yet. Upload a CSV file to start chatting!</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`rounded-xl p-4 ${
                message.role === 'user'
                  ? 'bg-blue-50 text-blue-900 self-end'
                  : 'bg-gray-100 text-gray-900 self-start'
              }`}
            >
              <div className="font-semibold text-sm mb-2 capitalize">{message.role}</div>
              <p className="whitespace-pre-line">{message.content}</p>
              {message.chart_url ? (
                <img
                  src={message.chart_url}
                  alt="Analysis chart"
                  className="mt-3 max-h-52 w-full rounded-lg object-contain"
                />
              ) : null}
            </div>
          ))
        )}
      </div>

      <form onSubmit={handleSubmit} className="border-t pt-4">
        <textarea
          className="w-full border border-gray-300 rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder={disabled ? 'Upload a CSV file to ask questions.' : 'Ask a question about your dataset...'}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          disabled={disabled || loading}
          rows={3}
        />
        <button
          type="submit"
          className="mt-3 w-full bg-blue-500 text-white rounded-lg py-2 font-medium disabled:opacity-50"
          disabled={disabled || loading || !draft.trim()}
        >
          {loading ? 'Sending…' : 'Send'}
        </button>
      </form>
    </div>
  );
}
