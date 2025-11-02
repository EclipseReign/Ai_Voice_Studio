import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Mail } from 'lucide-react';

const Footer = () => {
  const { t } = useTranslation();
  const currentYear = new Date().getFullYear();

  return (
    <footer className="mt-auto border-t bg-background">
      <div className="container mx-auto px-4 py-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="font-semibold text-lg">EclipseReign</p>
            <p className="text-sm text-muted-foreground">© {currentYear} · {t('footer.allRightsReserved')}</p>
          </div>
          
          <nav className="flex flex-wrap gap-4 text-sm">
            <Link to="/terms" className="hover:underline text-muted-foreground hover:text-foreground">
              {t('footer.terms')}
            </Link>
            <Link to="/privacy" className="hover:underline text-muted-foreground hover:text-foreground">
              {t('footer.privacy')}
            </Link>
            <Link to="/cookies" className="hover:underline text-muted-foreground hover:text-foreground">
              {t('footer.cookies')}
            </Link>
            <Link to="/eula" className="hover:underline text-muted-foreground hover:text-foreground">
              {t('footer.license')}
            </Link>
            <Link to="/contacts" className="hover:underline text-muted-foreground hover:text-foreground">
              {t('footer.contacts')}
            </Link>
          </nav>
        </div>
        
        <div className="mt-4 text-sm text-muted-foreground flex items-center gap-2">
          <Mail className="h-4 w-4" />
          <span>{t('footer.contact')}:</span>
          <a href="mailto:denisrvnk@gmai.com" className="hover:underline text-primary">
            denisrvnk@gmai.com
          </a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
