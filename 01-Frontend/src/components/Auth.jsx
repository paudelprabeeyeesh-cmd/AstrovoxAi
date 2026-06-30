import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'

export default function Auth({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { signIn, signUp, error } = useAuth()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    
    const result = isLogin 
      ? await signIn(email, password)
      : await signUp(email, password)
    
    setLoading(false)
    if (result.success && onLogin) {
      onLogin(result.user)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-void-black p-4">
      <div className="glass-morphism rounded-3xl p-8 w-full max-w-md border border-neon-cyan/20 shadow-2xl">
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">🧠</div>
          <h1 className="text-3xl font-bold gradient-text">ASTRAVOX PRIME</h1>
          <p className="text-gray-400 text-sm mt-2">
            {isLogin ? 'Sign in to your neural core' : 'Create your cognitive identity'}
          </p>
        </div>

        {error && (
          <div className="bg-red-500/10 border-l-4 border-red-500 p-3 rounded-lg mb-4 text-red-400 text-sm">
            ⚠️ {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-black/40 border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-neon-cyan transition mb-4"
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-black/40 border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-neon-cyan transition mb-6"
            required
          />

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-neon-cyan to-neon-purple text-black font-bold py-3 rounded-full hover:scale-[1.02] transition disabled:opacity-50"
          >
            {loading ? '⏳ CONNECTING...' : isLogin ? '🔓 LOGIN' : '🔐 REGISTER'}
          </button>
        </form>

        <div className="text-center mt-4 text-sm text-gray-400">
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <span
            onClick={() => setIsLogin(!isLogin)}
            className="text-neon-cyan cursor-pointer hover:underline"
          >
            {isLogin ? 'Register' : 'Login'}
          </span>
        </div>

        <div className="mt-6 pt-4 border-t border-gray-800 text-center text-xs text-gray-500">
          Built by Prabesh Paudel, Dipson Baral & Susanta Baral. All rights reserved. &copy; 2027
        </div>
      </div>
    </div>
  )
}