import { useState, useEffect, useRef } from 'react';
import { Send, Loader } from 'lucide-react';

const INITIAL_MESSAGE = {
  role: 'assistant',
  text: "Hi! I'm here to help you figure out what might be going on. Let's start with your main symptoms. What are you experiencing?"
};

export default function ChatInterface({ onResults }) {
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [confirmedSymptoms, setConfirmedSymptoms] = useState([]);
  const [age, setAge] = useState(30);
  const [gender, setGender] = useState('male');
  const [askedSymptoms, setAskedSymptoms] = useState(new Set());
  const [nextQuestion, setNextQuestion] = useState(null);
  const [nextSymptom, setNextSymptom] = useState(null);
  const [predictions, setPredictions] = useState(null);
  const chatEndRef = useRef(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const callPredictAPI = async (symptoms, message = null) => {
    try {
      const payload = {
        age,
        gender,
        asked_symptoms: Array.from(askedSymptoms)
      };
      
      if (message) {
        payload.message = message;
      } else {
        payload.symptoms = symptoms;
      }

      const res = await fetch('http://localhost:8000/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        const error = new Error(errorData.detail || 'Prediction failed');
        error.status = res.status;
        error.detail = errorData.detail;
        throw error;
      }

      return await res.json();
    } catch (err) {
      console.error('API error:', err);
      throw err;
    }
  };

  const callFollowupAPI = async (symptoms, newAnswer, message = null) => {
    try {
      const payload = {
        new_answer: newAnswer,
        age,
        gender
      };

      if (message) {
        payload.message = message;
      } else {
        payload.symptoms = symptoms;
      }

      const res = await fetch('http://localhost:8000/followup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        const error = new Error(errorData.detail || 'Followup failed');
        error.status = res.status;
        error.detail = errorData.detail;
        throw error;
      }

      return await res.json();
    } catch (err) {
      console.error('API error:', err);
      throw err;
    }
  };

  const normalizeSymptom = (symptom) => {
    return symptom.toLowerCase().trim().replace(/\s+/g, '_').replace(/-/g, '_');
  };

  const parseInitialSymptoms = (text) => {
    return text
      .toLowerCase()
      .replace(/[,/]+/g, ' ')
      .replace(/\b(and|with|also|plus|alongside|having)\b/g, ' ')
      .split(/\s+/)
      .map((part) => part.trim())
      .filter(Boolean)
      .map((part) => normalizeSymptom(part))
      .filter((part, index, all) => all.indexOf(part) === index);
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setIsLoading(true);

    // Add user message to chat
    setMessages((prev) => [...prev, { role: 'user', text: userMessage }]);

    try {
      // First turn - user provides initial symptoms
      if (confirmedSymptoms.length === 0) {
        const parsedSymptoms = parseInitialSymptoms(userMessage);
        if (parsedSymptoms.length === 0) {
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              text: 'I didn\'t quite catch that. Could you tell me your main symptoms? For example: fever, cough, headache, etc.'
            }
          ]);
          setIsLoading(false);
          return;
        }

        let data;
        try {
          // Try with parsed symptoms first
          data = await callPredictAPI(parsedSymptoms);
        } catch (err) {
          // If 422 error (symptoms not recognized), retry with message format
          if (err.status === 422) {
            setMessages((prev) => [
              ...prev,
              {
                role: 'assistant',
                text: 'I had trouble understanding those symptoms. Please describe them in more detail, like "I have a fever and cough" or "feeling tired with a headache".'
              }
            ]);
            setIsLoading(false);
            return;
          }
          throw err;
        }

        setConfirmedSymptoms(parsedSymptoms);
        const newAskedSymptoms = new Set(parsedSymptoms);
        setAskedSymptoms(newAskedSymptoms);
        setPredictions(data);

        if (data.next_question) {
          setNextQuestion(data.next_question);
          setNextSymptom(data.next_symptom);
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', text: data.next_question }
          ]);
        } else {
          // No more questions
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              text: 'Based on your symptoms, here are the possible conditions.'
            }
          ]);
          if (data.top_predictions && onResults) {
            onResults(data, parsedSymptoms, age, gender);
          }
        }
      } else {
        // Follow-up turns - user answers yes/no or provides more info
        const isYes = /^(yes|yeah|yep|y|true|1)$/i.test(userMessage);
        const isNo = /^(no|nope|n|false|0)$/i.test(userMessage);

        if (!isYes && !isNo) {
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              text: 'Please answer with "yes" or "no" to help me narrow down the diagnosis.'
            }
          ]);
          setIsLoading(false);
          return;
        }

        // Process the answer
        const updatedAskedSymptoms = new Set([...askedSymptoms, nextSymptom]);
        setAskedSymptoms(updatedAskedSymptoms);

        let updatedSymptoms = [...confirmedSymptoms];
        if (isYes) {
          updatedSymptoms.push(nextSymptom);
          setConfirmedSymptoms(updatedSymptoms);
        }

        // Call followup API
        const newAnswer = { [nextSymptom]: isYes ? 1 : 0 };
        const data = await callFollowupAPI(confirmedSymptoms, newAnswer);
        setPredictions(data);

        if (data.next_question && data.next_symptom) {
          setNextQuestion(data.next_question);
          setNextSymptom(data.next_symptom);
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', text: data.next_question }
          ]);
        } else {
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              text: 'Based on everything you\'ve shared, here are the most likely conditions.'
            }
          ]);
          if (data.top_predictions && onResults) {
            onResults(data, updatedSymptoms, age, gender);
          }
        }
      }
    } catch (err) {
      console.error('Error:', err);
      
      // Handle 422 errors specifically
      if (err.status === 422) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            text: 'I couldn\'t recognize those symptoms. Please describe them like:\n• "I have a fever and cough"\n• "I\'m experiencing fatigue and headache"\n• "feeling tired, dizzy, and nauseous"'
          }
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            text: 'Sorry, I encountered an error. Please try again.'
          }
        ]);
      }
    } finally {
      setIsLoading(false);
      scrollToBottom();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs lg:max-w-md xl:max-w-lg px-4 py-3 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-none'
                  : 'bg-white text-slate-900 border border-slate-200 rounded-bl-none'
              }`}
            >
              <p className="text-sm leading-relaxed">{msg.text}</p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white text-slate-900 border border-slate-200 rounded-lg rounded-bl-none px-4 py-3 flex items-center gap-2">
              <Loader size={16} className="animate-spin text-indigo-600" />
              <span className="text-sm text-slate-600">Thinking...</span>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-slate-200 bg-white p-6">
        <div className="flex gap-3">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              confirmedSymptoms.length === 0
                ? "Tell me your symptoms (e.g., 'fever, cough, headache')..."
                : "Answer with 'yes' or 'no'..."
            }
            disabled={isLoading}
            className="flex-1 px-4 py-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:bg-slate-100 disabled:cursor-not-allowed text-slate-900 placeholder-slate-500"
          />
          <button
            onClick={handleSendMessage}
            disabled={isLoading || !inputValue.trim()}
            className="px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
