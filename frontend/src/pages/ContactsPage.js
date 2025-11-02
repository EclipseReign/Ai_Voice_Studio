import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { ArrowLeft, Mail } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { ThemeSwitcher } from '@/components/ThemeSwitcher';

const ContactsPage = () => {
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
        <h1 className="text-3xl font-bold mb-8">{t('legal.contacts.title')}</h1>

        <div className="grid gap-6">
          <Card>
            <CardHeader>
              <CardTitle>{t('legal.contacts.organization')}</CardTitle>
              <CardDescription>{t('legal.contacts.organizationDesc')}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">EclipseReign</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t('legal.contacts.email')}</CardTitle>
              <CardDescription>{t('legal.contacts.emailDesc')}</CardDescription>
            </CardHeader>
            <CardContent>
              <a href="mailto:denisrvnk@gmai.com" className="flex items-center gap-2 text-lg text-primary hover:underline">
                <Mail className="h-5 w-5" />
                denisrvnk@gmai.com
              </a>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
};

export default ContactsPage;
