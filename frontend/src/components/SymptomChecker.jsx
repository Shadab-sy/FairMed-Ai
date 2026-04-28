import { useState, useEffect, useRef } from 'react';
import { CheckCircle2, XCircle, Loader } from 'lucide-react';

// ── SYMPTOM QUESTION TREE ────────────────────────────────────────────────────
const FOLLOW_UP_GROUPS = {
  respiratory: [
    { symptom: 'cough', question: 'Do you have a cough?' },
    { symptom: 'shortness_of_breath', question: 'Are you experiencing shortness of breath?' },
    { symptom: 'wheezing', question: 'Do you hear a wheezing sound when breathing?' },
    { symptom: 'chest_tightness', question: 'Do you feel tightness in your chest?' },
  ],
  pain: [
    { symptom: 'headache', question: 'Do you have a headache?' },
    { symptom: 'back_pain', question: 'Do you have back pain?' },
    { symptom: 'abdominal_pain', question: 'Do you have abdominal or stomach pain?' },
    { symptom: 'burning_chest_pain', question: 'Do you experience burning chest pain?' },
    { symptom: 'joint_pain', question: 'Do you have pain in your joints?' },
  ],
  general: [
    { symptom: 'fatigue', question: 'Are you feeling unusually tired or fatigued?' },
    { symptom: 'fever', question: 'Do you have a fever?' },
    { symptom: 'nausea', question: 'Are you feeling nauseous?' },
    { symptom: 'vomiting', question: 'Have you been vomiting?' },
    { symptom: 'dizziness', question: 'Are you feeling dizzy?' },
    { symptom: 'loss_of_appetite', question: 'Have you lost your appetite?' },
  ],
  skin: [
    { symptom: 'skin_rash', question: 'Do you have a skin rash?' },
    { symptom: 'acne_or_pimples', question: 'Do you have acne or pimples?' },
    { symptom: 'itching_of_skin', question: 'Is your skin itchy?' },
  ],
};

const ALL_QUESTIONS = [
  ...FOLLOW_UP_GROUPS.general,
  ...FOLLOW_UP_GROUPS.respiratory,
  ...FOLLOW_UP_GROUPS.pain,
  ...FOLLOW_UP_GROUPS.skin,
];

const MIN_SYMPTOMS_TO_PREDICT = 3;
const MAX_QUESTIONS = 10;

function parseInitialSymptoms(query) {
  if (!query) return [];

  return query
    .toLowerCase()
    .replace(/[,/]+/g, ' ')
    .replace(/\b(and|with|also|plus|alongside)\b/g, ' ')
    .split(/\s+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const aliases = {
        cold: 'cold',
        fever: 'fever',
        fatigue: 'fatigue',
        tired: 'fatigue',
        nausea: 'nausea',
        nauseous: 'nausea',
        dizzy: 'dizziness',
        dizziness: 'dizziness',
        cough: 'cough',
        headache: 'headache',
      };
      return aliases[part] || part.replace(/-/g, '_');
    })
    .filter((part, index, all) => all.indexOf(part) === index);
}

