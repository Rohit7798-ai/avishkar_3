/**
 * Voice output (Text-to-Speech) service for Kisan AI Copilot.
 * Cleans markdown and emojis to provide smooth natural speech in regional languages.
 */

class VoiceService {
  constructor() {
    this.synth = typeof window !== 'undefined' ? window.speechSynthesis : null;
    this.currentUtterance = null;
    this.enabled = true; // default enabled
  }

  isSupported() {
    return Boolean(this.synth);
  }

  setEnabled(val) {
    this.enabled = Boolean(val);
    if (!this.enabled) {
      this.stop();
    }
  }

  isEnabled() {
    return this.enabled;
  }

  /**
   * Cleans markdown syntax and icons before speaking
   */
  cleanTextForSpeech(text) {
    if (!text) return '';
    return text
      // remove markdown bold/italic
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      // remove markdown headers
      .replace(/^#+\s+/gm, '')
      // remove bullet points
      .replace(/^[•\-*]\s+/gm, '')
      // remove emojis
      .replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '')
      // normalize multiple spaces / newlines
      .replace(/\n+/g, '. ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  /**
   * Speak response aloud in target language
   */
  speak(text, lang = 'en') {
    if (!this.synth || !this.enabled) return;

    this.stop();

    const clean = this.cleanTextForSpeech(text);
    if (!clean) return;

    try {
      const utterance = new SpeechSynthesisUtterance(clean);
      const langMap = {
        mr: 'mr-IN',
        hi: 'hi-IN',
        en: 'en-IN',
      };
      utterance.lang = langMap[lang] || 'en-IN';
      utterance.rate = 0.95; // Slightly slower for clear regional comprehension
      utterance.pitch = 1.0;

      // Try selecting an appropriate installed voice
      const voices = this.synth.getVoices();
      if (voices && voices.length > 0) {
        const targetCode = (langMap[lang] || 'en-IN').toLowerCase();
        const matched = voices.find(
          (v) =>
            v.lang.toLowerCase() === targetCode ||
            v.lang.toLowerCase().startsWith(lang)
        );
        if (matched) {
          utterance.voice = matched;
        }
      }

      this.currentUtterance = utterance;
      this.synth.speak(utterance);
    } catch (err) {
      console.warn('Speech synthesis error:', err);
    }
  }

  stop() {
    if (this.synth) {
      try {
        this.synth.cancel();
      } catch (e) {
        // ignore
      }
    }
    this.currentUtterance = null;
  }
}

export const voiceService = new VoiceService();
export default voiceService;
