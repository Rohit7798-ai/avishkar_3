import React from 'react';
import { useHealth } from '../../hooks/useHealth';
import { Badge } from '../ui/Badge';

export function Header({ onMenuClick }) {
  const { isHealthy, service, loading } = useHealth(true, 30000);

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between sticky top-0 z-20">
      <div className="flex items-center gap-3">
        {/* Mobile menu toggle */}
        <button
          type="button"
          onClick={onMenuClick}
          aria-label="Toggle navigation menu"
          className="md:hidden p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        {/* Mobile brand display */}
        <div className="flex items-center gap-2 md:hidden">
          <span className="text-xl">🌱</span>
          <span className="font-bold text-slate-900 text-sm">Farmer Decision</span>
        </div>
      </div>

      {/* Right controls: Help button & service indicator */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => {
            window.dispatchEvent(
              new CustomEvent('open-farm-copilot', { detail: { mode: 'help' } })
            );
          }}
          data-tour="ask-ai-help"
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-full transition-all duration-150 shadow-xs active:scale-95"
          aria-label="Ask AI / Help"
        >
          <span className="text-sm">🤖</span>
          <span>Ask AI / मदत</span>
        </button>

        {!loading && !isHealthy && (
          <Badge variant="warning" dot>
            Offline Mode
          </Badge>
        )}
      </div>
    </header>
  );
}
