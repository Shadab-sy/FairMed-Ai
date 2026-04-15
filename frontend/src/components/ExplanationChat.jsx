import React, { useState, useEffect } from 'react';
import { Bot, User } from 'lucide-react';

const ExplanationChat = ({ query, explanation }) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(true);

  useEffect(() => {
    let i = 0;
    setDisplayedText('');
    setIsTyping(true);
    
    // Slight initial delay for typing realism
    const initialDelay = setTimeout(() => {
      const typingInterval = setInterval(() => {
        if (i < explanation.length) {
          setDisplayedText((prev) => prev + explanation.charAt(i));
          i++;
        } else {
          clearInterval(typingInterval);
          setIsTyping(false);
        }
      }, 15); // typing speed
      
      return () => clearInterval(typingInterval);
    }, 500);
    
    return () => clearTimeout(initialDelay);
  }, [explanation]);

  return (
    <div className="glass-panel p-6 animate-fade-in flex flex-col h-full" style={{ animationDelay: '0.2s' }}>
      <div className="flex items-center gap-2 mb-6 pb-4 border-b border-slate-100">
        <Bot size={20} className="text-primary" />
        <h3 className="font-semibold text-slate-800">AI Explanation</h3>
      </div>
      
      <div className="flex-1 overflow-y-auto pr-2 space-y-6">
        {/* User Query Bubble */}
        <div className="flex gap-4 p-4 bg-slate-50/80 rounded-2xl rounded-tr-sm ml-8 border border-slate-100">
          <div className="flex-1">
            <p className="text-sm text-slate-700 leading-relaxed">"{query}"</p>
          </div>
          <div className="shrink-0 bg-slate-200 w-8 h-8 rounded-full flex items-center justify-center text-slate-500">
            <User size={16} />
          </div>
        </div>

        {/* AI Response Bubble */}
        <div className="flex gap-4 p-4 bg-primary/5 rounded-2xl rounded-tl-sm mr-8 border border-primary/10 relative">
          <div className="shrink-0 bg-primary shadow-glow w-8 h-8 rounded-full flex items-center justify-center text-white">
            <Bot size={16} />
          </div>
          <div className="flex-1">
            <p className="text-sm text-slate-800 leading-relaxed font-medium">
              {displayedText}
              {isTyping && (
                <span className="inline-block w-1.5 h-4 ml-1 bg-primary align-middle animate-pulse"></span>
              )}
            </p>
          </div>
        </div>
      </div>
      
      <div className="mt-4 pt-4 border-t border-slate-100 text-xs text-center text-slate-400 font-medium">
        This is an AI summary and not a medical diagnosis. Always consult a healthcare professional.
      </div>
    </div>
  );
};

export default ExplanationChat;
