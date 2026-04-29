/**
 * Stub component for file upload.
 * To be implemented in Phase 8.
 */

export default function FileUpload() {
  return (
    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
      <input
        type="file"
        accept=".csv"
        className="hidden"
        id="file-input"
      />
      <label
        htmlFor="file-input"
        className="cursor-pointer block"
      >
        <p className="text-gray-600 text-sm">
          Drag and drop your CSV file here, or click to select
        </p>
        <p className="text-gray-400 text-xs mt-2">
          Max 10 MB • CSV format only
        </p>
      </label>
    </div>
  );
}
