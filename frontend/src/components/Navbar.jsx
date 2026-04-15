import React from 'react';
import { Activity, Menu } from 'lucide-react';

const Navbar = ({ onToggleSidebar }) => {
  return (
    <nav className="w-full py-4 px-6 md:px-8 flex items-center justify-between glass-panel sticky top-0 z-50 rounded-none border-t-0 border-x-0 border-slate-200/50 shadow-sm bg-white/70 backdrop-blur-xl">
      <div className="flex items-center gap-4">
        <button 
          onClick={onToggleSidebar}
          className="p-2 hover:bg-slate-100 rounded-lg text-slate-600 transition-colors"
        >
          <Menu size={24} />
        </button>
        <div className="flex items-center gap-2 cursor-pointer transition-transform hover:scale-105 active:scale-95 duration-200">
          <div className="bg-primary/10 p-2 rounded-xl text-primary flex-shrink-0">
            <Activity size={24} />
          </div>
          <span className="font-bold text-xl tracking-tight text-slate-800">
            FairMed <span className="text-primary font-black">AI</span>
          </span>
        </div>
      </div>
      
      <div className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600">
        <a href="#" className="hover:text-primary transition-colors duration-200">Home</a>
        <a href="#" className="hover:text-primary transition-colors duration-200">About</a>
        <a href="#" className="hover:text-primary transition-colors duration-200">How it Works</a>
        <button className="bg-primary hover:bg-primary-hover text-white px-5 py-2 rounded-full shadow-md shadow-primary/30 transition-all duration-300 hover:shadow-lg hover:shadow-primary/40 active:scale-95 font-semibold">
          Get Started
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
