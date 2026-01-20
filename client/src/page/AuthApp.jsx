import React, { useState, useRef, useEffect } from 'react';
import { Lock, Mail, User, LogIn, UserPlus, Eye, EyeOff, Send, MessageSquare, BrainCircuit, Sparkles, Bot, UserCircle } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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

  if (isLoggedIn && userData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-4 md:p-8 flex gap-6 justify-center items-start">
        {/* Sidebar - User Profile & Memory */}
        <div className="w-full max-w-sm bg-white/80 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/50 p-6 sticky top-8 h-[750px] flex flex-col relative">
          <div className="text-center mb-6 flex-shrink-0">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-500 via-indigo-600 to-purple-600 rounded-full mx-auto mb-4 flex items-center justify-center text-white shadow-xl ring-4 ring-blue-100">
              <User size={40} strokeWidth={2.5} />
            </div>
            <h2 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-700 bg-clip-text text-transparent">Welcome Back!</h2>
            <p className="text-lg text-gray-700 font-medium mt-1">{userData.name || 'User'}</p>
          </div>

          {/* Memory Section */}
          <div className="flex-1 bg-gradient-to-br from-indigo-50 to-blue-50 border border-indigo-100 rounded-2xl p-5 overflow-hidden flex flex-col mb-16 shadow-inner">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-indigo-200 flex-shrink-0">
              <div className="flex items-center gap-2 text-indigo-900 font-bold text-lg">
                <BrainCircuit size={22} className="text-indigo-600" />
                <h3>AI Memory</h3>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto space-y-5 pr-2 custom-scrollbar">
              {/* Likes */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-green-700 mb-2.5 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span> 
                  What I Like
                </h4>
                {userData.memory.likes.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {userData.memory.likes.map((like, i) => (
                      <span key={i} className="bg-white text-green-800 px-3 py-1.5 rounded-lg text-xs font-medium border border-green-200 shadow-sm hover:shadow-md transition-shadow">
                        {like}
                      </span>
                    ))}
                  </div>
                ) : <p className="text-gray-400 text-xs italic">No data yet...</p>}
              </div>

              {/* Dislikes */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-red-700 mb-2.5 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span> 
                  What I Dislike
                </h4>
                {userData.memory.dislikes.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {userData.memory.dislikes.map((dislike, i) => (
                      <span key={i} className="bg-white text-red-800 px-3 py-1.5 rounded-lg text-xs font-medium border border-red-200 shadow-sm hover:shadow-md transition-shadow">
                        {dislike}
                      </span>
                    ))}
                  </div>
                ) : <p className="text-gray-400 text-xs italic">No data yet...</p>}
              </div>
            </div>
          </div>

          {/* Logout Button */}
          <div className='absolute inset-x-6 bottom-6'>
            <button
              onClick={handleLogout}
              className="w-full bg-gradient-to-r from-red-50 to-red-100 text-red-600 py-3 rounded-xl font-semibold hover:from-red-100 hover:to-red-200 transition-all border border-red-200 shadow-md hover:shadow-lg"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Chat Area */}
        <div className="w-full bg-white/90 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/50 flex flex-col h-[750px] overflow-hidden">
          {/* Chat Header */}
          <div className="p-5 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-t-3xl flex justify-between items-center shadow-sm z-10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg">
                <Bot size={22} className="text-white" />
              </div>
              <div>
                <h3 className="font-bold text-gray-800 flex items-center gap-2">
                  AI Shopping Assistant
                </h3>
                <div className="flex items-center gap-1.5 text-xs text-green-600">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span>Online</span>
                </div>
              </div>
            </div>
            <Sparkles size={20} className="text-indigo-500" />
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-5 bg-gradient-to-b from-gray-50/50 to-white">
            {messages.length === 0 && (
              <div className="text-center mt-24">
                <div className="w-20 h-20 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-full mx-auto mb-4 flex items-center justify-center">
                  <MessageSquare className="w-10 h-10 text-indigo-400" />
                </div>
                <p className="text-gray-500 font-medium text-lg">Start your conversation!</p>
                <p className="text-sm text-gray-400 mt-2">Try: "I like chocolate and coding"</p>
              </div>
            )}
            
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
                {msg.role === 'ai' && (
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-md">
                    <Bot size={18} className="text-white" />
                  </div>
                )}
                
                <div 
                  className={`max-w-[75%] px-4 py-3 rounded-2xl shadow-md text-sm ${
                    msg.role === 'user' 
                      ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-tr-sm' 
                      : 'bg-white text-gray-800 border border-gray-100 rounded-tl-sm'
                  }`}
                >
                  {msg.role === 'user' ? (
                    <p className="leading-relaxed">{msg.text}</p>
                  ) : (
                    <div className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-p:text-gray-700 prose-strong:text-gray-900 prose-a:text-blue-600">
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        components={{
                          a: ({node, ...props}) => (
                            <a {...props} className="text-blue-600 hover:text-blue-700 underline font-medium" target="_blank" rel="noopener noreferrer" />
                          ),
                          code: ({node, inline, ...props}) => (
                            inline ? 
                              <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono text-pink-600" {...props} /> :
                              <code className="block bg-gray-100 p-2 rounded-lg text-xs font-mono overflow-x-auto" {...props} />
                          )
                        }}
                      >
                        {msg.text}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>

                {msg.role === 'user' && (
                  <div className="w-8 h-8 bg-gradient-to-br from-gray-700 to-gray-900 rounded-xl flex items-center justify-center flex-shrink-0 shadow-md">
                    <UserCircle size={18} className="text-white" />
                  </div>
                )}
              </div>
            ))}

            {chatLoading && (
              <div className="flex gap-3 justify-start animate-in fade-in slide-in-from-bottom-2 duration-300">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-md">
                  <Bot size={18} className="text-white" />
                </div>
                <div className="bg-white px-5 py-4 rounded-2xl rounded-tl-sm border border-gray-100 shadow-md flex gap-1.5">
                  <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-5 bg-white border-t border-gray-100 rounded-b-3xl">
            <form onSubmit={handleSendMessage} className="flex gap-3">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Type your message..."
                disabled={chatLoading}
                className="flex-1 px-5 py-3.5 border border-gray-200 rounded-2xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all bg-gray-50 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button 
                type="submit" 
                disabled={chatLoading || !chatInput.trim()}
                className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white px-5 py-3.5 rounded-2xl hover:from-blue-600 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl disabled:shadow-md flex items-center justify-center"
              >
                <Send size={20} />
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

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