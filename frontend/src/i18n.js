"import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translations
import en from './locales/en.json';
import ru from './locales/ru.json';
import de from './locales/de.json';
import zh from './locales/zh.json';
import it from './locales/it.json';
import es from './locales/es.json';
import fr from './locales/fr.json';
import pt from './locales/pt.json';
import ja from './locales/ja.json';
import ko from './locales/ko.json';

const resources = {
  en: { translation: en },
  ru: { translation: ru },
  de: { translation: de },
  zh: { translation: zh },
  it: { translation: it },
  es: { translation: es },
  fr: { translation: fr },
  pt: { translation: pt },
  ja: { translation: ja },
  ko: { translation: ko },
};

i18n
  .use(LanguageDetector) // Auto-detect browser language
  .use(initReactI18next) // Pass i18n instance to react-i18next
  .init({
    resources,
    fallbackLng: 'en', // Fallback language if detection fails
    supportedLngs: ['en', 'ru', 'de', 'zh', 'it', 'es', 'fr', 'pt', 'ja', 'ko'],
    
    detection: {
      // Order of language detection
      order: ['localStorage', 'navigator', 'htmlTag'],
      // Cache user language
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },

    interpolation: {
      escapeValue: false, // React already escapes values
    },

    react: {
      useSuspense: false, // Disable suspense for now
    },
  });

export default i18n;
"