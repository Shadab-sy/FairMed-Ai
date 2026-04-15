import React, { useState } from 'react';
import { Scale, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';

const BiasToggle = ({ noBias = true }) => {
  const [isChecked, setIsChecked] = useState(false);

  return (
    <div className="glass-panel p-6 animate-fade-in" style={{ animationDelay: '0.1s' }}>
      <div className="flex items-center justify-between mb-6 border-b border-slate-100 pb-4">
        <div className="flex items-center gap-3">
          <div className="bg-slate-100 p-2 rounded-lg text-slate-600">
            <Scale size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-800">Bias Detection</h3>
            <p className="text-xs text-slate-500">Check for demographic disparities</p>
          </div>
        </div>
        
        <label className="relative inline-flex items-center cursor-pointer">
          <input 
            type="checkbox" 
            className="sr-only peer" 
            checked={isChecked}
            onChange={() => setIsChecked(!isChecked)}
          />
          <div className="w-14 h-7 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-primary shadow-inner"></div>
          <span className="ml-3 text-sm font-medium text-slate-600 select-none">
            {isChecked ? 'Running' : 'Check Fairness'}
          </span>
        </label>
      </div>

      <div className={`transition-all duration-500 overflow-hidden ${isChecked ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className={`p-4 rounded-xl mb-4 flex items-start gap-3 ${noBias ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'}`}>
          {noBias ? <ShieldCheck size={24} className="shrink-0" /> : <AlertTriangle size={24} className="shrink-0" />}
          <div>
            <h4 className="font-semibold">{noBias ? 'No Significant Bias Detected' : 'Potential Bias Found'}</h4>
            <p className="text-sm mt-1 opacity-90">
              {noBias 
                ? 'The model maintains consistent confidence across major demographic groups for this symptom set.'
                : 'The model shows a >5% variance in confidence between demographic groups. Review recommended.'}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
            <h5 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">Male (Baseline)</h5>
            <div className="flex items-end justify-between">
              <span className="text-xl font-bold text-slate-800">89%</span>
              <span className="text-xs text-slate-400">Confidence</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-1.5 mt-2">
              <div className="bg-slate-400 h-1.5 rounded-full" style={{ width: '89%' }}></div>
            </div>
          </div>
          
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
            <h5 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">Female (Comparative)</h5>
            <div className="flex items-end justify-between">
              <span className="text-xl font-bold text-slate-800">{noBias ? '88%' : '74%'}</span>
              <span className="text-xs text-slate-400">Confidence</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-1.5 mt-2">
              <div className={`h-1.5 rounded-full ${noBias ? 'bg-success' : 'bg-warning'}`} style={{ width: noBias ? '88%' : '74%' }}></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BiasToggle;
