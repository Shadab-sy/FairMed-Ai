import { X, Clock, Plus } from 'lucide-react';

export default function Sidebar({ history, onHistoryClick, isSidebarOpen, onClose }) {
  return (
    <>
      {/* Mobile Overlay - Only visible when sidebar is open on mobile */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-30 md:hidden transition-opacity duration-300"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar - Toggleable with smooth transition */}
      <aside
        className={`w-72 bg-white border-r border-slate-200 shadow-soft-lg flex flex-col 
          fixed md:relative top-16 md:top-0 bottom-0 left-0 z-40 
          transition-all duration-300 ease-out
          ${isSidebarOpen 
            ? 'translate-x-0' 
            : '-translate-x-full'
          }`}
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-100 flex items-center justify-between flex-shrink-0">
          <h2 className="text-lg font-bold text-slate-900">History</h2>
          <button
            onClick={onClose}
            className="md:hidden p-2 hover:bg-slate-100 rounded-lg transition-colors duration-150 flex-shrink-0"
            aria-label="Close sidebar"
          >
            <X size={20} className="text-slate-600" />
          </button>
        </div>

        {/* History List - Scrollable */}
        <div className="flex-1 overflow-y-auto p-4">
          {history.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <Clock size={32} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">No history yet</p>
              <p className="text-xs mt-2">Start a check to see it here</p>
            </div>
          ) : (
            <div className="space-y-2">
              {history.map((entry) => (
                <button
                  key={entry.id}
                  onClick={() => {
                    onHistoryClick(entry);
                    onClose();
                  }}
                  className="w-full text-left p-3 rounded-lg hover:bg-indigo-50 transition-colors duration-150 group"
                >
                  <div className="flex items-start gap-2">
                    <span className="text-lg mt-0.5 flex-shrink-0">🩺</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 truncate group-hover:text-indigo-600">
                        {entry.query}
                      </p>
                      <p className="text-xs text-slate-500 mt-1">{entry.date}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* New Check Button */}
        <div className="border-t border-slate-100 p-4 flex-shrink-0">
          <button
            onClick={onClose}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg shadow-soft transition-all duration-200 hover:shadow-lg"
          >
            <Plus size={18} />
            <span>New Check</span>
          </button>
        </div>
      </aside>
    </>
  );
}
