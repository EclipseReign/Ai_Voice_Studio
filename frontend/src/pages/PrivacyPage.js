import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { ThemeSwitcher } from '@/components/ThemeSwitcher';

const PrivacyPage = () => {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              {t('legal.backToHome')}
            </Button>
          </Link>
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <ThemeSwitcher />
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <h1 className="text-3xl font-bold mb-8">{t('legal.privacy.title')}</h1>

        <div className="prose prose-slate dark:prose-invert max-w-none space-y-6">
          <section>
            <h2 className="text-2xl font-semibold mb-3">1. {t('legal.privacy.section1Title')}</h2>
            <p dangerouslySetInnerHTML={{ __html: t('legal.privacy.section1Content') }}></p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-3">2. {t('legal.privacy.section2Title')}</h2>
            <p dangerouslySetInnerHTML={{ __html: t('legal.privacy.section2Content') }}></p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-3">3. {t('legal.privacy.section3Title')}</h2>
            <p dangerouslySetInnerHTML={{ __html: t('legal.privacy.section3Content') }}></p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-3">4. {t('legal.privacy.section4Title')}</h2>
            <p dangerouslySetInnerHTML={{ __html: t('legal.privacy.section4Content') }}></p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-3">5. {t('legal.privacy.section5Title')}</h2>
            <p dangerouslySetInnerHTML={{ __html: t('legal.privacy.section5Content') }}></p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-3">6. {t('legal.privacy.section6Title')}</h2>
            <p dangerouslySetInnerHTML={{ __html: t('legal.privacy.section6Content') }}></p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-3">7. {t('legal.privacy.section7Title')}</h2>
            <p dangerouslySetInnerHTML={{ __html: t('legal.privacy.section7Content') }}></p>
          </section>
        </div>
      </main>
    </div>
  );
};

export default PrivacyPage;
