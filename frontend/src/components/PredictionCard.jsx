import React from 'react';
import { ActivitySquare, AlertCircle } from 'lucide-react';

const PredictionCard = ({ disease, confidence, severity }) => {
  return (
    <div className="glass-panel p-6 animate-fade-in relative overflow-hidden">
      <div className="absolute top-0 left-0 w-1 h-full bg-primary"></div>
      
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-1">Top Prediction</h3>
          <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            {disease}
            {severity === 'high' && <AlertCircle className="text-warning h-5 w-5" />}
          </h2>
        </div>
        <div className="bg-primary/10 text-primary p-3 rounded-full">
          <ActivitySquare size={24} />
        </div>
      </div>
      
      <div>
        <div className="flex justify-between items-end mb-2">
          <span className="text-sm font-medium text-slate-600">Model Confidence</span>
          <span className="text-xl font-bold text-slate-800">{confidence}%</span>
        </div>
        <div className="w-full bg-slate-100 rounded-full h-3 mb-2 overflow-hidden shadow-inner">
          <div 
            className="bg-primary h-3 rounded-full transition-all duration-1000 ease-out relative"
            style={{ width: `${confidence}%` }}
          >
            <div className="absolute top-0 right-0 bottom-0 left-0 bg-white/20 animate-[pulse_2s_ease-in-out_infinite]"></div>
          </div>
        </div>
        <p className="text-xs text-slate-400">Based on analysis of 1M+ clinical records.</p>
      </div>
    </div>
  );
};

export default PredictionCard;
