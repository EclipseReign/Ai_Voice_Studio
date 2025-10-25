import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';

const EmailVerification = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [message, setMessage] = useState('');

  const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

  useEffect(() => {
    const verifyEmail = async () => {
      try {
        const token = searchParams.get('token');
        
        if (!token) {
          setStatus('error');
          setMessage('Токен верификации не найден');
          return;
        }

        const response = await axios.get(`${API}/auth/verify-email?token=${token}`);
        
        setStatus('success');
        setMessage(response.data.message || 'Email успешно подтверждён!');
        
        // Redirect to login after 3 seconds
        setTimeout(() => {
          navigate('/login');
        }, 3000);
      } catch (error) {
        setStatus('error');
        setMessage(error.response?.data?.detail || 'Ошибка верификации email');
      }
    };

    verifyEmail();
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 text-center max-w-md">
        {status === 'verifying' && (
          <>
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-indigo-600 mx-auto mb-4"></div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Верификация email...</h2>
            <p className="text-gray-600">Пожалуйста, подождите</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="text-6xl mb-4">✅</div>
            <h2 className="text-2xl font-bold text-green-600 mb-4">Успешно!</h2>
            <p className="text-gray-600 mb-4">{message}</p>
            <p className="text-sm text-gray-500">Перенаправление на страницу входа...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="text-6xl mb-4">❌</div>
            <h2 className="text-2xl font-bold text-red-600 mb-4">Ошибка</h2>
            <p className="text-gray-600 mb-6">{message}</p>
            <button
              onClick={() => navigate('/login')}
              className="bg-indigo-600 text-white py-2 px-6 rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Вернуться ко входу
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default EmailVerification;
