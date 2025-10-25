import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';

const AdminDashboard = () => {
  const { user, isAdmin, logout, refreshSubscription } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [grantEmail, setGrantEmail] = useState('');
  const [grantDuration, setGrantDuration] = useState(1);
  const [revokeEmail, setRevokeEmail] = useState('');

  const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

  useEffect(() => {
    if (!isAdmin) {
      navigate('/dashboard');
      return;
    }
    fetchData();
  }, [isAdmin, navigate]);

  const fetchData = async () => {
    try {
      const [statsRes, usersRes] = await Promise.all([
        axios.get(`${API}/admin/stats`, { withCredentials: true }),
        axios.get(`${API}/admin/users`, { withCredentials: true })
      ]);
      setStats(statsRes.data);
      setUsers(usersRes.data.users);
    } catch (error) {
      console.error('Error fetching admin data:', error);
      alert('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const handleGrantPro = async (e) => {
    e.preventDefault();
    if (!grantEmail) {
      alert('Введите email пользователя');
      return;
    }

    try {
      await axios.post(
        `${API}/admin/grant-pro`,
        { user_email: grantEmail, duration_months: grantDuration },
        { withCredentials: true }
      );
      alert(`Pro подписка предоставлена пользователю ${grantEmail}`);
      setGrantEmail('');
      setGrantDuration(1);
      fetchData();
      // Refresh subscription if admin granted Pro to themselves
      if (user?.email === grantEmail) {
        await refreshSubscription();
      }
    } catch (error) {
      alert(error.response?.data?.detail || 'Ошибка предоставления Pro');
    }
  };

  const handleRevokePro = async (e) => {
    e.preventDefault();
    if (!revokeEmail) {
      alert('Введите email пользователя');
      return;
    }

    if (!window.confirm(`Отозвать Pro подписку у ${revokeEmail}?`)) return;

    try {
      await axios.post(
        `${API}/admin/revoke-pro`,
        { user_email: revokeEmail },
        { withCredentials: true }
      );
      alert(`Pro подписка отозвана у ${revokeEmail}`);
      setRevokeEmail('');
      fetchData();
      // Refresh subscription if admin revoked Pro from themselves
      if (user?.email === revokeEmail) {
        await refreshSubscription();
      }
    } catch (error) {
      alert(error.response?.data?.detail || 'Ошибка отзыва Pro');
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('ru-RU');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-100">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <h1 className="text-2xl font-bold text-gray-900">⚙️ Admin Dashboard</h1>
              <span className="bg-purple-600 text-white px-3 py-1 rounded-full text-sm font-semibold">
                {user?.email}
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/')}
                className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors"
              >
                🎤 Генерация
              </button>
              <button
                onClick={() => navigate('/dashboard')}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                📊 Dashboard
              </button>
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
        {/* Statistics */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="text-3xl font-bold text-indigo-600 mb-2">{stats.total_users}</div>
              <div className="text-gray-600">Всего пользователей</div>
            </div>
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="text-3xl font-bold text-green-600 mb-2">{stats.verified_users}</div>
              <div className="text-gray-600">Подтверждённые</div>
            </div>
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="text-3xl font-bold text-purple-600 mb-2">{stats.pro_users}</div>
              <div className="text-gray-600">Pro пользователи</div>
            </div>
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="text-3xl font-bold text-blue-600 mb-2">{stats.total_generations}</div>
              <div className="text-gray-600">Всего генераций</div>
            </div>
          </div>
        )}

        {/* Grant/Revoke Pro */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Grant Pro */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4">✨ Предоставить Pro</h3>
            <form onSubmit={handleGrantPro} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email пользователя
                </label>
                <input
                  type="email"
                  value={grantEmail}
                  onChange={(e) => setGrantEmail(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="user@example.com"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Продолжительность (месяцы)
                </label>
                <input
                  type="number"
                  value={grantDuration}
                  onChange={(e) => setGrantDuration(parseInt(e.target.value))}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  min="1"
                  max="12"
                  required
                />
              </div>
              <button
                type="submit"
                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-purple-700 hover:to-pink-700 transition-all"
              >
                Предоставить Pro
              </button>
            </form>
          </div>

          {/* Revoke Pro */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4">❌ Отозвать Pro</h3>
            <form onSubmit={handleRevokePro} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email пользователя
                </label>
                <input
                  type="email"
                  value={revokeEmail}
                  onChange={(e) => setRevokeEmail(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  placeholder="user@example.com"
                  required
                />
              </div>
              <button
                type="submit"
                className="w-full bg-red-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-red-700 transition-all mt-12"
              >
                Отозвать Pro
              </button>
            </form>
          </div>
        </div>

        {/* Users Table */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">👥 Все пользователи</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Пользователь
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Подписка
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Статус
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Регистрация
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        {user.picture && (
                          <img src={user.picture} alt={user.name} className="h-8 w-8 rounded-full mr-3" />
                        )}
                        <div>
                          <div className="text-sm font-medium text-gray-900">{user.name}</div>
                          <div className="text-sm text-gray-500">{user.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        user.tier === 'pro'
                          ? 'bg-purple-100 text-purple-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {user.tier === 'pro' ? '✨ Pro' : 'Free'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-2">
                        {user.email_verified && (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                            ✅ Email
                          </span>
                        )}
                        {user.is_admin && (
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-purple-100 text-purple-800">
                            🛡️ Admin
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(user.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
