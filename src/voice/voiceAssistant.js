/**
 * Multilingual Voice Assistant (SpeechSynthesis)
 * Member 5 - Offline Database + Sync + Voice + Testing Engineer
 * 
 * Zero external API dependencies (100% offline Web Speech API).
 * Provides clear audio guidance to field officers in English, Hindi, and Telugu.
 */

export const SUPPORTED_LANGUAGES = {
  ENGLISH: 'en',
  HINDI: 'hi',
  TELUGU: 'te'
};

export const PROMPT_KEYS = {
  ROTATE_PACKAGE: 'ROTATE_PACKAGE',
  IMAGE_UNCLEAR: 'IMAGE_UNCLEAR',
  MANUAL_VERIFY: 'MANUAL_VERIFY',
  INSPECTION_COMPLETE: 'INSPECTION_COMPLETE',
  COMPLIANT: 'COMPLIANT',
  NON_COMPLIANT: 'NON_COMPLIANT',
  OFFLINE_SAVED: 'OFFLINE_SAVED',
  SYNC_SUCCESS: 'SYNC_SUCCESS',
  DARK_IMAGE: 'DARK_IMAGE',
  PRICE_MISMATCH: 'PRICE_MISMATCH',
  MRP_CHANGED: 'MRP_CHANGED',
  FALLBACK_360: 'FALLBACK_360'
};

// Predefined Legal Metrology Audio Translations
export const VOICE_DICTIONARY = {
  [PROMPT_KEYS.ROTATE_PACKAGE]: {
    en: 'Rotate the package slowly.',
    hi: 'पैकेज को धीरे-धीरे घुमाएं।',
    te: 'ప్యాకేజీని నెమ్మదిగా తిప్పండి.'
  },
  [PROMPT_KEYS.IMAGE_UNCLEAR]: {
    en: 'Image is unclear. Please retake.',
    hi: 'छवि स्पष्ट नहीं है। कृपया पुनः फोटो लें।',
    te: 'చిత్రం స్పష్టంగా లేదు. దయచేసి మళ్లీ తీయండి.'
  },
  [PROMPT_KEYS.MANUAL_VERIFY]: {
    en: 'Manual verification required.',
    hi: 'मैन्युअल सत्यापन आवश्यक है।',
    te: 'మాన్యువల్ ధృవీకరణ అవసరం.'
  },
  [PROMPT_KEYS.INSPECTION_COMPLETE]: {
    en: 'Inspection completed.',
    hi: 'निरीक्षण पूरा हुआ।',
    te: 'తనిఖీ పూర్తయింది.'
  },
  [PROMPT_KEYS.COMPLIANT]: {
    en: 'Product is compliant with Legal Metrology rules.',
    hi: 'उत्पाद विधिक मापविज्ञान नियमों के अनुकूल है।',
    te: 'ఉత్పత్తి లీగల్ మెట్రాలజీ నిబంధనలకు అనుగుణంగా ఉంది.'
  },
  [PROMPT_KEYS.NON_COMPLIANT]: {
    en: 'Violation detected. Mandatory declaration is missing.',
    hi: 'उल्लंघन पाया गया। अनिवार्य घोषणा गायब है।',
    te: 'ఉల్లంఘన గుర్తించబడింది. తప్పనిసరి సమాచారం లేదు.'
  },
  [PROMPT_KEYS.OFFLINE_SAVED]: {
    en: 'Inspection saved offline. Will sync automatically.',
    hi: 'निरीक्षण ऑफ़लाइन सहेजा गया। बाद में सिंक होगा।',
    te: 'తనిఖీ ఆఫ్‌లైన్‌లో భద్రపరచబడింది. ఆటోమేటిక్‌గా సింక్ అవుతుంది.'
  },
  [PROMPT_KEYS.SYNC_SUCCESS]: {
    en: 'All offline inspections synced successfully.',
    hi: 'सभी ऑफ़लाइन निरीक्षण सफलतापूर्वक सिंक हो गए हैं।',
    te: 'అన్ని ఆఫ్‌లైన్ తనిఖీలు విజయవంతంగా సింక్ చేయబడ్డాయి.'
  },
  [PROMPT_KEYS.DARK_IMAGE]: {
    en: 'Lighting is too dark. Please use flashlight or move to light.',
    hi: 'रोशनी बहुत कम है। कृपया टॉर्च चालू करें।',
    te: 'వెలుతురు చాలా తక్కువగా ఉంది. దయచేసి లైట్ వేయండి.'
  },
  [PROMPT_KEYS.PRICE_MISMATCH]: {
    en: 'Price mismatch detected between packaging and online listing.',
    hi: 'पैकेजिंग और ऑनलाइन मूल्य में बेमेल पाया गया।',
    te: 'ప్యాకేజింగ్ మరియు ఆన్‌లైన్ ధర మధ్య వ్యత్యాసం ఉంది.'
  },
  [PROMPT_KEYS.MRP_CHANGED]: {
    en: 'Price or quantity change detected from previous inspection.',
    hi: 'पिछली जांच की तुलना में कीमत या मात्रा में बदलाव पाया गया।',
    te: 'మునుపటి తనిఖీతో పోలిస్తే ధర లేదా పరిమాణంలో మార్పు గుర్తించబడింది.'
  },
  [PROMPT_KEYS.FALLBACK_360]: {
    en: 'Switching to pre-recorded 360-degree demo scan.',
    hi: 'बैकअप 360 डिग्री डेमो वीडियो शुरू किया जा रहा है।',
    te: 'ముందుగా రికార్డ్ చేసిన 360 డిగ్రీల డెమో వీడియోకి మారుతోంది.'
  }
};

