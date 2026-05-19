'use client';

import { useRef, useState, ChangeEvent } from 'react';

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
    <div className="border-2 border-dashed border-white/5 rounded-[2rem] p-10 text-center bg-slate-950/20 hover:bg-slate-950/40 hover:border-indigo-500/30 transition-all cursor-pointer group relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
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
        className={`cursor-pointer block relative z-10 ${disabled ? 'opacity-30 pointer-events-none' : ''}`}
      >
        <div className="w-16 h-16 rounded-2xl bg-indigo-500/5 flex items-center justify-center mx-auto mb-6 group-hover:scale-110 group-hover:bg-indigo-500/10 transition-all duration-500 border border-indigo-500/10">
          <svg className="w-8 h-8 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        </div>
        <p className="text-slate-200 text-sm font-black uppercase tracking-widest">
          Drop dataset vectors here
        </p>
        <p className="text-slate-500 text-[10px] mt-3 uppercase tracking-[0.2em] font-bold">
          MAX 10MB • CSV / XLSX ENCODING
        </p>
      </label>
      {status && (
        <div className="mt-8 flex items-center justify-center gap-3 animate-fade-in">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)] animate-pulse"></div>
          <p className="text-[10px] font-black text-emerald-400 uppercase tracking-[0.2em]">{status}</p>
        </div>
      )}
    </div>
  );
}
