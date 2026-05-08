'use client';

import React, { useRef, useState } from 'react';

interface FileUploadProps {
  onUpload: (file: File) => Promise<void>;
  disabled?: boolean;
}

export default function FileUpload({ onUpload, disabled = false }: FileUploadProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [status, setStatus] = useState<string>('');

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setStatus('Ingesting data...');
    try {
      await onUpload(file);
      setStatus('Ingestion complete. Analysis ready.');
    } catch (error) {
      setStatus('Ingestion failed. Retry required.');
    }
  };

  return (
    <div className="border-2 border-dashed border-white/10 rounded-xl p-8 text-center bg-white/5 hover:bg-white/10 transition-all cursor-pointer group">
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        className="hidden"
        id="file-input"
        onChange={handleFileChange}
        disabled={disabled}
      />
      <label
        htmlFor="file-input"
        className={`cursor-pointer block ${disabled ? 'opacity-30 pointer-events-none' : ''}`}
      >
        <div className="w-12 h-12 rounded-full bg-indigo-500/10 flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
          <svg className="w-6 h-6 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        <p className="text-slate-300 text-sm font-medium">
          Drop CSV vectors here, or click to browse
        </p>
        <p className="text-slate-500 text-[10px] mt-2 uppercase tracking-widest font-bold">
          MAX 10MB • CSV FORMAT ONLY
        </p>
      </label>
      {status && (
        <div className="mt-6 flex items-center justify-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></div>
          <p className="text-[11px] font-bold text-indigo-300 uppercase tracking-tighter">{status}</p>
        </div>
      )}
    </div>
  );
}
