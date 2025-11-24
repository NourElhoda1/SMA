import React, { useState, useRef, useEffect } from 'react';
import { Lock, Mail, User, LogIn, UserPlus, Eye, EyeOff, Send, MessageSquare, RefreshCw, BrainCircuit } from 'lucide-react';

export default function AuthApp() {
  const [isSignup, setIsSignup] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: ''
  });
  
  const [userData, setUserData] = useState(null);
  const [token, setToken] = useState('');

  // --- Nouveaux états pour le Chat ---
  const [chatInput, setChatInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const API_BASE = 'http://127.0.0.1:8000';

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
    setSuccess('');
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch(`${API_BASE}/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      const data = await response.json();
      if (response.ok) {
        setSuccess('Compte créé ! Connectez-vous.');
        setTimeout(() => { setIsSignup(false); setSuccess(''); }, 2000);
      } else {
        setError(data.detail || 'Erreur inscription');
      }
    } catch (err) {
      setError('Erreur serveur.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const formBody = new URLSearchParams();
      formBody.append('username', formData.email);
      formBody.append('password', formData.password);

      const response = await fetch(`${API_BASE}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formBody
      });
      const data = await response.json();

      if (response.ok) {
        setToken(data.access_token);
        await fetchUserProfile(data.access_token);
        setIsLoggedIn(true);
      } else {
        setError(data.detail || 'Erreur connexion');
      }
    } catch (err) {
      setError('Erreur serveur.');
    } finally {
      setLoading(false);
    }
  };

  const fetchUserProfile = async (accessToken) => {
    try {
      const response = await fetch(`${API_BASE}/me`, {
        headers: { 'Authorization': `Bearer ${accessToken}` }
      });
      const data = await response.json();
      if (response.ok) {
        setUserData(data);
      }
    } catch (err) {
      console.error('Erreur profil:', err);
    }
  };

  // --- Logique du Chat ---
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput;
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setChatInput('');
    setChatLoading(true);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ message: userMsg })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setMessages(prev => [...prev, { role: 'ai', text: data.response }]);
        // Rafraîchir le profil pour voir si la mémoire a changé (Likes/Dislikes)
        fetchUserProfile(token);
      } else {
        setMessages(prev => [...prev, { role: 'ai', text: "Erreur lors de la réponse." }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'ai', text: "Erreur de connexion." }]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setToken('');
    setUserData(null);
    setMessages([]);
    setFormData({ email: '', password: '', name: '' });
  };

  // --- Vue Connectée (Profil + Chat) ---
  if (isLoggedIn && userData) {
    return (
      <div className="min-h-screen bg-slate-50 p-4 md:p-8 flex gap-6 justify-center items-start">
        
        {/* Colonne Gauche : Profil & Mémoire */}
        <div className="w-full max-w-sm bg-white rounded-2xl shadow-xl p-6 sticky top-8 h-[750px] flex flex-col relative">
          
          {/* Header Profil */}
          <div className="text-center mb-6 flex-shrink-0">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-full mx-auto mb-4 flex items-center justify-center text-white shadow-lg">
              <User size={40} />
            </div>
            <h2 className="text-2xl font-bold text-gray-800">Welcome Back!</h2>
            <p className="text-lg text-gray-600 font-medium">{userData.name || 'User'}</p>
          </div>

          {/* Carte Mémoire (Scrollable) */}
          <div className="flex-1 bg-indigo-50 border border-indigo-100 rounded-2xl p-4 overflow-hidden flex flex-col mb-16">
            <div className="flex items-center justify-between mb-3 border-b border-indigo-200 pb-2 flex-shrink-0">
              <div className="flex items-center gap-2 text-indigo-800 font-bold">
                <BrainCircuit size={20} />
                <h3>Mémoire IA</h3>
              </div>
              <button onClick={() => fetchUserProfile(token)} className="text-indigo-400 hover:text-indigo-700 transition-colors" title="Actualiser">
                <RefreshCw size={16} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-4 pr-1 custom-scrollbar">
              {/* Section Likes */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-green-700 mb-2 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span> Ce que j'aime
                </h4>
                {userData.memory.likes.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {userData.memory.likes.map((like, i) => (
                      <span key={i} className="bg-white text-green-800 px-2 py-1 rounded-md text-xs border border-green-200 shadow-sm">
                        {like}
                      </span>
                    ))}
                  </div>
                ) : <p className="text-gray-400 text-xs italic">Aucune donnée...</p>}
              </div>

              {/* Section Dislikes */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-red-700 mb-2 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span> Ce que je déteste
                </h4>
                {userData.memory.dislikes.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {userData.memory.dislikes.map((dislike, i) => (
                      <span key={i} className="bg-white text-red-800 px-2 py-1 rounded-md text-xs border border-red-200 shadow-sm">
                        {dislike}
                      </span>
                    ))}
                  </div>
                ) : <p className="text-gray-400 text-xs italic">Aucune donnée...</p>}
              </div>
            </div>
            
            
          </div>

          {/* Bouton Logout Fixé en bas */}
          <div className='absolute inset-x-6 bottom-6'>
            <button
              onClick={handleLogout}
              className="w-full bg-red-50 text-red-600 py-3 rounded-xl font-semibold hover:bg-red-100 transition-colors border border-red-100"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Colonne Droite : Chat Interface */}
        <div className="w-full  bg-white rounded-2xl shadow-xl flex flex-col h-[750px]">
          {/* Chat Header */}
          <div className="p-4 border-b bg-white rounded-t-2xl flex justify-between items-center shadow-sm z-10">
            <h3 className="font-bold text-gray-700 flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              AI Assistant
            </h3>
            <button onClick={() => fetchUserProfile(token)} className="text-gray-400 hover:text-blue-500 transition-colors" title="Refresh Memory">
              <RefreshCw size={18} />
            </button>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
            {messages.length === 0 && (
              <div className="text-center text-gray-400 mt-20">
                <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-20" />
                <p>Start chatting! Try telling me what you like.</p>
                <p className="text-xs mt-2">Example: "I like chocolate and coding"</p>
              </div>
            )}
            
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div 
                  className={`max-w-[80%] p-3 rounded-2xl shadow-sm text-sm ${
                    msg.role === 'user' 
                      ? 'bg-blue-600 text-white rounded-tr-none' 
                      : 'bg-white text-gray-800 border border-gray-100 rounded-tl-none'
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex justify-start">
                <div className="bg-white p-3 rounded-2xl rounded-tl-none border shadow-sm flex gap-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-75"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-150"></div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input */}
          <div className="p-4 bg-white border-t rounded-b-2xl">
            <form onSubmit={handleSendMessage} className="flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Type your message..."
                disabled={chatLoading}
                className="flex-1 px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
              />
              <button 
                type="submit" 
                disabled={chatLoading || !chatInput.trim()}
                className="bg-blue-600 text-white p-3 rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg"
              >
                <Send size={20} />
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  // --- Vue Non Connectée (Login/Signup) ---
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full mx-auto mb-4 flex items-center justify-center">
            {isSignup ? <UserPlus className="w-8 h-8 text-white" /> : <LogIn className="w-8 h-8 text-white" />}
          </div>
          <h2 className="text-3xl font-bold text-gray-800 mb-2">
            {isSignup ? 'Create Account' : 'Welcome Back'}
          </h2>
          <p className="text-gray-600">
            {isSignup ? 'Sign up to get started' : 'Sign in to your account'}
          </p>
        </div>

        {error && <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>}
        {success && <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">{success}</div>}

        <form onSubmit={isSignup ? handleSignup : handleLogin} className="space-y-5">
          {isSignup && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input type="text" name="name" value={formData.name} onChange={handleInputChange} className="w-full pl-11 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" placeholder="John Doe" />
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input type="email" name="email" value={formData.email} onChange={handleInputChange} required className="w-full pl-11 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" placeholder="you@example.com" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input type={showPassword ? "text" : "password"} name="password" value={formData.password} onChange={handleInputChange} required className="w-full pl-11 pr-11 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" placeholder="••••••••" />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          <button type="submit" disabled={loading} className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white py-3 rounded-lg font-semibold hover:from-blue-600 hover:to-indigo-700 transition-all shadow-lg disabled:opacity-50">
            {loading ? 'Processing...' : (isSignup ? 'Sign Up' : 'Sign In')}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-gray-600">
            {isSignup ? 'Already have an account?' : "Don't have an account?"}
            <button onClick={() => { setIsSignup(!isSignup); setError(''); setSuccess(''); }} className="ml-2 text-blue-600 font-semibold hover:text-blue-700">
              {isSignup ? 'Sign In' : 'Sign Up'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}