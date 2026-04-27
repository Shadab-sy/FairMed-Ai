import { CheckCircle2, HelpCircle, Sparkles } from 'lucide-react';
import PredictionCard from './PredictionCard';

export default function ResultsPanel({ predictions, insights, symptoms, age, gender, onStartNew, onSaveToHistory }) {
  return (
    <div className="w-full max-w-2xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="flex justify-center mb-4">
          <div className="bg-emerald-100 rounded-full p-3">
            <CheckCircle2 size={32} className="text-emerald-600" />
          </div>
        </div>
        <h2 className="text-3xl font-bold text-slate-900 mb-2">Assessment Complete</h2>
        <p className="text-slate-600">Here are your top predictions based on your symptoms</p>
      </div>

      {/* Confirmed Symptoms */}
      <div className="bg-white rounded-2xl shadow-soft p-6 mb-6">
        <h3 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">
          Symptoms Confirmed
        </h3>
        <div className="flex flex-wrap gap-2">
          {symptoms.map((symptom) => (
            <span
              key={symptom}
              className="px-3 py-1 bg-indigo-100 text-indigo-700 text-sm font-medium rounded-full capitalize"
            >
              {symptom.replace(/_/g, ' ')}
            </span>
          ))}
          <span className="px-3 py-1 bg-slate-100 text-slate-700 text-sm font-medium rounded-full">
            Age {age}
          </span>
          <span className="px-3 py-1 bg-slate-100 text-slate-700 text-sm font-medium rounded-full capitalize">
            {gender}
          </span>
        </div>
      </div>

      {/* Predictions */}
      <div className="space-y-4 mb-6">
        {predictions.map((pred, idx) => (
          <PredictionCard
            key={idx}
            disease={pred.disease}
            confidence={pred.confidence}
            rank={idx + 1}
          />
        ))}
      </div>

      {insights?.explanation && (
        <div className="bg-white rounded-2xl shadow-soft p-6 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={18} className="text-indigo-600" />
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              Model Explanation
            </h3>
          </div>
          <p className="text-sm text-slate-700 mb-4">{insights.explanation}</p>
          {insights.factors?.length > 0 && (
            <div className="space-y-2">
              {insights.factors.map((factor) => (
                <div key={factor.feature} className="flex items-center justify-between gap-3 text-sm">
                  <span className="capitalize text-slate-700">{factor.feature.replace(/_/g, ' ')}</span>
                  <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-1 rounded-full capitalize">
                    {factor.direction} · {factor.impact}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {insights?.nextQuestion && (
        <div className="bg-white rounded-2xl shadow-soft p-6 mb-6">
          <div className="flex items-center gap-2 mb-2">
            <HelpCircle size={18} className="text-indigo-600" />
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              Suggested Follow-Up
            </h3>
          </div>
          <p className="text-sm text-slate-700">{insights.nextQuestion}</p>
          <p className="text-xs text-slate-400 mt-2 capitalize">
            Source: {insights.questionSource || 'rules'}
          </p>
        </div>
      )}

      {/* Disclaimer */}
      <div className="bg-yellow-50 border-l-4 border-yellow-400 rounded-lg p-4 mb-6">
        <p className="text-sm text-yellow-800">
          <strong>⚠️ Important:</strong> This is an AI-assisted tool, not a medical diagnosis. 
          Please consult a qualified healthcare professional for proper diagnosis and treatment.
        </p>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={onStartNew}
          className="flex-1 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg shadow-soft transition-all duration-200"
        >
          Start New Assessment
        </button>
        <button
          onClick={onSaveToHistory}
          className="flex-1 px-6 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg transition-all duration-200 border border-slate-200"
        >
          Save to History
        </button>
      </div>
    </div>
  );
}
