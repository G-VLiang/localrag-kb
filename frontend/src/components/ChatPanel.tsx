import { useState } from 'react'
import { askQuestion } from '../api/rag'
import { extractErrorMessage } from '../api/errors'
import type { SearchHit } from '../api/rag'

interface Message {
  role: 'user' | 'assistant'
  content: string
  hits?: SearchHit[]
}

interface ChatPanelProps {
  kbIds: string[]
}

export default function ChatPanel({ kbIds }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const send = async () => {
    const q = input.trim()
    if (!q || kbIds.length === 0) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: q }])
    setLoading(true)
    try {
      const { data } = await askQuestion(q, kbIds)
      setMessages((prev) => [...prev, { role: 'assistant', content: data.answer, hits: data.hits }])
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `出错了：${extractErrorMessage(err)}` },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-2">
        <h3 className="text-sm font-semibold text-gray-700">智能问答</h3>
        <span className="text-xs text-gray-400">
          检索范围：{kbIds.length > 0 ? `${kbIds.length} 个知识库` : '未选择'}
        </span>
      </div>

      {/* 消息区 */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center mt-8">
            <p className="text-sm text-gray-400">
              {kbIds.length === 0
                ? '请在左侧勾选要检索的知识库'
                : '就你的知识库提问，我会基于文档内容回答并标注来源'}
            </p>
            <p className="text-xs text-gray-300 mt-2">
              提示：文档保存后会自动建立向量索引
            </p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.hits && m.hits.length > 0 && (
                <div className="mt-2 space-y-1 border-t border-gray-200 pt-2">
                  <p className="text-xs text-gray-500 font-medium">📚 来源引用：</p>
                  {m.hits.map((h, j) => (
                    <div key={j} className="text-xs text-gray-600">
                      <span className="font-medium">[{j + 1}] {h.document_title}</span>
                      <span className="text-gray-400"> (相关度 {(h.score * 100).toFixed(0)}%)</span>
                      <p className="text-gray-500 line-clamp-2">{h.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && <p className="text-sm text-gray-400">思考中...</p>}
      </div>

      {/* 输入区 */}
      <div className="border-t border-gray-200 p-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder={kbIds.length === 0 ? '请先选择知识库' : '输入问题，回车发送'}
          disabled={kbIds.length === 0}
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={send}
          disabled={loading || kbIds.length === 0}
          className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          发送
        </button>
      </div>
    </div>
  )
}
