import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { API } from '../App';
import axios from 'axios';
import { Check, X, Zap, Crown, Loader2 } from 'lucide-react';

const PricingPage = () => {
  const { t } = useTranslation();
  const { user, subscription, fetchSubscription } = useAuth();
  const navigate = useNavigate();
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState(false);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await axios.get(`${API}/subscription/config`);
      setConfig(response.data);
    } catch (error) {
      console.error('Error fetching config:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = async () => {
    if (!user) {
      navigate('/login');
      return;
    }

    setSubscribing(true);

    try {
      // Load PayPal SDK
      if (!window.paypal) {
        const script = document.createElement('script');
        script.src = `https://www.paypal.com/sdk/js?client-id=${config.paypal_client_id}&vault=true&intent=subscription`;
        script.async = true;
        document.body.appendChild(script);
        
        script.onload = () => {
          renderPayPalButton();
        };
      } else {
        renderPayPalButton();
      }
    } catch (error) {
      console.error('Error loading PayPal:', error);
      setSubscribing(false);
    }
  };

  const renderPayPalButton = () => {
    const container = document.getElementById('paypal-button-container');
    if (!container) return;

    window.paypal.Buttons({
      style: {
        shape: 'rect',
        color: 'gold',
        layout: 'vertical',
        label: 'subscribe'
      },
      createSubscription: function(data, actions) {
        return actions.subscription.create({
          plan_id: config.paypal_plan_id
        });
      },
      onApprove: async function(data) {
        try {
          // Send subscription ID to backend for verification
          const response = await axios.post(
            `${API}/subscription/paypal/approve?subscription_id=${data.subscriptionID}`,
            {},
            { withCredentials: true }
          );

          if (response.data.success) {
            // Refresh subscription status
            await fetchSubscription();
            alert('🎉 Добро пожаловать в Pro! Ваша подписка активирована.');
            navigate('/');
          }
        } catch (error) {
          console.error('Error approving subscription:', error);
          alert('Ошибка при активации подписки. Пожалуйста, свяжитесь с поддержкой.');
        } finally {
          setSubscribing(false);
        }
      },
      onError: function(err) {
        console.error('PayPal error:', err);
        alert('Ошибка PayPal. Пожалуйста, попробуйте снова.');
        setSubscribing(false);
      }
    }).render('#paypal-button-container');
  };

  const handleCancel = async () => {
    if (!window.confirm('Вы уверены, что хотите отменить подписку Pro?')) {
      return;
    }

    try {
      const response = await axios.post(
        `${API}/subscription/cancel`,
        {},
        { withCredentials: true }
      );

      if (response.data.success) {
        await fetchSubscription();
        alert(response.data.message);
      }
    } catch (error) {
      console.error('Error cancelling subscription:', error);
      alert('Ошибка при отмене подписки');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
      </div>
    );
  }

  const freeTier = config?.tiers?.free || {};
  const proTier = config?.tiers?.pro || {};
  const currentTier = subscription?.tier || 'free';

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Выберите свой тариф
          </h1>
          <p className="text-xl text-gray-600">
            Генерируйте тексты и озвучку с AI Voice Studio
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
          {/* Free Tier */}
          <div className={`bg-white rounded-2xl shadow-lg p-8 border-2 ${
            currentTier === 'free' ? 'border-purple-500' : 'border-gray-200'
          }`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Zap className="w-6 h-6 text-purple-600" />
                <h2 className="text-2xl font-bold text-gray-900">Free</h2>
              </div>
              {currentTier === 'free' && (
                <span className="bg-purple-100 text-purple-700 px-3 py-1 rounded-full text-sm font-semibold">
                  Текущий
                </span>
              )}
            </div>
            
            <div className="mb-6">
              <div className="flex items-baseline">
                <span className="text-4xl font-bold text-gray-900">$0</span>
                <span className="text-gray-500 ml-2">/месяц</span>
              </div>
            </div>

            <ul className="space-y-3 mb-8">
              {freeTier.features?.map((feature, index) => (
                <li key={index} className="flex items-start gap-2">
                  <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                  <span className="text-gray-700">{feature}</span>
                </li>
              ))}
              <li className="flex items-start gap-2">
                <X className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <span className="text-gray-500 line-through">Голоса высокого качества</span>
              </li>
            </ul>

            {currentTier === 'free' && subscription && (
              <div className="bg-purple-50 rounded-lg p-4 mb-4">
                <p className="text-sm text-gray-700">
                  <span className="font-semibold">{t('pricing.textUsage')}:</span> {subscription.text_usage_today}/{subscription.text_limit} {t('pricing.today')}
                </p>
                <p className="text-sm text-gray-700">
                  <span className="font-semibold">Озвучка:</span> {subscription.audio_usage_today}/{subscription.audio_limit} сегодня
                </p>
              </div>
            )}

            <button
              disabled
              className="w-full py-3 px-4 bg-gray-200 text-gray-500 rounded-lg font-semibold cursor-not-allowed"
            >
              Текущий тариф
            </button>
          </div>

          {/* Pro Tier */}
          <div className={`bg-gradient-to-br from-purple-600 to-indigo-600 rounded-2xl shadow-xl p-8 border-2 ${
            currentTier === 'pro' ? 'border-yellow-400' : 'border-transparent'
          } transform hover:scale-105 transition-transform duration-200`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Crown className="w-6 h-6 text-yellow-400" />
                <h2 className="text-2xl font-bold text-white">Pro</h2>
              </div>
              {currentTier === 'pro' && (
                <span className="bg-yellow-400 text-purple-900 px-3 py-1 rounded-full text-sm font-semibold">
                  Активен
                </span>
              )}
            </div>
            
            <div className="mb-6">
              <div className="flex items-baseline">
                <span className="text-4xl font-bold text-white">${proTier.price}</span>
                <span className="text-purple-200 ml-2">/месяц</span>
              </div>
            </div>

            <ul className="space-y-3 mb-8">
              {proTier.features?.map((feature, index) => (
                <li key={index} className="flex items-start gap-2">
                  <Check className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                  <span className="text-white">{feature}</span>
                </li>
              ))}
            </ul>

            {currentTier === 'pro' && subscription && subscription.expires_at && (
              <div className="bg-purple-700 bg-opacity-50 rounded-lg p-4 mb-4">
                <p className="text-sm text-purple-100">
                  Продлевается: {new Date(subscription.expires_at).toLocaleDateString('ru-RU')}
                </p>
              </div>
            )}

            {currentTier === 'pro' ? (
              <button
                onClick={handleCancel}
                className="w-full py-3 px-4 bg-white text-purple-600 rounded-lg font-semibold hover:bg-purple-50 transition-colors"
              >
                Отменить подписку
              </button>
            ) : (
              <>
                {!subscribing ? (
                  <button
                    onClick={handleSubscribe}
                    className="w-full py-3 px-4 bg-yellow-400 text-purple-900 rounded-lg font-semibold hover:bg-yellow-300 transition-colors"
                  >
                    Обновить до Pro
                  </button>
                ) : (
                  <div id="paypal-button-container" className="w-full"></div>
                )}
              </>
            )}
          </div>
        </div>

        {/* FAQ or Additional Info */}
        <div className="mt-12 text-center">
          <p className="text-gray-600">
            💳 Безопасная оплата через PayPal • 🔒 Отмена в любое время • 🌍 Доступно по всему миру
          </p>
          <p className="text-sm text-gray-500 mt-2">
            *Обратите внимание: PayPal может быть недоступен в некоторых регионах (например, Россия)
          </p>
        </div>

        {/* Back to Home */}
        <div className="mt-8 text-center">
          <button
            onClick={() => navigate('/')}
            className="text-purple-600 hover:text-purple-700 font-semibold"
          >
            ← Вернуться на главную
          </button>
        </div>
      </div>
    </div>
  );
};

export default PricingPage;
