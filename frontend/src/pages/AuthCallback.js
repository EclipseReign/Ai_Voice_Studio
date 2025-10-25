import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const AuthCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { processSessionId } = useAuth();
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get session_id from URL query params
        const sessionId = searchParams.get('session_id');
        
        if (!sessionId) {
          setError('Не получен session_id от Emergent Auth');
          setLoading(false);
          return;
        }

        // Process session with backend
        const success = await processSessionId(sessionId);
        
        if (success) {
          // Redirect to dashboard on success
          navigate('/dashboard');
        } else {
          setError('Ошибка обработки сессии');
          setLoading(false);
        }
      } catch (err) {
        console.error('Auth callback error:', err);
        setError('Ошибка аутентификации');
        setLoading(false);
      }
    };

    handleCallback();
  }, [searchParams, processSessionId, navigate]);

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
