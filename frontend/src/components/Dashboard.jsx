import SymptomChecker from './SymptomChecker';
import ResultsPanel from './ResultsPanel';

export default function Dashboard({
  initialQuery,
  onResults,
  results,
  insights,
  symptoms,
  age,
  gender,
  onStartNew,
  onSaveToHistory
}) {
  return (
    <main className="flex-1 px-4 py-12 max-w-7xl mx-auto w-full">
      {!results ? (
        <SymptomChecker initialQuery={initialQuery} onResults={onResults} />
      ) : (
        <ResultsPanel
          predictions={results}
          insights={insights}
          symptoms={symptoms}
          age={age}
          gender={gender}
          onStartNew={onStartNew}
          onSaveToHistory={onSaveToHistory}
        />
      )}
    </main>
  );
}