// ── API HELPER ──────────────────────────────────────────────────────────────
async function callPredictAPI(message) {
  try {
    const res = await fetch('http://localhost:8000/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    if (!res.ok) throw new Error('Prediction failed');
    return await res.json();
  } catch (err) {
    console.error('API error:', err);
    throw err;
  }
}

export default function SymptomChecker({ initialQuery, onResults }) {
  const initialSymptoms = parseInitialSymptoms(initialQuery);
  const [phase, setPhase] = useState('intro');
  const [age, setAge] = useState(30);
  const [gender, setGender] = useState('male');
  const [confirmedSymptoms, setConfirmedSymptoms] = useState(() => initialSymptoms);
  const [askedSymptoms, setAskedSymptoms] = useState(() => new Set(initialSymptoms));
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [answerHistory, setAnswerHistory] = useState([]);
  const [fullStory, setFullStory] = useState(initialQuery || '');
  const chatEndRef = useRef(null);

  // Scroll to latest chat message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [answerHistory, currentQuestion, phase]);

  const getFallbackNextQuestion = (asked) => {
    return ALL_QUESTIONS.find(q => !asked.has(q.symptom)) || null;
  };

  const getNextQuestion = async (story) => {
    try {
      const data = await callPredictAPI(story);
      // We also update our local confirmed symptoms based on the backend extraction
      if (data.detected_symptoms) {
          setConfirmedSymptoms(data.detected_symptoms);
      }
      if (data.next_question) {
        return {
          question: data.next_question,
          // Extract symptom keyword if possible
          symptom: data.next_question.toLowerCase().match(/chest pain|fever|cough|headache|fatigue|nausea|dizzy|dizziness|vomiting|shortness of breath|diarrhea/)?.[0]?.replace(/ /g, '_') || 'unknown'
        };
      }
    } catch {
      // API failure or 422
    }
    return getFallbackNextQuestion(askedSymptoms);
  };

  const startQuestioning = async () => {
    // initial query is handled when start is clicked
    const next = await getNextQuestion(fullStory);
    setCurrentQuestion(next);
    setPhase('questioning');
    setAnswerHistory([{
      type: 'system',
      text: "I'll use AI-guided follow-up questions to narrow things down."
    }]);
  };

  const handleAnswer = async (answer) => {
    if (!currentQuestion) return;

    const newAsked = new Set([...askedSymptoms, currentQuestion.symptom]);
    setAskedSymptoms(newAsked);

    const newHistory = [
      ...answerHistory,
      { type: 'question', text: currentQuestion.question },
      { type: 'answer', text: answer ? 'Yes' : 'No' }
    ];
    setAnswerHistory(newHistory);

    let newStory = fullStory;
    if (answer) {
      newStory = `${fullStory}. Yes, I have ${currentQuestion.symptom.replace(/_/g, ' ')}`;
    } else {
      newStory = `${fullStory}. No, I do not have ${currentQuestion.symptom.replace(/_/g, ' ')}`;
    }
    setFullStory(newStory);

    const questionsAsked = newHistory.filter(h => h.type === 'question').length;
    // We don't rely on strict symptom count since backend does it, just stop after 10 questions
    const shouldStop = questionsAsked >= MAX_QUESTIONS;

    if (shouldStop) {
      setPhase('loading');
      setAnswerHistory([...newHistory, {
        type: 'system',
        text: `Analyzing your responses...`
      }]);

      try {
        const data = await callPredictAPI(newStory);
        const formatted = (data.top_predictions || []).map(p => ({
          disease: p.disease,
          confidence: Math.round(p.confidence)
        }));
        onResults(formatted, data.detected_symptoms || confirmedSymptoms, age, gender, {
          explanation: null,
          factors: [],
          nextQuestion: data.next_question,
          questionSource: 'gemini'
        });
        setPhase('results');
      } catch {
        setPhase('error');
        setAnswerHistory([...newHistory, {
          type: 'error',
          text: 'Failed to get predictions. Please try again.'
        }]);
      }
    } else {
      const next = await getNextQuestion(newStory);
      if (!next) {
          setPhase('loading');
          try {
            const data = await callPredictAPI(newStory);
            const formatted = (data.top_predictions || []).map(p => ({
              disease: p.disease,
              confidence: Math.round(p.confidence)
            }));
            onResults(formatted, data.detected_symptoms || confirmedSymptoms, age, gender, {
              explanation: null,
              factors: [],
              nextQuestion: null,
              questionSource: 'gemini'
            });
            setPhase('results');
          } catch {
            setPhase('error');
          }
      } else {
          setCurrentQuestion(next);
      }
    }
  };

  const questionsAsked = answerHistory.filter(h => h.type === 'question').length;
  const progress = Math.min((questionsAsked / MAX_QUESTIONS) * 100, 100);

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* INTRO PHASE */}
      {phase === 'intro' && (
        <div className="bg-white rounded-2xl shadow-soft p-8 animate-fade-in">
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Assessment Details</h2>
          <p className="text-slate-600 mb-6">I'll ask a few quick questions to help narrow things down</p>

          {initialQuery && (
            <div className="bg-indigo-50 border border-indigo-200 rounded-xl px-4 py-3 mb-6 flex items-center gap-2">
              <CheckCircle2 size={18} className="text-indigo-600" />
              <span className="text-sm text-indigo-900">
                Starting with: <strong className="capitalize">{initialQuery}</strong>
              </span>
            </div>
          )}

          <div className="space-y-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Age</label>
              <input
                type="number"
                value={age}
                onChange={(e) => setAge(parseInt(e.target.value) || 30)}
                className="w-full px-4 py-3 rounded-lg border-2 border-slate-200 focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Gender</label>
              <div className="flex gap-3">
                {['male', 'female'].map((g) => (
                  <button
                    key={g}
                    onClick={() => setGender(g)}
                    className={`flex-1 py-3 rounded-lg font-medium capitalize transition-all ${
                      gender === g
                        ? 'bg-indigo-600 text-white shadow-soft'
                        : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    }`}
                  >
                    {g}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <button
            onClick={startQuestioning}
            className="w-full px-6 py-4 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg shadow-soft transition-all duration-200"
          >
            Begin Assessment
          </button>
        </div>
      )}

      {/* QUESTIONING PHASE */}
      {(phase === 'questioning' || phase === 'loading') && (
        <div className="bg-white rounded-2xl shadow-soft p-6 animate-fade-in">
          {/* Progress Bar */}
          <div className="mb-6">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-medium text-slate-600">Progress</span>
              <span className="text-xs font-medium text-indigo-600">
                {confirmedSymptoms.length} symptoms
              </span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
              <div
                className="bg-indigo-600 h-full rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Chat History */}
          <div className="space-y-3 mb-6 max-h-96 overflow-y-auto">
            {answerHistory.map((item, i) => (
              <div key={i} className={`flex ${item.type === 'answer' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`rounded-lg px-4 py-2 text-sm max-w-xs ${
                    item.type === 'answer'
                      ? 'bg-indigo-600 text-white rounded-br-none'
                      : item.type === 'system'
                      ? 'bg-slate-100 text-slate-600 italic text-xs'
                      : 'bg-slate-50 border border-slate-200 text-slate-700 rounded-bl-none'
                  }`}
                >
                  {item.text}
                </div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          {/* Current Question */}
          {phase === 'questioning' && currentQuestion && (
            <div>
              <div className="bg-slate-50 border border-slate-200 rounded-lg px-4 py-3 text-slate-700 text-sm mb-4 rounded-bl-none">
                {currentQuestion.question}
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => handleAnswer(true)}
                  className="flex-1 flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white py-3 rounded-lg font-semibold transition-all"
                >
                  <CheckCircle2 size={18} /> Yes
                </button>
                <button
                  onClick={() => handleAnswer(false)}
                  className="flex-1 flex items-center justify-center gap-2 bg-slate-200 hover:bg-slate-300 text-slate-700 py-3 rounded-lg font-semibold transition-all"
                >
                  <XCircle size={18} /> No
                </button>
              </div>
            </div>
          )}

          {/* Loading State */}
          {phase === 'loading' && (
            <div className="flex items-center justify-center gap-3 py-8 text-indigo-600">
              <Loader size={20} className="animate-spin-gentle" />
              <span className="text-sm font-medium">Analyzing your symptoms...</span>
            </div>
          )}
        </div>
      )}

      {/* RESULTS PHASE */}
      {phase === 'results' && (
        <div className="text-center py-8">
          <Loader size={40} className="animate-spin-gentle text-indigo-600 mx-auto mb-4" />
          <p className="text-slate-600">Preparing your results...</p>
        </div>
      )}
    </div>
  );
}
