import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { chatService } from '../../services/chatService';
import { cropService } from '../../services/cropService';
import { voiceService } from '../../services/voiceService';
import { useTutorial } from '../../context/TutorialContext';

const CONTEXT_PROMPTS = {
  '/': {
    en: [
      { label: '🌾 My Crops', query: 'Show my crops' },
      { label: '🌧️ Today Weather', query: "Show today's weather" },
      { label: '💰 Mandi Rates', query: 'Open the marketplace' },
      { label: '🧪 Fertilizer Advice', query: 'Show fertilizer recommendations' },
      { label: '❓ How to use app?', query: 'How do I use this app?' },
    ],
    mr: [
      { label: '🌾 माझे पीक', query: 'माझे पीक दाखवा' },
      { label: '🌧️ आजचे हवामान', query: 'आजचे हवामान दाखवा' },
      { label: '💰 बाजारभाव', query: 'बाजारभाव काय आहेत?' },
      { label: '🧪 खत सल्ला', query: 'खत व्यवस्थापन सांगा' },
      { label: '❓ ॲप कसे वापरावे?', query: 'मला ॲप कसे वापरावे ते शिकवा' },
    ],
    hi: [
      { label: '🌾 मेरी फसलें', query: 'मेरी फसलें दिखाएं' },
      { label: '🌧️ आज का मौसम', query: 'आज का मौसम दिखाएं' },
      { label: '💰 मंडी भाव', query: 'मंडी भाव क्या हैं?' },
      { label: '🧪 खाद सलाह', query: 'उर्वरक सलाह दें' },
      { label: '❓ ऐप कैसे चलाएं?', query: 'ऐप का उपयोग कैसे करें?' },
    ],
  },
  '/crops': {
    en: [
      { label: '🌱 Check Health', query: 'Check my crop health' },
      { label: '➕ Add New Crop', query: 'Add my new crop' },
      { label: '📸 Take Photo', query: "Take today's crop photo" },
      { label: '💧 When to irrigate?', query: 'When should I irrigate?' },
      { label: '📜 Crop History', query: 'Show my crop history' },
    ],
    mr: [
      { label: '🌱 पिकाचे आरोग्य', query: 'पिकाचे आरोग्य तपासा' },
      { label: '➕ नवीन पीक जोडा', query: 'नवीन पीक जोडा' },
      { label: '📸 फोटो काढा', query: 'आजचा पीक फोटो काढा' },
      { label: '💧 पाणी कधी द्यावे?', query: 'पाणी कधी द्यावे?' },
      { label: '📜 मागील इतिहास', query: 'माझा पीक इतिहास दाखवा' },
    ],
    hi: [
      { label: '🌱 फसल स्वास्थ्य', query: 'फसल का स्वास्थ्य जांचें' },
      { label: '➕ नई फसल जोड़ें', query: 'नई फसल जोड़ें' },
      { label: '📸 तस्वीर लें', query: 'आज की फसल की तस्वीर लें' },
      { label: '💧 सिंचाई कब करें?', query: 'सिंचाई कब करनी चाहिए?' },
      { label: '📜 पुराना इतिहास', query: 'फसल का इतिहास दिखाएं' },
    ],
  },
  '/farms': {
    en: [
      { label: '📍 Detect Location', query: 'Help me detect my location' },
      { label: '➕ Add Farm', query: 'How do I add a farm?' },
      { label: '⚡ Sync Weather', query: 'Sync weather for my farm' },
    ],
    mr: [
      { label: '📍 स्थान शोधा', query: 'माझे लोकेशन कसे शोधायचे?' },
      { label: '➕ नवीन शेत', query: 'नवीन शेत कसे जोडायचे?' },
      { label: '⚡ हवामान सिंक', query: 'हवामान सिंक करा' },
    ],
    hi: [
      { label: '📍 लोकेशन खोजें', query: 'लोकेशन कैसे पता करें?' },
      { label: '➕ नया खेत', query: 'नया खेत कैसे जोड़ें?' },
      { label: '⚡ मौसम सिंक', query: 'मौसम सिंक करें' },
    ],
  },
  '/market': {
    en: [
      { label: '💰 Sell or Hold?', query: 'Should I sell or hold?' },
      { label: '📈 Price Prediction', query: 'What is the future price prediction?' },
      { label: '🧪 Fertilizer Prices', query: 'Show current fertilizer prices' },
    ],
    mr: [
      { label: '💰 विकावे की थांबावे?', query: 'बाजारात कांदा विकावा की थांबावे?' },
      { label: '📈 पुढील भाव अंदाज', query: 'पुढील आठवड्यात भाव वाढतील का?' },
      { label: '🧪 खताचे भाव', query: 'खताचे सध्याचे भाव काय आहेत?' },
    ],
    hi: [
      { label: '💰 बेचें या रुकें?', query: 'मंडी में बेचें या इंतजार करें?' },
      { label: '📈 भविष्य का भाव', query: 'आगे भाव बढ़ने की क्या संभावना है?' },
      { label: '🧪 खाद के भाव', query: 'खाद के वर्तमान भाव क्या हैं?' },
    ],
  },
  '/weather': {
    en: [
      { label: '🌧️ Rain Risk', query: 'Is there any rain risk?' },
      { label: '☀️ Curing Safety', query: 'Is it safe to cure onions in the field?' },
      { label: '💧 Irrigation Check', query: 'When should I irrigate?' },
    ],
    mr: [
      { label: '🌧️ पावसाचा धोका', query: 'पुढील काही दिवसांत पाऊस पडेल का?' },
      { label: '☀️ कांदा वाळवणे', query: 'कांदा शेतात सुकवणे सुरक्षित आहे का?' },
      { label: '💧 पाणी नियोजन', query: 'पाणी कधी द्यावे?' },
    ],
    hi: [
      { label: '🌧️ बारिश का खतरा', query: 'क्या बारिश होने की संभावना है?' },
      { label: '☀️ सुखाने की सुरक्षा', query: 'क्या खेत में फसल सुखाना सुरक्षित है?' },
      { label: '💧 सिंचाई सलाह', query: 'सिंचाई कब करनी चाहिए?' },
    ],
  },
};

