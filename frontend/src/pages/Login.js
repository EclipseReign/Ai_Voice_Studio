import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { LanguageSwitcher } from '../components/LanguageSwitcher';
import { ThemeSwitcher } from '../components/ThemeSwitcher';

const Login = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const handleGoogleLogin = async () => {
    try {
      const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
      const response = await fetch(`${API}/auth/google`);
      const data = await response.json();
      
      if (data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (error) {
      console.error('Error initiating Google login:', error);
      alert('Ошибка при входе через Google. Попробуйте еще раз.');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-slate-950 dark:to-slate-900 flex items-center justify-center p-4">
      {/* Language and Theme Switchers - Top Right */}
      <div className="absolute top-4 right-4 flex items-center gap-3">
        <LanguageSwitcher variant="compact" />
        <ThemeSwitcher variant="icon-only" showLabel={false} />
      </div>

      <div className="max-w-md w-full bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">{t('login.title')}</h1>
          <p className="text-gray-600 dark:text-gray-300">{t('login.subtitle')}</p>
        </div>

        <div className="space-y-4">
          <button
            onClick={handleGoogleLogin}
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-4 px-6 rounded-lg font-semibold text-lg hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
          >
            🚀 {t('login.withGoogle')}
          </button>

          <div className="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
            <p>{t('login.agreeToTerms')}</p>
          </div>
        </div>

        <div className="mt-8 pt-8 border-t border-gray-200 dark:border-gray-700">
          <div className="text-center space-y-2">
            <h3 className="font-semibold text-gray-900 dark:text-white">{t('dashboard.subscription')}:</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="bg-gray-50 dark:bg-slate-700 rounded-lg p-3">
                <div className="font-semibold text-gray-900 dark:text-white">{t('dashboard.free')}</div>
                <div className="text-gray-600 dark:text-gray-300">3 {t('nav.generation')}</div>
              </div>
              <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900 dark:to-pink-900 rounded-lg p-3 border-2 border-purple-200 dark:border-purple-700">
                <div className="font-semibold text-purple-900 dark:text-purple-200">{t('dashboard.pro')} - $19.99</div>
                <div className="text-purple-700 dark:text-purple-300">{t('dashboard.unlimited')} ✨</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