// BCP 47 Language Tag Mapping
const LOCALE_TAGS = {
  en: 'en-IN',
  hi: 'hi-IN',
  te: 'te-IN'
};

class VoiceAssistant {
  constructor() {
    this.currentLanguage = SUPPORTED_LANGUAGES.ENGLISH;
    this.isMuted = false;
    this.voicesLoaded = false;
    this.cachedVoices = [];

    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      this.initVoices();
    }
  }

  /**
   * Load and cache system voices
   */
  initVoices() {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;

    const load = () => {
      this.cachedVoices = window.speechSynthesis.getVoices();
      this.voicesLoaded = this.cachedVoices.length > 0;
    };

    load();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = load;
    }
  }

  /**
   * Set current active language ('en' | 'hi' | 'te')
   * @param {string} lang 
   */
  setLanguage(lang) {
    if (Object.values(SUPPORTED_LANGUAGES).includes(lang)) {
      this.currentLanguage = lang;
      console.log(`[VoiceAssistant] Language set to: ${lang}`);
    } else {
      console.warn(`[VoiceAssistant] Unsupported language "${lang}", defaulting to "en"`);
      this.currentLanguage = SUPPORTED_LANGUAGES.ENGLISH;
    }
  }

  /**
   * Get best matching voice for the selected language
   * @param {string} lang 
   * @returns {SpeechSynthesisVoice|null}
   */
  getBestVoice(lang) {
    if (!this.cachedVoices.length && typeof window !== 'undefined' && window.speechSynthesis) {
      this.cachedVoices = window.speechSynthesis.getVoices();
    }

    const targetLocale = LOCALE_TAGS[lang] || 'en-IN';
    
    // 1. Exact match (e.g. 'te-IN', 'hi-IN', 'en-IN')
    let matched = this.cachedVoices.find(v => v.lang === targetLocale || v.lang.replace('_', '-') === targetLocale);
    
    // 2. Prefix match (e.g. 'te', 'hi', 'en')
    if (!matched) {
      matched = this.cachedVoices.find(v => v.lang.startsWith(lang));
    }

    // 3. Fallback default voice
    if (!matched && this.cachedVoices.length) {
      matched = this.cachedVoices[0];
    }

    return matched;
  }

  /**
   * Speak a predefined prompt key or raw text
   * @param {string} promptKeyOrText - E.g. PROMPT_KEYS.ROTATE_PACKAGE or custom text
   * @param {string} [language] - Optional override ('en' | 'hi' | 'te')
   * @param {Object} [options] - Optional rate, pitch, volume
   * @returns {Promise<boolean>}
   */
  speak(promptKeyOrText, language = null, options = {}) {
    return new Promise((resolve) => {
      if (this.isMuted) {
        console.log('[VoiceAssistant] Speech muted, skipping.');
        return resolve(false);
      }

      if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
        console.warn('[VoiceAssistant] SpeechSynthesis API not supported in this environment.');
        return resolve(false);
      }

      const lang = language || this.currentLanguage;
      
      // Lookup text from predefined dictionary if key exists, otherwise use raw text
      let textToSpeak = promptKeyOrText;
      if (VOICE_DICTIONARY[promptKeyOrText]) {
        textToSpeak = VOICE_DICTIONARY[promptKeyOrText][lang] || VOICE_DICTIONARY[promptKeyOrText].en;
      }

      // Cancel any ongoing speech to avoid backlog lag
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(textToSpeak);
      utterance.lang = LOCALE_TAGS[lang] || 'en-IN';
      utterance.rate = options.rate || 0.95; // Slightly slower for crisp clarity
      utterance.pitch = options.pitch || 1.0;
      utterance.volume = options.volume !== undefined ? options.volume : 1.0;

      const voice = this.getBestVoice(lang);
      if (voice) {
        utterance.voice = voice;
      }

      utterance.onend = () => {
        resolve(true);
      };

      utterance.onerror = (e) => {
        console.warn('[VoiceAssistant] SpeechSynthesis error:', e.error);
        resolve(false);
      };

      console.log(`[VoiceAssistant] Speaking (${lang}): "${textToSpeak}"`);
      window.speechSynthesis.speak(utterance);
    });
  }

  /**
   * Stop any playing speech immediately
   */
  stop() {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }

  /**
   * Toggle mute state
   */
  toggleMute() {
    this.isMuted = !this.isMuted;
    if (this.isMuted) this.stop();
    return this.isMuted;
  }
}

// Export singleton instance and convenience helper
export const voiceAssistant = new VoiceAssistant();

/**
 * Universal helper function requested in prompt: speak(text, language)
 * @param {string} textOrKey 
 * @param {string} language 'en' | 'hi' | 'te'
 * @returns {Promise<boolean>}
 */
export function speak(textOrKey, language = 'en') {
  return voiceAssistant.speak(textOrKey, language);
}
