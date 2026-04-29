/**
 * Stub component for chat window.
 * To be implemented in Phase 8.
 */

export default function ChatWindow() {
  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-4">
        <div className="text-gray-500 text-center py-8">
          <p>No messages yet. Upload a CSV file to start chatting!</p>
        </div>
      </div>

      {/* Input area */}
      <div className="border-t pt-4">
        <textarea
          className="w-full border border-gray-300 rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Ask a question about your dataset..."
          disabled
          rows={3}
        />
        <button
          className="mt-3 w-full bg-blue-500 text-white rounded-lg py-2 font-medium disabled:opacity-50"
          disabled
        >
          Send
        </button>
      </div>
    </div>
  );
}
