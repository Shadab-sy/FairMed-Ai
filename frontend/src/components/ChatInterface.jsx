import { useState, useEffect, useRef } from 'react';
import { Send, Loader, RefreshCw, User } from 'lucide-react';

const INITIAL_MESSAGE = {
  role: 'assistant',
  text: "Hi! I'm here to help figure out what might be going on. Describe your symptoms and I'll give you an immediate assessment.",
};

const SYMPTOM_KEYWORDS = {
  'chest pain': 'burning_chest_pain',
  'chest discomfort': 'burning_chest_pain',
  'fever': 'fever',
  'cough': 'cough',
  'headache': 'headache',
  'fatigue': 'fatigue',
  'tired': 'fatigue',
  'nausea': 'nausea',
  'nauseous': 'nausea',
  'dizziness': 'dizziness',
  'dizzy': 'dizziness',
  'vomiting': 'vomiting',
  'shortness of breath': 'shortness_of_breath',
  'diarrhea': 'diarrhea',
  'sweating': 'sweating',
  'back pain': 'back_pain',
  'joint pain': 'joint_pain',
  'skin rash': 'skin_rash',
  'sore throat': 'throat_soreness',
  'loss of appetite': 'loss_of_appetite',
  'insomnia': 'insomnia',
};

function extractSymptomFromText(text) {
  const lower = text.toLowerCase();
  for (const [phrase, key] of Object.entries(SYMPTOM_KEYWORDS)) {
    if (lower.includes(phrase)) return key;
  }
  return null;
}

function isYesAnswer(text) {
  return /^(yes|yeah|yep|yup|y|sure|correct|true|1|absolutely|definitely|indeed)$/i.test(text.trim());
}

function isNoAnswer(text) {
  return /^(no|nope|nah|n|not|false|0|never|negative)$/i.test(text.trim());
}

