import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const TutorialContext = createContext(null);

export function TutorialProvider({ children }) {
  const [activeTutorial, setActiveTutorial] = useState(null);
  const [stepIndex, setStepIndex] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();

  const currentStep =
    activeTutorial && activeTutorial.steps && activeTutorial.steps[stepIndex]
      ? activeTutorial.steps[stepIndex]
      : null;

  const startTutorial = (tutorial) => {
    if (!tutorial || !tutorial.steps || tutorial.steps.length === 0) return;
    setActiveTutorial(tutorial);
    setStepIndex(0);
  };

  const exitTutorial = () => {
    // Clean up previous highlights
    document.querySelectorAll('.tour-highlight').forEach((el) => {
      el.classList.remove('tour-highlight', 'ring-4', 'ring-emerald-500', 'ring-offset-2', 'animate-pulse');
    });
    setActiveTutorial(null);
    setStepIndex(0);
  };

  const nextStep = () => {
    if (!activeTutorial) return;
    if (stepIndex < activeTutorial.steps.length - 1) {
      setStepIndex((prev) => prev + 1);
    } else {
      exitTutorial();
    }
  };

  const prevStep = () => {
    if (stepIndex > 0) {
      setStepIndex((prev) => prev - 1);
    }
  };

  // Synchronize target route and element highlight
  useEffect(() => {
    if (!currentStep) return;

    // Navigate to step's path if not already there
    if (currentStep.path && location.pathname !== currentStep.path) {
      navigate(currentStep.path);
    }

    // Remove previous highlights
    document.querySelectorAll('.tour-highlight').forEach((el) => {
      el.classList.remove('tour-highlight', 'ring-4', 'ring-emerald-500', 'ring-offset-2', 'animate-pulse');
    });

    // Find and highlight target element
    const timer = setTimeout(() => {
      if (currentStep.target) {
        const targetEl = document.querySelector(currentStep.target);
        if (targetEl) {
          targetEl.classList.add('tour-highlight', 'ring-4', 'ring-emerald-500', 'ring-offset-2', 'animate-pulse');
          targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [currentStep, location.pathname, navigate]);

  return (
    <TutorialContext.Provider
      value={{
        activeTutorial,
        currentStep,
        stepIndex,
        totalSteps: activeTutorial?.steps?.length || 0,
        startTutorial,
        exitTutorial,
        nextStep,
        prevStep,
      }}
    >
      {children}

      {/* Floating Tutorial Guidance Overlay Card */}
      {activeTutorial && currentStep && (
        <aside
          role="region"
          aria-label="App Step-by-Step Tutorial Guide"
          className="fixed top-20 left-1/2 -translate-x-1/2 z-50 max-w-md w-[calc(100vw-2rem)] bg-slate-900/95 text-white backdrop-blur-md px-4 py-3.5 rounded-2xl shadow-2xl border border-emerald-500/40 animate-in fade-in slide-in-from-top-4 duration-300"
        >
          <div className="flex items-center justify-between gap-2 pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></span>
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                {currentStep.title || `Step ${stepIndex + 1}`}
              </span>
              <span className="text-[11px] text-slate-400">
                ({stepIndex + 1} of {activeTutorial.steps.length})
              </span>
            </div>
            <button
              type="button"
              onClick={exitTutorial}
              className="text-xs text-slate-400 hover:text-white px-2 py-0.5 rounded hover:bg-slate-800 transition-colors"
            >
              Exit / बंद करा ✕
            </button>
          </div>

          <p className="text-xs sm:text-sm text-slate-100 font-medium py-2.5 leading-relaxed">
            {currentStep.instruction}
          </p>

          <div className="flex items-center justify-between pt-1 text-xs">
            <button
              type="button"
              onClick={prevStep}
              disabled={stepIndex === 0}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 transition-colors"
            >
              ← Back / मागे
            </button>
            <div className="flex gap-1.5">
              {activeTutorial.steps.map((_, idx) => (
                <span
                  key={idx}
                  className={`w-2 h-2 rounded-full transition-all ${
                    idx === stepIndex ? 'bg-emerald-400 scale-125' : 'bg-slate-700'
                  }`}
                />
              ))}
            </div>
            <button
              type="button"
              onClick={nextStep}
              className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium shadow-md transition-colors"
            >
              {stepIndex < activeTutorial.steps.length - 1
                ? 'Next / पुढे →'
                : 'Finish / समाप्त ✔'}
            </button>
          </div>
        </aside>
      )}
    </TutorialContext.Provider>
  );
}

export function useTutorial() {
  const context = useContext(TutorialContext);
  if (!context) {
    throw new Error('useTutorial must be used within a TutorialProvider');
  }
  return context;
}

export default TutorialContext;
