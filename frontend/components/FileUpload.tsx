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

    if (!file) {
      return;
    }

    setStatus('Uploading...');

    try {
      await onUpload(file);
      setStatus('Upload complete! You can now ask questions.');
    } catch (error) {
      setStatus('Upload failed. Please try again.');
    }
  };

  return (
    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
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
        className={`cursor-pointer block ${disabled ? 'opacity-50 pointer-events-none' : ''}`}
      >
        <p className="text-gray-600 text-sm">
          Drag and drop your CSV file here, or click to select
        </p>
        <p className="text-gray-400 text-xs mt-2">
          Max 10 MB • CSV format only
        </p>
      </label>
      <div className="mt-4 text-sm text-gray-600">{status}</div>
    </div>
  );
}
