import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getMe, login, register } from '../api'
import { extractErrorMessage } from '../api/errors'
import { useAuth } from '../store/auth'

export default function LoginPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const setUser = useAuth((s) => s.setUser)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        const { data } = await login(email, password)
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
      } else {
        await register({ email, username, password })
      }
      // 登录后拉取用户信息
      if (mode === 'login') {
        const { data: me } = await getMe()
        setUser(me)
        navigate('/')
      } else {
        setMode('login')
        setPassword('')
      }
    } catch (err: any) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-sm p-8">
        <h1 className="text-2xl font-bold text-gray-900 text-center">LocalRAG KB</h1>
        <p className="mt-1 text-sm text-gray-500 text-center">
          {mode === 'login' ? '登录你的知识库' : '注册新账号'}
        </p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">邮箱</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {mode === 'register' && (
            <div>
              <label className="block text-sm font-medium text-gray-700">用户名</label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700">密码</label>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? '处理中...' : mode === 'login' ? '登录' : '注册'}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-500">
          {mode === 'login' ? '没有账号？' : '已有账号？'}
          <button
            onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
            className="ml-1 text-blue-600 hover:underline"
          >
            {mode === 'login' ? '去注册' : '去登录'}
          </button>
        </p>
      </div>
    </div>
  )
}
