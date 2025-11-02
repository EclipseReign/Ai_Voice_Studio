import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { ThemeSwitcher } from '@/components/ThemeSwitcher';

const CookiesPage = () => {
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
        <h1 className="text-3xl font-bold mb-8">{t('legal.cookies.title')}</h1>

        <div className="prose prose-slate dark:prose-invert max-w-none space-y-6">
          <section>
            <p dangerouslySetInnerHTML={{ __html: t('legal.cookies.intro') }}></p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-3">{t('legal.cookies.categoriesTitle')}</h2>
            
            <div className="space-y-4">
              <div className="border rounded-lg p-4">
                <h3 className="font-semibold text-lg mb-2">{t('legal.cookies.essential')}</h3>
                <p dangerouslySetInnerHTML={{ __html: t('legal.cookies.essentialContent') }}></p>
              </div>

              <div className="border rounded-lg p-4">
                <h3 className="font-semibold text-lg mb-2">{t('legal.cookies.analytics')}</h3>
                <p dangerouslySetInnerHTML={{ __html: t('legal.cookies.analyticsContent') }}></p>
              </div>

              <div className="border rounded-lg p-4">
                <h3 className="font-semibold text-lg mb-2">{t('legal.cookies.marketing')}</h3>
                <p dangerouslySetInnerHTML={{ __html: t('legal.cookies.marketingContent') }}></p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-3">{t('legal.cookies.managementTitle')}</h2>
            <p dangerouslySetInnerHTML={{ __html: t('legal.cookies.managementContent') }}></p>
          </section>
        </div>
      </main>
    </div>
  );
};

export default CookiesPage;
