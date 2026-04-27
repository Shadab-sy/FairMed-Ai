import { useState, useCallback, useEffect } from 'react';
import './App.css';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import ResultsPanel from './components/ResultsPanel';

export default function App() {
  const [currentResults, setCurrentResults] = useState(null);
  const [currentSymptoms, setCurrentSymptoms] = useState([]);
  const [patientAge, setPatientAge] = useState(30);
  const [patientGender, setPatientGender] = useState('male');
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
    setPatientAge(30);
    setPatientGender('male');
    // Keep sidebar closed by default
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

  const handleChatResults = useCallback((results, symptoms, age, gender) => {
    setCurrentResults(results);
    setCurrentSymptoms(symptoms);
    setPatientAge(age);
    setPatientGender(gender);
  }, []);

  const toggleSidebar = useCallback(() => {
    setIsSidebarOpen((prev) => {
      console.log("Sidebar toggle:", !prev);
      return !prev;
    });
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Navigation Bar */}
      <Navbar onMenuClick={toggleSidebar} />

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - Toggleable */}
        <Sidebar
          history={history}
          onHistoryClick={handleHistoryClick}
          isSidebarOpen={isSidebarOpen}
          onClose={() => {
            if (window.innerWidth < 768) {
              setIsSidebarOpen(false);
            }
          }}
        />

        {/* Main Chat Area */}
        <main className="flex-1">
          {!currentResults ? (
            <ChatInterface onResults={handleChatResults} />
          ) : (
            <ResultsPanel
              predictions={currentResults}
              insights={null}
              symptoms={currentSymptoms}
              age={patientAge}
              gender={patientGender}
              onStartNew={handleStartNewCheck}
              onSaveToHistory={handleSaveToHistory}
            />
          )}
        </main>
      </div>
    </div>
  );
}
