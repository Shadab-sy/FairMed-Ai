import React, { useState } from 'react';
import { Search, Sparkles, Loader2 } from 'lucide-react';

const Landing = ({ onSearch, isProcessing }) => {
  const [query, setQuery] = useState('');
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim() && !isProcessing) {
      onSearch(query);
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center w-full max-w-3xl mx-auto px-4 mt-20 animate-fade-in">
      <div className="text-center mb-8">
        <h1 className="text-4xl md:text-5xl font-extrabold text-slate-800 mb-4 tracking-tight">
          Smarter, fairer healthcare <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-emerald-500">
            powered by AI.
          </span>
        </h1>
        <p className="text-slate-500 text-lg md:text-xl max-w-2xl mx-auto">
          Describe your symptoms below to get an AI-driven initial assessment, complete with built-in fairness checks.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="w-full relative group">
        <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none text-slate-400 group-focus-within:text-primary transition-colors duration-300">
          <Search size={22} className={isProcessing ? "hidden" : "block"} />
          <Loader2 size={22} className={`animate-spin ${isProcessing ? "block text-primary" : "hidden"}`} />
        </div>
        
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter your symptoms (e.g., fever, cough, headache...)"
          className="w-full bg-white/80 backdrop-blur-xl border-2 border-slate-200/60 rounded-full py-5 pl-14 pr-32 text-lg text-slate-800 focus:outline-none focus:border-primary/50 focus:ring-4 focus:ring-primary/20 shadow-[0_8px_30px_rgb(0,0,0,0.04)] transition-all duration-300 placeholder:text-slate-400"
          disabled={isProcessing}
        />
        
        <div className="absolute inset-y-0 right-2 flex items-center">
          <button
            type="submit"
            disabled={!query.trim() || isProcessing}
            className="flex items-center gap-2 bg-slate-900 hover:bg-primary text-white rounded-full px-6 py-3 font-medium transition-all duration-300 disabled:opacity-50 disabled:hover:bg-slate-900 disabled:cursor-not-allowed hover:shadow-lg hover:shadow-primary/30"
          >
            <Sparkles size={18} />
            <span className="hidden sm:inline">Analyze</span>
          </button>
        </div>
      </form>
      
      <div className="mt-12 flex flex-wrap justify-center gap-3">
        {['Fever and chills for 3 days', 'Persistent headache and blurred vision', 'Skin rash after taking medication', 'Shortness of breath climbing stairs'].map((suggestion, i) => (
          <button
            key={i}
            type="button"
            onClick={() => setQuery(suggestion)}
            className="text-sm bg-white border border-slate-200 text-slate-600 px-4 py-2 rounded-full hover:border-primary/30 hover:text-primary hover:bg-primary/5 transition-all duration-200 shadow-sm"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
};

export default Landing;
