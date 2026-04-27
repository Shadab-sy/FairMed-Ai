import { useState } from 'react';

export default function Landing({ onSearch }) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query);
      setQuery('');
    }
  };

  const handleChipClick = (text) => {
    setQuery(text);
  };

  return (
    <main className="flex-1 flex items-center justify-center px-4 py-16">
      <div className="w-full max-w-2xl animate-fade-in">
        {/* Background Decorative Blobs */}
        <div className="absolute top-20 left-10 w-72 h-72 bg-indigo-200 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse-subtle" />
        <div className="absolute bottom-20 right-10 w-72 h-72 bg-emerald-200 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse-subtle" />

        <div className="relative z-10 text-center mb-12">
          <h1 className="text-5xl md:text-6xl font-bold text-slate-900 mb-4 leading-tight">
            What symptoms are you experiencing?
          </h1>
          <p className="text-xl text-slate-600 mb-8">
            Describe how you're feeling and I'll help identify possible conditions
          </p>
        </div>

        {/* Search Input */}
        <form onSubmit={handleSubmit} className="mb-8 relative z-10">
          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. fever, headache, fatigue..."
              className="flex-1 px-6 py-4 rounded-2xl bg-white border-2 border-slate-200 text-lg focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 shadow-soft transition-all duration-200"
            />
            <button
              type="submit"
              disabled={!query.trim()}
              className="px-8 py-4 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-2xl shadow-soft transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Start Assessment →
            </button>
          </div>
        </form>

        {/* Quick Pick Chips */}
        <div className="mb-12 relative z-10">
          <p className="text-sm text-slate-500 font-medium mb-3">Quick picks:</p>
          <div className="flex flex-wrap gap-3">
            {[
              { icon: '🤒', label: 'Fever & Chills' },
              { icon: '😮‍💨', label: 'Breathing Issues' },
              { icon: '🤕', label: 'Head Pain' }
            ].map((chip) => (
              <button
                key={chip.label}
                onClick={() => handleChipClick(chip.label)}
                className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-full hover:border-indigo-400 hover:bg-indigo-50 transition-all duration-200 shadow-sm text-slate-700 font-medium"
              >
                <span>{chip.icon}</span>
                <span>{chip.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Disclaimer */}
        <div className="relative z-10 text-center text-sm text-slate-600 bg-yellow-50 border border-yellow-200 rounded-xl p-4">
          ⚠️ Not a substitute for professional medical advice
        </div>
      </div>
    </main>
  );
}
