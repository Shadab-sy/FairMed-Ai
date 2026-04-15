import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Landing from './components/Landing';
import Dashboard from './components/Dashboard';
import HistoryPanel from './components/HistoryPanel';

function App() {
  const [view, setView] = useState('landing');
  const [query, setQuery] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  
  // Dummy history data
  const [history, setHistory] = useState([
    { id: 1, query: 'Persistent headache and blurred vision', date: 'Today, 2:30 PM' },
    { id: 2, query: 'Skin rash after taking pain medication', date: 'Yesterday, 9:15 AM' }
  ]);

  const handleSearch = (searchQuery) => {
    setIsProcessing(true);
    // Simulate AI processing delay for UX
    setTimeout(() => {
      setQuery(searchQuery);
      setIsProcessing(false);
      setView('dashboard');
      
      // Add current search to history if not exists
      const exists = history.find(item => item.query.toLowerCase() === searchQuery.toLowerCase());
      if (!exists) {
        setHistory(prev => [
          { id: Date.now(), query: searchQuery, date: 'Just now' },
          ...prev
        ]);
      }
    }, 1500);
  };

  const handleBack = () => {
    setView('landing');
    setQuery('');
  };

  const toggleSidebar = () => {
    setIsSidebarOpen(prev => !prev);
  };

  const handleSelectHistory = (selectedQuery) => {
    setQuery(selectedQuery);
    setView('dashboard');
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false); // Auto close sidebar on mobile
    }
  };

  const handleNewSearch = () => {
    setView('landing');
    setQuery('');
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  };

  return (
    <div className="app-container relative flex overflow-x-hidden">
      <HistoryPanel 
        isOpen={isSidebarOpen} 
        onClose={() => setIsSidebarOpen(false)}
        history={history}
        onSelectHistory={handleSelectHistory}
        onNewSearch={handleNewSearch}
      />
      
      {/* Spacer when sidebar is open on desktop */}
      <div 
        className={`hidden md:block transition-all duration-300 ${isSidebarOpen ? 'w-72 shrink-0' : 'w-0 shrink-0'}`} 
      />

      <div className="flex-1 flex flex-col min-h-screen transition-all duration-300 w-full relative">
        <Navbar onToggleSidebar={toggleSidebar} />
        
        <main className="flex-1 w-full flex flex-col">
          {view === 'landing' ? (
            <Landing onSearch={handleSearch} isProcessing={isProcessing} />
          ) : (
            <Dashboard query={query} onBack={handleBack} />
          )}
        </main>
      </div>

      {/* Background Decorative Blur Ellipses */}
      <div className="fixed top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 blur-[120px] rounded-full pointer-events-none -z-10" />
      <div className="fixed bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-emerald-500/10 blur-[120px] rounded-full pointer-events-none -z-10" />
    </div>
  );
}

export default App;
