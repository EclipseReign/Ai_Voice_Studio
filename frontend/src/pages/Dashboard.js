import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { PayPalScriptProvider, PayPalButtons } from '@paypal/react-paypal-js';

const Dashboard = () => {
  const { user, subscription, logout, refreshSubscription, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showPayPal, setShowPayPal] = useState(false);

  const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API}/history`, {
        withCredentials: true
      });
      setHistory(response.data);
    } catch (error) {
      console.error('Error fetching history:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleCancelSubscription = async () => {
    if (!window.confirm('Вы уверены, что хотите отменить Pro подписку?')) return;
    
    try {
      await axios.post(`${API}/subscription/cancel`, {}, {
        withCredentials: true
      });
      alert('Подписка отменена');
      await refreshSubscription();
    } catch (error) {
      alert('Ошибка отмены подписки');
    }
  };

  const createPayPalSubscription = async (data, actions) => {
    try {
      const response = await axios.post(
        `${API}/subscription/create`,
        { subscription_id: 'temp' },
        { withCredentials: true }
      );
      
      // Create PayPal subscription
      return actions.subscription.create({
        plan_id: 'P-XXXXXXXXXXXXXXXXXXXXXXXX', // Replace with your PayPal plan ID
      });
    } catch (error) {
      console.error('Error creating subscription:', error);
      throw error;
    }
  };

  const onPayPalApprove = async (data, actions) => {
    try {
      const response = await axios.post(
        `${API}/subscription/create`,
        { subscription_id: data.subscriptionID },
        { withCredentials: true }
      );
      alert('Подписка Pro активирована!');
      await refreshSubscription();
      setShowPayPal(false);
    } catch (error) {
      alert('Ошибка активации подписки');
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('ru-RU');
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <h1 className="text-2xl font-bold text-gray-900">🎙️ AI Voice Studio</h1>
              {isAdmin && (
                <span className="bg-purple-600 text-white px-3 py-1 rounded-full text-sm font-semibold">
                  ADMIN
                </span>
              )}
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/')}
                className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors"
              >
                🎤 Генерация
              </button>
              {isAdmin && (
                <button
                  onClick={() => navigate('/admin')}
                  className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors"
                >
                  ⚙️ Admin
                </button>
              )}
              <button
                onClick={handleLogout}
                className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
              >
                Выйти
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* User Info */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
          <div className="flex items-center space-x-4">
            {user?.picture && (
              <img src={user.picture} alt={user.name} className="w-16 h-16 rounded-full" />
            )}
            <div>
              <h2 className="text-2xl font-bold text-gray-900">{user?.name}</h2>
              <p className="text-gray-600">{user?.email}</p>
            </div>
          </div>
        </div>

        {/* Subscription Status */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">💳 Подписка</h3>
          
          {subscription?.plan === 'free' && (
            <div className="space-y-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-lg font-semibold text-gray-900">Free Plan</span>
                  <span className="bg-gray-200 text-gray-700 px-3 py-1 rounded-full text-sm font-semibold">
                    Бесплатно
                  </span>
                </div>
                <p className="text-gray-600">
                  Использовано сегодня: {subscription.usage_today || 0} / 3 генераций
                </p>
              </div>
              
              {!showPayPal ? (
                <button
                  onClick={() => setShowPayPal(true)}
                  className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-purple-700 hover:to-pink-700 transition-all"
                >
                  ⬆️ Перейти на Pro ($15/мес) - Безлимитно ✨
                </button>
              ) : (
                <div className="bg-gray-50 rounded-lg p-4">
                  <PayPalScriptProvider
                    options={{
                      "client-id": process.env.REACT_APP_PAYPAL_CLIENT_ID || "test",
                      vault: true,
                      intent: "subscription"
                    }}
                  >
                    <PayPalButtons
                      createSubscription={createPayPalSubscription}
                      onApprove={onPayPalApprove}
                      onError={(err) => {
                        console.error('PayPal Error:', err);
                        alert('Ошибка PayPal. Попробуйте позже.');
                      }}
                      style={{ layout: 'vertical' }}
                    />
                  </PayPalScriptProvider>
                  <button
                    onClick={() => setShowPayPal(false)}
                    className="mt-2 text-gray-600 hover:text-gray-900"
                  >
                    Отмена
                  </button>
                </div>
              )}
            </div>
          )}

          {subscription?.plan === 'pro' && (
            <div className="space-y-4">
              <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg p-4 border-2 border-purple-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-lg font-semibold text-purple-900">Pro Plan</span>
                  <span className="bg-purple-600 text-white px-3 py-1 rounded-full text-sm font-semibold">
                    ✨ Активна
                  </span>
                </div>
                <p className="text-purple-700">Безлимитные генерации</p>
                {subscription.expires_at && (
                  <p className="text-sm text-purple-600 mt-2">
                    Действует до: {formatDate(subscription.expires_at)}
                  </p>
                )}
              </div>
              
              <button
                onClick={handleCancelSubscription}
                className="w-full bg-red-100 text-red-700 py-2 px-6 rounded-lg font-semibold hover:bg-red-200 transition-colors"
              >
                Отменить подписку
              </button>
            </div>
          )}
        </div>

        {/* History */}
        <div className="bg-white rounded-2xl shadow-lg p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">📊 История генераций</h3>
          
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              У вас пока нет генераций
            </div>
          ) : (
            <div className="space-y-4">
              {history.map((item) => (
                <div key={item.id} className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="text-sm text-gray-500">
                          {formatDate(item.created_at)}
                        </span>
                        {item.audio_url && (
                          <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-semibold">
                            АУДИО
                          </span>
                        )}
                      </div>
                      <p className="text-gray-700 text-sm line-clamp-2 mb-2">{item.text}</p>
                      {item.voice && (
                        <p className="text-xs text-gray-500">
                          Голос: {item.voice} | Язык: {item.language}
                        </p>
                      )}
                    </div>
                    {item.audio_url && (
                      <a
                        href={`${API}${item.audio_url}`}
                        download
                        className="ml-4 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors flex-shrink-0"
                      >
                        ⬇️ Скачать
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