const GREETINGS = {
  en: 'Namaste! I am your Kisan AI Copilot. I can operate the app for you, check crop health, guide you step by step, or speak in regional languages.',
  mr: 'नमस्कार! मी तुमचा किसान AI सहाय्यक आहे. मी तुमच्यासाठी ॲप चालवू शकतो, पिकाचे आरोग्य तपासू शकतो, किंवा तुम्हाला एक-एक पायरीने शिकवू शकतो.',
  hi: 'नमस्ते! मैं आपका किसान AI सहायक हूँ। मैं आपके लिए ऐप संचालित कर सकता हूँ, फसल स्वास्थ्य जांच सकता हूँ, और चरण-दर-चरण मार्गदर्शन कर सकता हूँ।',
};

export function FarmCopilotDrawer() {
  const [isOpen, setIsOpen] = useState(false);
  const [language, setLanguage] = useState(() => {
    return localStorage.getItem('kisan_copilot_lang') || 'mr'; // default Marathi for farmers
  });
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [crops, setCrops] = useState([]);
  const [selectedCropId, setSelectedCropId] = useState('');
  const [workflowState, setWorkflowState] = useState(null);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: GREETINGS[language] || GREETINGS.mr,
      timestamp: new Date().toISOString(),
      suggested_actions: [],
    },
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const recognitionRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();
  const { startTutorial } = useTutorial();

  // Save language preference
  const handleLanguageChange = (newLang) => {
    setLanguage(newLang);
    localStorage.setItem('kisan_copilot_lang', newLang);
  };

  // Load available crops for context
  useEffect(() => {
    async function loadCrops() {
      try {
        const cropList = await cropService.getCrops();
        if (Array.isArray(cropList) && cropList.length > 0) {
          setCrops(cropList);
          setSelectedCropId((prev) => prev || String(cropList[0].id));
        }
      } catch (err) {
        console.warn('Could not load crops for Copilot context:', err);
      }
    }
    loadCrops();
  }, []);

  // Update greeting when language changes if no interaction yet
  useEffect(() => {
    setMessages((prev) => {
      if (prev.length <= 1) {
        return [
          {
            role: 'assistant',
            content: GREETINGS[language] || GREETINGS.en,
            timestamp: new Date().toISOString(),
            suggested_actions: [],
          },
        ];
      }
      return prev;
    });
  }, [language]);

  // Listen to Global "Ask AI / Help" event from Header
  useEffect(() => {
    const handleGlobalOpen = (e) => {
      setIsOpen(true);
      if (e.detail?.mode === 'help') {
        const helpQuery =
          language === 'mr'
            ? 'हे पान काय आहे आणि मला मदत करा'
            : language === 'hi'
            ? 'यह पेज क्या है और मुझे क्या करना चाहिए?'
            : 'What is this screen and what should I do now?';
        setTimeout(() => handleSendMessage(helpQuery), 200);
      }
    };
    window.addEventListener('open-farm-copilot', handleGlobalOpen);
    return () => window.removeEventListener('open-farm-copilot', handleGlobalOpen);
  }, [language, location.pathname]);

  // Setup Browser Speech Recognition
  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      setSpeechSupported(true);
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInputMessage((prev) => (prev ? `${prev} ${transcript}` : transcript));
        setIsListening(false);
      };

      recognition.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen, loading]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  const toggleSpeechRecognition = () => {
    if (!recognitionRef.current) return;

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      try {
        const langMap = { en: 'en-IN', mr: 'mr-IN', hi: 'hi-IN' };
        recognitionRef.current.lang = langMap[language] || 'mr-IN';
        recognitionRef.current.start();
        setIsListening(true);
      } catch (err) {
        console.warn('Failed to start speech recognition:', err);
        setIsListening(false);
      }
    }
  };

  const handleSendMessage = async (textToSend) => {
    const query = (textToSend || inputMessage).trim();
    if (!query || loading) return;

    setInputMessage('');

    // Append user message
    const userMsg = {
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const historyPayload = messages
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }));

      const res = await chatService.sendMessage({
        message: query,
        crop_id: selectedCropId ? Number(selectedCropId) : null,
        language,
        current_path: location.pathname,
        workflow_state: workflowState,
        history: historyPayload,
      });

      // Update active target crop if returned
      if (res.crop_id && !selectedCropId) {
        setSelectedCropId(String(res.crop_id));
      }

      // Check if tutorial triggered
      if (res.action_type === 'tutorial' && res.tutorial_steps) {
        startTutorial({
          topic: res.intent,
          steps: res.tutorial_steps,
        });
      }

      // Check if navigation triggered
      if (res.action_type === 'navigate' && res.action_payload?.path) {
        const dest = res.action_payload.path;
        if (dest === 'BACK') {
          navigate(-1);
        } else {
          navigate(dest);
        }
      }

      // Check if modal triggered
      if (res.action_type === 'modal' && res.action_payload?.modal) {
        window.dispatchEvent(
          new CustomEvent('open-crop-modal', {
            detail: {
              modal: res.action_payload.modal,
              crop_id: res.action_payload.crop_id || selectedCropId,
            },
          })
        );
      }

      // Store workflow state if pending
      if (res.confirmation_needed) {
        setWorkflowState({
          active_intent: res.intent,
          pending_crop: res.confirmation_data,
        });
      } else if (res.action_type === 'confirm_action') {
        // Execute confirmed action (e.g. creating crop)
        if (res.action_payload?.action === 'create_crop' && res.action_payload?.data) {
          try {
            await cropService.createCrop(res.action_payload.data);
            const updatedCrops = await cropService.getCrops();
            setCrops(updatedCrops);
          } catch (createErr) {
            console.warn('Failed to auto-create crop from bot:', createErr);
          }
        }
        setWorkflowState(null);
      }

      const assistantMsg = {
        role: 'assistant',
        content: res.reply,
        timestamp: res.timestamp || new Date().toISOString(),
        suggested_actions: res.suggested_actions || [],
        confirmation_needed: res.confirmation_needed,
        confirmation_data: res.confirmation_data,
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // Speak response aloud if voice enabled
      if (voiceEnabled) {
        voiceService.speak(res.reply, language);
      }
    } catch (err) {
      const errorMsg = {
        role: 'assistant',
        content:
          language === 'mr'
            ? '⚠️ सर्व्हरशी संपर्क होऊ शकला नाही. कृपया थोड्या वेळाने प्रयत्न करा.'
            : language === 'hi'
            ? '⚠️ सर्वर से संपर्क नहीं हो सका। कृपया कुछ समय बाद पुनः प्रयास करें।'
            : '⚠️ Could not connect to the advisory server. Please ensure the backend is running.',
        timestamp: new Date().toISOString(),
        suggested_actions: [],
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleActionClick = (action) => {
    if (action.action_type === 'navigate') {
      const targetPath =
        typeof action.payload === 'object' && action.payload !== null
          ? action.payload.path || '/'
          : action.payload;
      if (targetPath === 'BACK') {
        navigate(-1);
      } else {
        navigate(targetPath);
      }
      if (window.innerWidth < 640) {
        setIsOpen(false);
      }
    } else if (action.action_type === 'modal') {
      const modalType = action.payload?.modal;
      window.dispatchEvent(
        new CustomEvent('open-crop-modal', {
          detail: {
            modal: modalType,
            crop_id: action.payload?.crop_id || selectedCropId,
          },
        })
      );
      if (window.innerWidth < 640) {
        setIsOpen(false);
      }
    } else if (action.action_type === 'tutorial') {
      if (action.payload?.steps) {
        startTutorial({
          topic: action.payload.topic || 'tutorial',
          steps: action.payload.steps,
        });
      }
    } else if (action.action_type === 'prompt' || action.action_type === 'query') {
      const promptText =
        typeof action.payload === 'object' && action.payload?.prompt
          ? action.payload.prompt
          : action.payload;
      handleSendMessage(promptText);
    }
  };

  // Get current contextual prompts
  const activePromptSet =
    CONTEXT_PROMPTS[location.pathname]?.[language] ||
    CONTEXT_PROMPTS['/']?.[language] ||
    CONTEXT_PROMPTS['/'].mr;

  return (
    <>
      {/* Floating Launcher Button */}
      {!isOpen && (
        <div className="fixed bottom-6 right-6 z-40 flex items-center gap-2 group">
          <div className="hidden md:flex items-center bg-white px-3.5 py-1.5 rounded-full shadow-lg border border-emerald-100 text-xs text-slate-800 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse mr-2"></span>
            {language === 'mr'
              ? '🌾 बोला किंवा विचारा'
              : language === 'hi'
              ? '🌾 बोलें या पूछें'
              : '🌾 Ask Kisan Copilot'}
          </div>
          <button
            type="button"
            onClick={() => setIsOpen(true)}
            className="flex items-center justify-center w-14 h-14 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white shadow-xl shadow-emerald-700/25 transition-all duration-200 transform hover:scale-105 focus:outline-none focus:ring-4 focus:ring-emerald-300"
            aria-label="Open Kisan AI Copilot"
          >
            <span className="text-2xl">🌱</span>
          </button>
        </div>
      )}

      {/* Floating Chat Window / Modal Drawer */}
      {isOpen && (
        <div
          role="dialog"
          aria-label="Kisan AI Copilot Assistant"
          className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 w-[calc(100vw-2rem)] sm:w-[440px] h-[600px] max-h-[85vh] bg-white rounded-2xl shadow-2xl border border-slate-200/90 flex flex-col z-50 overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-200"
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-emerald-600 to-teal-700 p-3.5 text-white flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-full bg-white/15 backdrop-blur-sm flex items-center justify-center text-lg border border-white/20">
                🌾
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <h3 className="font-semibold text-sm tracking-tight">Kisan AI Assistant</h3>
                  <span className="text-[10px] bg-emerald-500/80 px-1.5 py-0.5 rounded-full font-medium text-white border border-white/20">
                    Voice & Tutor
                  </span>
                </div>
                <p className="text-[11px] text-emerald-100 font-normal">
                  {language === 'mr'
                    ? 'काढणी • हवामान • बाजारपेठ • मार्गदर्शन'
                    : language === 'hi'
                    ? 'कटाई • मौसम • मंडी • मार्गदर्शन'
                    : 'Harvest • Weather • Market • Guide'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Voice Output Toggle Button */}
              <button
                type="button"
                onClick={() => {
                  const nextState = !voiceEnabled;
                  setVoiceEnabled(nextState);
                  voiceService.setEnabled(nextState);
                }}
                className={`p-1.5 rounded-lg text-xs transition-colors ${
                  voiceEnabled
                    ? 'bg-white/20 text-white font-bold'
                    : 'bg-black/20 text-white/60'
                }`}
                title={voiceEnabled ? 'Voice narration on (आवाज चालू)' : 'Voice narration off (आवाज बंद)'}
                aria-label="Toggle voice responses"
              >
                {voiceEnabled ? '🔊' : '🔇'}
              </button>

              {/* Language Selector */}
              <div className="flex bg-black/20 rounded-lg p-0.5 text-[11px]">
                {['mr', 'hi', 'en'].map((lang) => (
                  <button
                    key={lang}
                    type="button"
                    onClick={() => handleLanguageChange(lang)}
                    className={`px-1.5 py-0.5 rounded font-medium transition-colors ${
                      language === lang
                        ? 'bg-white text-emerald-800 shadow-sm font-semibold'
                        : 'text-emerald-100 hover:text-white'
                    }`}
                  >
                    {lang === 'en' ? 'EN' : lang === 'mr' ? 'मराठी' : 'हिंदी'}
                  </button>
                ))}
              </div>

              {/* Close Button */}
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="w-7 h-7 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center text-white text-sm transition-colors"
                aria-label="Close chat"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Active Crop Context Bar */}
          <div className="bg-emerald-50/70 border-b border-emerald-100 px-3 py-1.5 flex items-center justify-between text-xs text-slate-700">
            <span className="font-medium text-[11px] text-emerald-900 flex items-center gap-1">
              🌱 {language === 'mr' ? 'लक्ष्य पीक:' : language === 'hi' ? 'लक्षित फसल:' : 'Target Crop:'}
            </span>
            <select
              value={selectedCropId}
              onChange={(e) => setSelectedCropId(e.target.value)}
              className="text-xs bg-white border border-emerald-200 rounded px-2 py-0.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-emerald-500 max-w-[220px] truncate"
            >
              <option value="">{language === 'mr' ? 'सर्व पिके' : language === 'hi' ? 'सभी फसलें' : 'All Crops'}</option>
              {crops.map((crop) => (
                <option key={crop.id} value={crop.id}>
                  {crop.crop_name} {crop.variety ? `(${crop.variety})` : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Messages Stream */}
          <div className="flex-1 overflow-y-auto p-3.5 space-y-3 bg-slate-50/50">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex flex-col ${
                  msg.role === 'user' ? 'items-end' : 'items-start'
                }`}
              >
                <div
                  className={`max-w-[88%] rounded-2xl px-3.5 py-2.5 text-xs sm:text-[13px] leading-relaxed shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-emerald-600 text-white rounded-br-none'
                      : 'bg-white text-slate-800 border border-slate-200/80 rounded-bl-none'
                  }`}
                >
                  <p className="whitespace-pre-line">{msg.content}</p>

                  {/* Interactive Confirmation Box */}
                  {msg.confirmation_needed && (
                    <div className="mt-3 p-2.5 bg-emerald-50/90 border border-emerald-300 rounded-xl space-y-2">
                      <p className="text-[11px] font-semibold text-emerald-950">
                        {language === 'mr'
                          ? 'ही माहिती सेव्ह करू का?'
                          : language === 'hi'
                          ? 'क्या आप इसे सुरक्षित करना चाहते हैं?'
                          : 'Save and proceed?'}
                      </p>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            handleSendMessage(
                              language === 'mr'
                                ? 'होय, सेव्ह करा'
                                : language === 'hi'
                                ? 'हाँ, सुरक्षित करें'
                                : 'Yes, save it'
                            )
                          }
                          className="flex-1 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs rounded-lg transition-colors shadow-xs"
                        >
                          {language === 'mr'
                            ? '✅ होय, सेव्ह करा'
                            : language === 'hi'
                            ? '✅ हाँ, सुरक्षित करें'
                            : '✅ Yes, Save'}
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            handleSendMessage(
                              language === 'mr'
                                ? 'रद्द करा'
                                : language === 'hi'
                                ? 'रद्द करें'
                                : 'Cancel'
                            )
                          }
                          className="flex-1 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 font-medium text-xs rounded-lg transition-colors"
                        >
                          {language === 'mr' ? '❌ रद्द करा' : language === 'hi' ? '❌ रद्द करें' : '❌ Cancel'}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Interactive Action Buttons */}
                  {msg.suggested_actions && msg.suggested_actions.length > 0 && (
                    <div className="mt-2.5 pt-2 border-t border-slate-100 flex flex-wrap gap-1.5">
                      {msg.suggested_actions.map((act, actIdx) => (
                        <button
                          key={actIdx}
                          type="button"
                          onClick={() => handleActionClick(act)}
                          className="inline-flex items-center gap-1 text-[11px] font-medium bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200/80 rounded-lg px-2.5 py-1 transition-colors"
                        >
                          {act.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <span className="text-[10px] text-slate-400 mt-1 px-1">
                  {new Date(msg.timestamp).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
            ))}

            {/* Typing Loader */}
            {loading && (
              <div className="flex items-center gap-1 text-slate-400 text-xs px-2.5 py-1.5 bg-white border border-slate-200 rounded-xl w-fit">
                <span className="animate-spin text-sm">🌱</span>
                <span>{language === 'mr' ? 'माहिती शोधत आहे...' : language === 'hi' ? 'जानकारी खोजी जा रही है...' : 'Thinking...'}</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Context-Aware Quick Prompt Pills */}
          <div className="px-3 py-1.5 bg-white border-t border-slate-100 overflow-x-auto whitespace-nowrap flex gap-1.5 scrollbar-thin">
            {activePromptSet.map((item, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSendMessage(item.query)}
                disabled={loading}
                className="text-[11px] bg-slate-100 hover:bg-emerald-50 hover:text-emerald-700 text-slate-600 border border-slate-200 rounded-full px-2.5 py-1 transition-colors flex-shrink-0"
              >
                {item.label}
              </button>
            ))}
          </div>

          {/* Input Bar */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="p-2.5 bg-white border-t border-slate-200 flex items-center gap-1.5"
          >
            {/* Voice Input Button */}
            {speechSupported && (
              <button
                type="button"
                onClick={toggleSpeechRecognition}
                className={`p-2 rounded-xl border transition-all ${
                  isListening
                    ? 'bg-rose-500 text-white border-rose-600 animate-pulse'
                    : 'bg-slate-50 text-slate-500 hover:text-emerald-600 border-slate-200'
                }`}
                title={isListening ? 'Listening... बोलणे चालू आहे' : 'Voice Input (आवाजात बोला)'}
                aria-label="Toggle voice input"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                  />
                </svg>
              </button>
            )}

            <input
              ref={inputRef}
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder={
                language === 'mr'
                  ? 'येथे बोला किंवा प्रश्न विचारा...'
                  : language === 'hi'
                  ? 'यहाँ बोलें या प्रश्न पूछें...'
                  : 'Ask harvest, crops, weather, or tutorial...'
              }
              className="flex-1 text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white"
            />

            <button
              type="submit"
              disabled={!inputMessage.trim() || loading}
              className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 text-white rounded-xl p-2 transition-colors flex items-center justify-center"
              aria-label="Send message"
            >
              <svg
                className="w-4 h-4 transform rotate-90"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
              </svg>
            </button>
          </form>
        </div>
      )}
    </>
  );
}

export default FarmCopilotDrawer;
