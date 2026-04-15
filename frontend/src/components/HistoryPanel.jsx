import React from 'react';
import { X, Clock, MessageSquare, Plus } from 'lucide-react';

const HistoryPanel = ({ isOpen, onClose, history, onSelectHistory, onNewSearch }) => {
  return (
    <>
      {/* Backdrop overlay for mobile */}
      <div 
        className={`fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-40 transition-opacity duration-300 md:hidden ${isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
        onClick={onClose}
      />
      
      {/* Sidebar Panel */}
      <div className={`fixed top-0 left-0 h-full w-72 bg-white/95 backdrop-blur-xl border-r border-slate-200/60 shadow-xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        
        <div className="p-4 flex items-center justify-between border-b border-slate-100">
          <div className="flex items-center gap-2 text-slate-800 font-semibold">
            <Clock size={18} className="text-primary" />
            <span>History</span>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-lg text-slate-500 transition-colors md:hidden">
            <X size={20} />
          </button>
        </div>
        
        <div className="p-4">
          <button 
            onClick={onNewSearch}
            className="w-full flex items-center gap-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 py-3 px-4 rounded-xl transition-all duration-200 font-medium text-sm"
          >
            <Plus size={16} />
            New Assessment
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 px-2">Previous Searches</h4>
          
          {history.length === 0 ? (
            <div className="text-center p-4 text-sm text-slate-500">
              No recent searches found.
            </div>
          ) : (
            history.map((item) => (
              <button
                key={item.id}
                onClick={() => onSelectHistory(item.query)}
                className="w-full text-left p-3 rounded-xl hover:bg-primary/5 border border-transparent hover:border-primary/10 transition-colors duration-200 group flex items-start gap-3"
              >
                <MessageSquare size={16} className="text-slate-400 mt-0.5 group-hover:text-primary transition-colors shrink-0" />
                <div>
                  <p className="text-sm text-slate-700 font-medium line-clamp-2 leading-snug group-hover:text-primary transition-colors">
                    {item.query}
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    {item.date}
                  </p>
                </div>
              </button>
            ))
          )}
        </div>
        
      </div>
    </>
  );
};

export default HistoryPanel;
