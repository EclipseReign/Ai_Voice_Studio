import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';

const CookieBanner = () => {
  const { t } = useTranslation();
  const [isVisible, setIsVisible] = useState(false);
  const CONSENT_KEY = 'cookieConsent.v1';

  useEffect(() => {
    // Check if consent was already given
    const saved = localStorage.getItem(CONSENT_KEY);
    if (!saved) {
      setIsVisible(true);
    } else {
      // If user accepted analytics, enable it
      try {
        const parsed = JSON.parse(saved);
        if (parsed && parsed.analytics) {
          enableNonEssential();
        }
      } catch (e) {
        console.error('Error parsing cookie consent:', e);
      }
    }
  }, []);

  const enableNonEssential = () => {
    // Here you can add analytics code like Google Analytics
    // Example:
    // if (window.gtag) {
    //   window.gtag('consent', 'update', {
    //     analytics_storage: 'granted'
    //   });
    // }
  };

  const handleAcceptAll = () => {
    localStorage.setItem(
      CONSENT_KEY,
      JSON.stringify({
        necessary: true,
        analytics: true,
        marketing: true,
        ts: Date.now(),
      })
    );
    enableNonEssential();
    setIsVisible(false);
  };

  const handleNecessaryOnly = () => {
    localStorage.setItem(
      CONSENT_KEY,
      JSON.stringify({
        necessary: true,
        analytics: false,
        marketing: false,
        ts: Date.now(),
      })
    );
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-50 bg-slate-900 text-white p-4 shadow-lg border-t border-slate-700"
      role="dialog"
      aria-live="polite"
      aria-label={t('cookies.bannerTitle')}
    >
      <div className="container mx-auto max-w-6xl">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex-1">
            <p className="text-sm leading-relaxed">
              {t('cookies.bannerText')}{' '}
              <Link to="/cookies" className="underline text-blue-300 hover:text-blue-200">
                {t('cookies.learnMore')}
              </Link>
            </p>
          </div>
          
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={handleAcceptAll}
              className="bg-green-600 hover:bg-green-700 text-white"
              size="sm"
            >
              {t('cookies.acceptAll')}
            </Button>
            <Button
              onClick={handleNecessaryOnly}
              variant="outline"
              className="bg-slate-800 hover:bg-slate-700 border-slate-600 text-white"
              size="sm"
            >
              {t('cookies.necessaryOnly')}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CookieBanner;
