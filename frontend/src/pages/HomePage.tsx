import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createSpace, listSpaces } from '../api'
import { useAuth } from '../store/auth'
import type { Space } from '../api/types'
import PromptModal from '../components/PromptModal'

export default function HomePage() {
  const [spaces, setSpaces] = useState<Space[]>([])
  const [loading, setLoading] = useState(true)
  const [promptOpen, setPromptOpen] = useState(false)
  const [promptKind, setPromptKind] = useState<'personal' | 'team'>('personal')
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

  const openCreate = (kind: 'personal' | 'team') => {
    setPromptKind(kind)
    setPromptOpen(true)
  }

  const handleCreate = async (name: string) => {
    setPromptOpen(false)
    try {
      const { data } = await createSpace({ name, kind: promptKind })
      setSpaces((prev) => [...prev, data])
      navigate(`/space/${data.id}`)
    } catch {
      /* 忽略：错误提示可后续统一处理 */
    }
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
          <div className="flex gap-2">
            <button
              onClick={() => openCreate('personal')}
              className="px-3 py-1.5 text-sm rounded border border-gray-300 text-gray-700 hover:bg-gray-100"
            >
              + 个人空间
            </button>
            <button
              onClick={() => openCreate('team')}
              className="px-3 py-1.5 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
            >
              + 团队空间
            </button>
          </div>
        </div>
        {loading ? (
          <p className="mt-4 text-gray-500">加载中...</p>
        ) : spaces.length === 0 ? (
          <div className="mt-8 text-center text-gray-500">
            <p>还没有空间</p>
            <p className="text-sm mt-1">创建个人空间或团队空间开始沉淀知识</p>
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-2 gap-4">
            {spaces.map((s) => (
              <button
                key={s.id}
                onClick={() => navigate(`/space/${s.id}`)}
                className="text-left bg-white rounded-lg border border-gray-200 p-4 hover:shadow-sm"
              >
                <div className="flex items-center gap-2">
                  <p className="font-medium text-gray-900">{s.name}</p>
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded ${
                      s.kind === 'team'
                        ? 'bg-blue-50 text-blue-600'
                        : 'bg-gray-100 text-gray-500'
                    }`}
                  >
                    {s.kind === 'team' ? '团队' : '个人'}
                  </span>
                </div>
                <p className="text-sm text-gray-500 mt-1">{s.description || '无描述'}</p>
              </button>
            ))}
          </div>
        )}
      </main>

      <PromptModal
        open={promptOpen}
        title={promptKind === 'team' ? '新建团队空间' : '新建个人空间'}
        label="空间名称"
        onClose={() => setPromptOpen(false)}
        onConfirm={handleCreate}
      />
    </div>
  )
}