// ── Setup screen shown before the first message ───────────────────────────
function SetupScreen({ onStart }) {
  const [ageInput, setAgeInput] = useState('');
  const [genderInput, setGenderInput] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const parsedAge = parseInt(ageInput, 10);
    if (!ageInput || isNaN(parsedAge) || parsedAge < 1 || parsedAge > 120) {
      setError('Please enter a valid age between 1 and 120.');
      return;
    }
    if (!genderInput) {
      setError('Please select a gender.');
      return;
    }
    onStart(parsedAge, genderInput);
  };

  return (
    <div className="flex flex-col h-full bg-slate-50 items-center justify-center p-6">
      <div className="w-full max-w-sm bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">

        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="bg-indigo-100 rounded-full p-2">
            <User size={20} className="text-indigo-600" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">Before we start</h2>
            <p className="text-xs text-slate-500">Helps the model give accurate predictions</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Age */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5 uppercase tracking-wide">
              Age
            </label>
            <input
              type="number"
              min="1"
              max="120"
              value={ageInput}
              onChange={(e) => { setAgeInput(e.target.value); setError(''); }}
              placeholder="e.g. 34"
              className="w-full px-4 py-2.5 border border-slate-300 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          {/* Gender */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5 uppercase tracking-wide">
              Biological sex
            </label>
            <div className="flex gap-2">
              {['male', 'female'].map((g) => (
                <button
                  key={g}
                  type="button"
                  onClick={() => { setGenderInput(g); setError(''); }}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-semibold capitalize transition-colors border ${
                    genderInput === g
                      ? 'bg-indigo-600 text-white border-indigo-600'
                      : 'bg-white text-slate-600 border-slate-300 hover:border-indigo-400 hover:text-indigo-600'
                  }`}
                >
                  {g}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <p className="text-xs text-red-500">{error}</p>
          )}

          <button
            type="submit"
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl transition-colors"
          >
            Start Assessment
          </button>
        </form>
      </div>
    </div>
  );
}

// ── Main chat component ───────────────────────────────────────────────────
export default function ChatInterface({ onResults, onStartNew }) {
  const [phase, setPhase] = useState('setup'); // 'setup' | 'chat'
  const [age, setAge] = useState(null);
  const [gender, setGender] = useState(null);

  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [confirmedSymptoms, setConfirmedSymptoms] = useState([]);
  const [nextQuestion, setNextQuestion] = useState(null);
  const [nextSymptom, setNextSymptom] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [isDone, setIsDone] = useState(false);
  const [isFinal, setIsFinal] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSetupComplete = (parsedAge, selectedGender) => {
    setAge(parsedAge);
    setGender(selectedGender);
    setPhase('chat');
  };

  const callPredictAPI = async (message) => {
    const res = await fetch('http://localhost:8000/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, age, gender }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const e = new Error(err.detail || 'Prediction failed');
      e.status = res.status;
      throw e;
    }
    return res.json();
  };

  const callFollowupAPI = async (sid, symptomKey, answered) => {
    const res = await fetch('http://localhost:8000/followup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sid,
        new_answer: { [symptomKey]: answered ? 1 : 0 },
        age,
        gender,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const e = new Error(err.detail || 'Followup failed');
      e.status = res.status;
      throw e;
    }
    return res.json();
  };

  const handleResponse = (data) => {
    const symptoms = data.detected_symptoms || confirmedSymptoms;
    if (data.detected_symptoms) setConfirmedSymptoms(data.detected_symptoms);

    if (data.top_predictions?.length && onResults) {
      onResults(data, symptoms, age, gender);
    }

    // Check if prediction is final (high confidence or max questions reached)
    const isFinalPrediction = data.is_final || false;
    setIsFinal(isFinalPrediction);

    if (data.next_question && !isFinalPrediction) {
      // Use symptom key from backend (more reliable than extracting from question)
      const sym = data.next_symptom_key || extractSymptomFromText(data.next_question);
      setNextSymptom(sym);
      setNextQuestion(data.next_question);
      setIsDone(false);
      setMessages((prev) => [...prev, { role: 'assistant', text: data.next_question }]);
    } else {
      setNextQuestion(null);
      setNextSymptom(null);
      setIsDone(true);
      const finalMessage = isFinalPrediction
        ? "Based on your symptoms, this is the most likely condition. You can start a new check or refine your symptoms."
        : "That's all I need. Your results are shown on the right.";
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: finalMessage },
      ]);
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading || isDone) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setIsLoading(true);
    setMessages((prev) => [...prev, { role: 'user', text: userMessage }]);

    const isFirstTurn = sessionId === null;

    try {
      let data;

      if (isFirstTurn) {
        data = await callPredictAPI(userMessage);
        if (data.session_id) setSessionId(data.session_id);
      } else {
        let symKey = nextSymptom;
        let answered;

        if (isYesAnswer(userMessage)) {
          answered = true;
        } else if (isNoAnswer(userMessage)) {
          answered = false;
        } else {
          const extracted = extractSymptomFromText(userMessage);
          if (extracted) {
            symKey = extracted;
            answered = true;
          } else {
            answered = true;
          }
        }

        if (!symKey && nextSymptom) symKey = nextSymptom;

        if (!symKey) {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', text: nextQuestion || 'Could you clarify your answer?' },
          ]);
          setIsLoading(false);
          return;
        }

        data = await callFollowupAPI(sessionId, symKey, answered);
      }

      handleResponse(data);
    } catch (err) {
      console.error('Chat error:', err);
      if (err.status === 422) {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', text: "I couldn't pick up any symptoms. Try: 'I have a fever and cough'." },
        ]);
        if (isFirstTurn) setSessionId(null);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', text: 'Connection error. Please try again.' },
        ]);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setPhase('setup');
    setAge(null);
    setGender(null);
    setMessages([INITIAL_MESSAGE]);
    setConfirmedSymptoms([]);
    setNextQuestion(null);
    setNextSymptom(null);
    setSessionId(null);
    setIsDone(false);
    setIsFinal(false);
    setInputValue('');
    if (onStartNew) onStartNew();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // ── Setup screen ────────────────────────────────────────────────────────
  if (phase === 'setup') {
    return <SetupScreen onStart={handleSetupComplete} />;
  }

  // ── Chat screen ─────────────────────────────────────────────────────────
  const placeholder = isDone
    ? 'Assessment complete'
    : isFinal
    ? 'Prediction is final'
    : sessionId === null
    ? "Describe your symptoms (e.g. 'fever, cough, headache')..."
    : 'Reply yes / no, or describe how you feel...';

  return (
    <div className="flex flex-col h-full bg-slate-50">

      {/* Patient badge */}
      <div className="flex items-center gap-2 px-4 py-2 bg-white border-b border-slate-100">
        <span className="text-xs text-slate-500">Patient:</span>
        <span className="text-xs font-semibold text-slate-700">Age {age}</span>
        <span className="text-xs text-slate-400">·</span>
        <span className="text-xs font-semibold text-slate-700 capitalize">{gender}</span>
        <button
          onClick={handleReset}
          className="ml-auto text-xs text-indigo-500 hover:text-indigo-700 font-medium transition-colors"
        >
          Change
        </button>
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`msg-row ${msg.role === 'user' ? 'user' : 'bot'}`}>
            <div className="chat-bubble">
              {msg.text}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="msg-row bot">
            <div className="chat-bubble loading">
              <Loader size={14} className="animate-spin text-indigo-400" />
              <span>Analyzing…</span>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-200 bg-white p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading || isDone || isFinal}
            className="flex-1 px-4 py-3 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed text-slate-900 placeholder-slate-400 text-sm"
          />
          {isDone || isFinal ? (
            <button
              onClick={handleReset}
              className="px-4 py-3 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-xl font-medium transition-colors flex items-center gap-2 text-sm"
            >
              <RefreshCw size={16} /> New
            </button>
          ) : (
            <button
              onClick={handleSendMessage}
              disabled={isLoading || !inputValue.trim()}
              className="px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
