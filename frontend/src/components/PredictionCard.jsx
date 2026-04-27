import { useEffect, useState } from 'react';

export default function PredictionCard({ disease, confidence, rank = 1 }) {
  const [fillWidth, setFillWidth] = useState(0);

  useEffect(() => {
    // Animate the confidence bar on mount
    setTimeout(() => setFillWidth(confidence), 100);
  }, [confidence]);

  if (rank === 1) {
    return (
      <div className="bg-white rounded-2xl shadow-soft-lg p-8 border-l-4 border-indigo-600">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-3xl font-bold text-slate-900">{disease}</h3>
          <span className="px-3 py-1 bg-indigo-100 text-indigo-700 text-xs font-bold rounded-full">
            Top Match
          </span>
        </div>

        <div className="mb-6">
          <div className="flex items-end gap-2 mb-3">
            <span className="text-5xl font-bold text-indigo-600">{confidence}%</span>
            {confidence > 60 && (
              <span className="text-sm text-amber-600 font-semibold mb-1">High Confidence</span>
            )}
          </div>

          <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
            <div
              className="bg-indigo-600 h-full rounded-full transition-all duration-1000 ease-out"
              style={{ width: `${fillWidth}%` }}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-soft p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <p className="font-semibold text-slate-900 text-sm">{disease}</p>
          <p className="text-2xl font-bold text-slate-700 mt-2">{confidence}%</p>
        </div>
        <span className="text-2xl text-slate-400">{rank}</span>
      </div>

      <div className="mt-3 w-full bg-slate-200 rounded-full h-2 overflow-hidden">
        <div
          className="bg-indigo-400 h-full rounded-full transition-all duration-1000 ease-out"
          style={{ width: `${fillWidth}%` }}
        />
      </div>
    </div>
  );
}
