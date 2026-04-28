import { useEffect, useState } from 'react';

const RANK_COLORS = [
  { bar: 'bg-indigo-600', badge: 'bg-indigo-100 text-indigo-700', label: 'Top Match' },
  { bar: 'bg-violet-500', badge: 'bg-violet-100 text-violet-700', label: '2nd' },
  { bar: 'bg-slate-400',  badge: 'bg-slate-100  text-slate-600',  label: '3rd' },
];

export default function PredictionCard({ disease, confidence, rank = 1 }) {
  const [fillWidth, setFillWidth] = useState(0);
  const color = RANK_COLORS[Math.min(rank - 1, RANK_COLORS.length - 1)];

  // Animate bar on mount or when confidence changes
  useEffect(() => {
    const t = setTimeout(() => setFillWidth(confidence), 80);
    return () => clearTimeout(t);
  }, [confidence]);

  return (
    <div className="space-y-2">
      {/* Disease name + badge + percentage */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`shrink-0 text-xs font-bold px-2 py-0.5 rounded-full ${color.badge}`}>
            {color.label}
          </span>
          <span className="font-semibold text-slate-900 text-sm truncate">{disease}</span>
        </div>
        <span className="shrink-0 text-lg font-bold text-slate-800">{confidence}%</span>
      </div>

      {/* Confidence bar */}
      <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${color.bar}`}
          style={{ width: `${fillWidth}%` }}
        />
      </div>
    </div>
  );
}
