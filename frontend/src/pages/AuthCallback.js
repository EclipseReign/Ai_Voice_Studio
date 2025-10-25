import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';

const AuthCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { checkExistingSession } = useAuth();
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get authorization code from URL query params
        const code = searchParams.get('code');
        
        if (!code) {
          setError('Не получен код авторизации от Google');
          setLoading(false);
          return;
        }

        // Send code to backend for processing
        const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
        const response = await axios.get(`${API}/auth/google/callback`, {
          params: { code },
          withCredentials: true
        });
        
        console.log('Auth callback response:', response.data);
        
        // Wait a bit for cookie to be set
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Check session after successful authentication
        await checkExistingSession();
        
        // Redirect to dashboard on success
        navigate('/dashboard');
        
      } catch (err) {
        console.error('Auth callback error:', err);
        const errorDetail = err.response?.data?.detail || 'Ошибка аутентификации';
        console.error('Error detail:', errorDetail);
        setError(errorDetail);
        setLoading(false);
      }
    };

    handleCallback();
  }, [searchParams, navigate, checkExistingSession]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Обработка входа...</h2>
          <p className="text-gray-600">Пожалуйста, подождите</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-xl p-8 text-center max-w-md">
          <div className="text-6xl mb-4">❌</div>
          <h2 className="text-2xl font-bold text-red-600 mb-4">Ошибка входа</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => navigate('/login')}
            className="bg-indigo-600 text-white py-2 px-6 rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Попробовать снова
          </button>
        </div>
      </div>
    );
  }

  return null;
};

export default AuthCallback;
