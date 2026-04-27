import { Menu } from 'lucide-react';

export default function Navbar({ onMenuClick }) {
  return (
    <nav className="sticky top-0 z-40 bg-white shadow-soft border-b border-slate-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="h-16 flex items-center justify-between">
          {/* Left: Hamburger Menu */}
          <button
            onClick={onMenuClick}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors duration-150"
            aria-label="Toggle sidebar"
          >
            <Menu size={24} className="text-slate-700" />
          </button>

          {/* Center: Logo */}
          <div className="flex items-center gap-2">
            <span className="text-2xl">🩺</span>
            <span className="text-xl font-bold text-indigo-600">FairMed AI</span>
          </div>

          {/* Right: Badge */}
          <div className="px-3 py-1 bg-slate-100 text-xs text-slate-600 rounded-full font-medium">
            Powered by AI
          </div>
        </div>
      </div>
    </nav>
  );
}
