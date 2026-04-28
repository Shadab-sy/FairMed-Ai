import { CheckCircle2, Activity, RotateCcw, Save } from 'lucide-react';
import PredictionCard from './PredictionCard';

export default function ResultsPanel({
  predictions,
  insights,
  symptoms,
  age,
  gender,
  isLive,
  onStartNew,
  onSaveToHistory,
}) {
  const hasPredictions = predictions && predictions.length > 0;

  return (
    <div className="w-full max-w-xl mx-auto space-y-4 pb-8">

      {/* ── Status badge ───────────────────────────────────────────── */}
      <div className={`flex items-center gap-2 px-4 py-2 rounded-full w-fit text-sm font-semibold ${
        isLive
          ? 'bg-indigo-100 text-indigo-700'
          : 'bg-emerald-100 text-emerald-700'
      }`}>
        {isLive
          ? <><Activity size={15} className="animate-pulse" /> Updating live…</>
          : <><CheckCircle2 size={15} /> Assessment complete</>
        }
      </div>

      {/* ── Predictions — shown first and prominently ───────────────── */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 pt-5 pb-3 border-b border-slate-100">
          <h2 className="text-base font-bold text-slate-800 uppercase tracking-wide">
            Top Possible Conditions
          </h2>
          {isLive && (
            <p className="text-xs text-slate-400 mt-0.5">
              Refining as you answer follow-up questions
            </p>
          )}
        </div>

        <div className="p-5 space-y-4">
          {hasPredictions ? (
            predictions.map((pred, idx) => (
              <PredictionCard
                key={`${pred.disease}-${idx}`}
                disease={pred.disease}
                confidence={
                  typeof pred.confidence === 'number'
                    ? pred.confidence
                    : Math.round(pred.confidence)
                }
                rank={idx + 1}
              />
            ))
          ) : (
            <div className="text-center py-6 text-slate-400 text-sm">
              No prediction available yet — describe more symptoms in the chat.
            </div>
          )}
        </div>
      </div>

      {/* ── Confirmed symptoms ──────────────────────────────────────── */}
      {symptoms && symptoms.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-3">
            Symptoms Confirmed
          </h3>
          <div className="flex flex-wrap gap-2">
            {symptoms.map((s) => (
              <span
                key={s}
                className="px-3 py-1 bg-indigo-50 text-indigo-700 text-xs font-medium rounded-full capitalize"
              >
                {s.replace(/_/g, ' ')}
              </span>
            ))}
            {age && (
              <span className="px-3 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded-full">
                Age {age}
              </span>
            )}
            {gender && (
              <span className="px-3 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded-full capitalize">
                {gender}
              </span>
            )}
          </div>
        </div>
      )}

      {/* ── Disclaimer ─────────────────────────────────────────────── */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-xs text-amber-800">
        <strong>⚠️ Not a diagnosis.</strong> This tool is for informational purposes only.
        Always consult a qualified healthcare professional.
      </div>

      {/* ── Actions — only when done ────────────────────────────────── */}
      {!isLive && (
        <div className="flex gap-3">
          <button
            onClick={onStartNew}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl transition-colors"
          >
            <RotateCcw size={15} /> New Assessment
          </button>
          <button
            onClick={onSaveToHistory}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-semibold rounded-xl transition-colors border border-slate-200"
          >
            <Save size={15} /> Save
          </button>
        </div>
      )}
    </div>
  );
}
