import { useState, useCallback, useEffect } from 'react';
import './App.css';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import ResultsPanel from './components/ResultsPanel';

export default function App() {
  const [currentResults, setCurrentResults] = useState(null);
  const [currentSymptoms, setCurrentSymptoms] = useState([]);
  const [patientAge, setPatientAge] = useState(null);
  const [patientGender, setPatientGender] = useState(null);
  const [isAssessmentLive, setIsAssessmentLive] = useState(false);
  const [history, setHistory] = useState([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Auto-close sidebar on mobile when results appear
  useEffect(() => {
    if (window.innerWidth < 768 && currentResults) {
      setIsSidebarOpen(false);
    }
  }, [currentResults]);

  const handleStartNewCheck = useCallback(() => {
    setCurrentResults(null);
    setCurrentSymptoms([]);
    setPatientAge(null);
    setPatientGender(null);
    setIsAssessmentLive(false);
    setIsSidebarOpen(false);
  }, []);

  const handleSaveToHistory = useCallback(() => {
    if (currentResults && currentSymptoms.length > 0) {
      const newEntry = {
        id: Date.now(),
        query: currentSymptoms.join(', '),
        date: new Date().toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        }),
        results: currentResults,
        insights: null,
        symptoms: currentSymptoms,
        age: patientAge,
        gender: patientGender
      };
      setHistory([newEntry, ...history]);
    }
  }, [currentResults, currentSymptoms, patientAge, patientGender, history]);

  const handleHistoryClick = useCallback((entry) => {
    setCurrentResults(entry.results);
    setCurrentSymptoms(entry.symptoms);
    setPatientAge(entry.age);
    setPatientGender(entry.gender);
    // Close sidebar on mobile when selection made
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  }, []);

  const handleChatResults = useCallback((data, symptoms, age, gender) => {
    const formatted = (data.top_predictions || []).map(p => ({
      disease: p.disease,
      confidence: Math.round(p.confidence),
    }));
    setCurrentResults(formatted);
    setCurrentSymptoms(symptoms || []);
    setPatientAge(age);
    setPatientGender(gender);
    setIsAssessmentLive(!!data.next_question);
  }, []);

  const toggleSidebar = useCallback(() => {
    setIsSidebarOpen((prev) => {
      console.log("Sidebar toggle:", !prev);
      return !prev;
    });
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar onMenuClick={toggleSidebar} />

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <Sidebar
          history={history}
          onHistoryClick={handleHistoryClick}
          isSidebarOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
        />

        {/* Page body */}
        <div className="page-scroll">
          <div className={`app-body ${currentResults ? 'has-results' : 'no-results'}`}>

            {/* Chat column */}
            <div className="chat-col">
              <ChatInterface
                onResults={handleChatResults}
                onStartNew={handleStartNewCheck}
              />
            </div>

            {/* Results column — only rendered once we have predictions */}
            {currentResults && (
              <div className="results-col">
                <div className="results-sticky">
                  <ResultsPanel
                    predictions={currentResults}
                    insights={null}
                    symptoms={currentSymptoms}
                    age={patientAge}
                    gender={patientGender}
                    isLive={isAssessmentLive}
                    onStartNew={handleStartNewCheck}
                    onSaveToHistory={handleSaveToHistory}
                  />
                </div>
              </div>
            )}

          </div>
        </div>
      </div>
    </div>
  );
}
