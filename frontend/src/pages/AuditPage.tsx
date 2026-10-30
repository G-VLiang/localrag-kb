import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listMyAudit } from '../api/audit'
import type { AuditLog } from '../api/audit'
import { extractErrorMessage } from '../api/errors'

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    listMyAudit(100)
      .then(({ data }) => setLogs(data))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-lg font-semibold text-gray-900">操作日志</h1>
          <button onClick={() => navigate('/')} className="text-sm text-gray-500 hover:text-gray-700">
            返回
          </button>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-6 py-6">
        {loading ? (
          <p className="text-gray-500">加载中...</p>
        ) : error ? (
          <p className="text-red-600">{error}</p>
        ) : logs.length === 0 ? (
          <div className="text-center text-gray-500 mt-10">
            <p>暂无操作记录</p>
            <p className="text-sm mt-1">你的写操作（保存文档、建库、导入等）会记录在这里</p>
          </div>
        ) : (
          <div className="overflow-x-auto bg-white rounded-lg border border-gray-200">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">时间</th>
                  <th className="text-left px-4 py-2 font-medium">操作</th>
                  <th className="text-left px-4 py-2 font-medium">方法</th>
                  <th className="text-left px-4 py-2 font-medium">路径</th>
                  <th className="text-left px-4 py-2 font-medium">状态</th>
                  <th className="text-left px-4 py-2 font-medium">IP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {logs.map((l) => (
                  <tr key={l.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-600 whitespace-nowrap">
                      {new Date(l.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2 text-gray-900">{l.action}</td>
                    <td className="px-4 py-2 text-gray-500">{l.method}</td>
                    <td className="px-4 py-2 text-gray-500 font-mono text-xs">{l.path}</td>
                    <td className={`px-4 py-2 ${l.status_code < 400 ? 'text-green-600' : 'text-red-600'}`}>
                      {l.status_code}
                    </td>
                    <td className="px-4 py-2 text-gray-500">{l.ip || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
