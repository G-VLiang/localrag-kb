import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createSpace, listSpaces } from '../api'
import { useAuth } from '../store/auth'
import type { Space } from '../api/types'

export default function HomePage() {
  const [spaces, setSpaces] = useState<Space[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const loadSpaces = () => {
    listSpaces()
      .then(({ data }) => setSpaces(data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadSpaces()
  }, [])

  const handleCreateSpace = async () => {
    const name = prompt('空间名称：')
    if (!name) return
    const { data } = await createSpace({ name, kind: 'personal' })
    setSpaces((prev) => [...prev, data])
    navigate(`/space/${data.id}`)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900">LocalRAG KB</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">{user?.username || user?.email}</span>
            <button
              onClick={() => navigate('/audit')}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              操作日志
            </button>
            <button
              onClick={() => {
                logout()
                navigate('/login')
              }}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              退出
            </button>
          </div>
        </div>
      </header>
      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">我的空间</h2>
          <button
            onClick={handleCreateSpace}
            className="px-3 py-1.5 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
          >
            + 新建空间
          </button>
        </div>
        {loading ? (
          <p className="mt-4 text-gray-500">加载中...</p>
        ) : spaces.length === 0 ? (
          <div className="mt-8 text-center text-gray-500">
            <p>还没有空间</p>
            <p className="text-sm mt-1">点击右上角「+ 新建空间」创建你的第一个知识空间</p>
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-2 gap-4">
            {spaces.map((s) => (
              <button
                key={s.id}
                onClick={() => navigate(`/space/${s.id}`)}
                className="text-left bg-white rounded-lg border border-gray-200 p-4 hover:shadow-sm"
              >
                <p className="font-medium text-gray-900">{s.name}</p>
                <p className="text-sm text-gray-500 mt-1">{s.description || '无描述'}</p>
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
