'use client';

import { useState, useRef } from 'react';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (file: File, displayName: string) => Promise<void>;
  isUploading: boolean;
}

export default function UploadModal({ isOpen, onClose, onUpload, isUploading }: UploadModalProps) {
  const [displayName, setDisplayName] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
    }
  };

  const handleSubmit = async () => {
    if (!file || !displayName.trim()) return;
    
    try {
      setError(null);
      await onUpload(file, displayName.trim());
      setDisplayName('');
      setFile(null);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Upload failed. Please try again.');
    }
  };

  const isValid = file && displayName.trim().length > 0 && !isUploading;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-[#020617]/80 backdrop-blur-sm animate-in fade-in duration-300"
        onClick={!isUploading ? onClose : undefined}
      ></div>

      {/* Modal Content */}
      <div className="relative w-full max-w-xl glass-card overflow-hidden shadow-2xl shadow-indigo-500/10 animate-in zoom-in-95 fade-in duration-300">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 via-transparent to-violet-500/5 pointer-events-none"></div>
        
        {/* Header */}
        <div className="px-8 py-6 border-b border-white/5 flex items-center justify-between bg-white/5">
          <div>
            <h2 className="text-xl font-black text-slate-100 tracking-tight">Deploy Intelligence</h2>
            <p className="text-[10px] text-indigo-400 font-black uppercase tracking-widest mt-1">New Dataset Workspace</p>
          </div>
          {!isUploading && (
            <button 
              onClick={onClose}
              className="p-2 rounded-xl hover:bg-white/5 text-slate-500 hover:text-white transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Body */}
        <div className="p-8 space-y-8">
          {/* Workspace Name Input */}
          <div className="space-y-3">
            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">
              Workspace Identifier <span className="text-indigo-500">*</span>
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. Q2 Performance Analysis"
              className="w-full bg-[#0b1326]/60 border border-white/10 rounded-2xl px-6 py-4 text-sm font-medium text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/50 transition-all"
              disabled={isUploading}
            />
          </div>

          {/* File Selection Area */}
          <div className="space-y-3">
             <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">
              Data Vector <span className="text-indigo-500">*</span>
            </label>
            <div 
              onClick={() => !isUploading && fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-3xl p-8 text-center transition-all cursor-pointer group relative overflow-hidden ${
                file 
                ? 'border-indigo-500/40 bg-indigo-500/5' 
                : 'border-white/5 bg-white/5 hover:border-indigo-500/20 hover:bg-white/10'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleFileChange}
              />
              
              <div className="relative z-10">
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4 transition-all duration-500 border ${
                  file ? 'bg-indigo-500/20 border-indigo-500/30 scale-110' : 'bg-white/5 border-white/10 group-hover:scale-110'
                }`}>
                  <svg className={`w-6 h-6 ${file ? 'text-indigo-400' : 'text-slate-500'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <p className="text-slate-200 text-xs font-bold uppercase tracking-widest">
                  {file ? file.name : 'Select CSV Dataset'}
                </p>
                <p className="text-slate-500 text-[9px] mt-2 font-medium tracking-widest uppercase">
                  {file ? `${(file.size / 1024).toFixed(1)} KB` : 'Max 10MB limit'}
                </p>
              </div>
            </div>
          </div>

          {error && (
            <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center gap-4 animate-in slide-in-from-top-2 duration-300">
              <svg className="w-5 h-5 text-rose-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-xs text-rose-400 font-medium">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-8 py-6 border-t border-white/5 bg-white/5 flex items-center justify-end gap-4">
          <button
            onClick={onClose}
            disabled={isUploading}
            className="px-6 py-3 rounded-xl text-xs font-black text-slate-500 uppercase tracking-widest hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!isValid}
            className={`px-8 py-3 rounded-xl text-xs font-black uppercase tracking-widest shadow-lg transition-all duration-300 ${
              isValid 
              ? 'bg-gradient-to-r from-indigo-500 to-violet-600 text-white shadow-indigo-500/20 hover:scale-105 active:scale-95' 
              : 'bg-white/5 text-slate-600 cursor-not-allowed shadow-none'
            }`}
          >
            {isUploading ? (
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
                Initializing...
              </div>
            ) : 'Deploy Workspace'}
          </button>
        </div>
      </div>
    </div>
  );
}
