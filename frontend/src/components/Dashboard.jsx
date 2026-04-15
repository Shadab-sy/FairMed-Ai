import React, { useState, useEffect } from 'react';
import PredictionCard from './PredictionCard';
import BiasToggle from './BiasToggle';
import ExplanationChat from './ExplanationChat';
import { ArrowLeft } from 'lucide-react';

const Dashboard = ({ query, onBack }) => {
  // Mock API resolution after some typing delay
  const [data, setData] = useState(null);

  useEffect(() => {
    // We already display a spinner in Landing before showing Dashboard.
    // So Dashboard mounts when data is ready. We'll set mock data immediately.
    
    // In a real app, this data would come from the backend.
    setData({
      disease: "Acute Upper Respiratory Infection",
      confidence: 89,
      severity: "low",
      explanation: `Based on your symptoms: "${query}".\n\nThe presence of fever, chills, and a persistent cough strongly suggests an upper respiratory infection, commonly known as a cold or mild flu. Your symptoms do not currently indicate a severe lower respiratory issue like pneumonia, as you haven't reported severe shortness of breath.\n\nRecommendation: Rest, stay hydrated, and monitor the fever. If symptoms persist for more than 7 days, please consult a physician.`,
      noBias: true
    });
  }, [query]);

  if (!data) return null;

  return (
    <div className="w-full max-w-6xl mx-auto px-4 mt-8 pb-12 animate-fade-in">
      <button 
        onClick={onBack}
        className="flex items-center gap-2 text-slate-500 hover:text-primary transition-colors duration-200 mb-8 px-4 py-2 rounded-full hover:bg-white/50 backdrop-blur-sm self-start"
      >
        <ArrowLeft size={18} />
        <span className="font-medium text-sm">New Search</span>
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Prediction and Bias */}
        <div className="lg:col-span-1 flex flex-col gap-6">
          <PredictionCard 
            disease={data.disease} 
            confidence={data.confidence} 
            severity={data.severity} 
          />
          <BiasToggle noBias={data.noBias} />
        </div>

        {/* Right Column: AI Explanation */}
        <div className="lg:col-span-2">
          <ExplanationChat query={query} explanation={data.explanation} />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
