import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  createKB,
  createNode,
  deleteNode,
  getDocument,
  getTree,
  listKB,
  saveDocument,
} from '../api'
import type { DocNode, KnowledgeBase } from '../api/types'
import { indexDocument } from '../api/rag'
import { extractErrorMessage } from '../api/errors'
import Editor from '../components/Editor'
import ChatPanel from '../components/ChatPanel'

type View = 'docs' | 'chat'

export default function SpacePage() {
  const { spaceId } = useParams<{ spaceId: string }>()
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [activeKb, setActiveKb] = useState<string | null>(null)
  const [selectedKbs, setSelectedKbs] = useState<string[]>([])
  const [view, setView] = useState<View>('docs')
  const [tree, setTree] = useState<DocNode[]>([])
  const [activeNode, setActiveNode] = useState<DocNode | null>(null)
  const [content, setContent] = useState('')
  const [contentFormat, setContentFormat] = useState<'html' | 'markdown'>('html')
  const [dirty, setDirty] = useState(false)
  const [indexMsg, setIndexMsg] = useState('')

  const loadKbs = useCallback(async () => {
    if (!spaceId) return
    const { data } = await listKB(spaceId)
    setKbs(data)
    if (data.length > 0) {
      setActiveKb((prev) => prev || data[0].id)
      setSelectedKbs((prev) => (prev.length > 0 ? prev : [data[0].id]))
    }
  }, [spaceId])

  const loadTree = useCallback(async () => {
    if (!activeKb) return
    const { data } = await getTree(activeKb)
    setTree(data)
  }, [activeKb])

  useEffect(() => {
    loadKbs()
  }, [loadKbs])

  useEffect(() => {
    if (activeKb) {
      loadTree()
      setActiveNode(null)
      setContent('')
    }
  }, [activeKb, loadTree])

  const openNode = async (node: DocNode) => {
    if (node.kind === 'folder') return
    setActiveNode(node)
    const { data } = await getDocument(node.knowledge_base_id, node.id)
    setContent(data.content)
    setContentFormat(data.content_format)
    setDirty(false)
  }

  const handleSave = async () => {
    if (!activeNode || !activeKb) return
    await saveDocument(activeKb, activeNode.id, { content, content_format: contentFormat })
    setDirty(false)
    // 保存后自动重建该文档索引（后台向量化）
    try {
      const { data } = await indexDocument('document', activeNode.id)
      setIndexMsg(`已索引 ${data.chunk_count} 个片段`)
    } catch (err: any) {
      // 索引失败不阻塞保存，但提示原因
      setIndexMsg(extractErrorMessage(err))
    }
  }

  const handleReindex = async () => {
    if (!activeNode) return
    setIndexMsg('索引中...')
    try {
      const { data } = await indexDocument('document', activeNode.id)
      setIndexMsg(`已索引 ${data.chunk_count} 个片段`)
    } catch (err: any) {
      setIndexMsg(extractErrorMessage(err))
    }
  }

  const handleNewDoc = async () => {
    if (!activeKb) return
    const title = prompt('文档标题：')
    if (!title) return
    const { data } = await createNode(activeKb, { title, kind: 'document' })
    await loadTree()
    await openNode(data)
  }

  const handleNewKB = async () => {
    if (!spaceId) return
    const name = prompt('知识库名称：')
    if (!name) return
    const { data } = await createKB(spaceId, { name })
    setKbs((prev) => [...prev, data])
    setActiveKb(data.id)
  }

  const handleDelete = async () => {
    if (!activeNode || !activeKb) return
    if (!confirm(`删除「${activeNode.title}」？`)) return
    await deleteNode(activeKb, activeNode.id)
    setActiveNode(null)
    setContent('')
    await loadTree()
  }

  const toggleKb = (kbId: string) => {
    setSelectedKbs((prev) =>
      prev.includes(kbId) ? prev.filter((id) => id !== kbId) : [...prev, kbId],
    )
  }

  const renderTree = (nodes: DocNode[], depth = 0) =>
    nodes.map((n) => (
      <div key={n.id}>
        <button
          onClick={() => openNode(n)}
          className={`w-full text-left px-3 py-1.5 text-sm rounded hover:bg-gray-100 flex items-center gap-2 ${
            activeNode?.id === n.id ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
          }`}
          style={{ paddingLeft: 12 + depth * 16 }}
        >
          <span>{n.kind === 'folder' ? '📁' : '📄'}</span>
          <span className="truncate">{n.title}</span>
        </button>
        {renderTree(tree.filter((c) => c.parent_id === n.id), depth + 1)}
      </div>
    ))

  const rootNodes = tree.filter((n) => n.parent_id === null)

  return (
    <div className="flex h-screen bg-gray-50">
      {/* 左侧：知识库 + 文档树 */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-3 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-gray-700">知识库</span>
            <button onClick={handleNewKB} className="text-blue-600 text-sm hover:underline">
              + 新建
            </button>
          </div>
          <div className="mt-2 space-y-1">
            {kbs.map((kb) => (
              <div key={kb.id} className="flex items-center gap-1 group">
                <input
                  type="checkbox"
                  checked={selectedKbs.includes(kb.id)}
                  onChange={() => toggleKb(kb.id)}
                  className="shrink-0"
                />
                <button
                  onClick={() => setActiveKb(kb.id)}
                  className={`flex-1 text-left px-2 py-1.5 text-sm rounded ${
                    activeKb === kb.id ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  🗂 {kb.name}
                </button>
              </div>
            ))}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          <div className="flex items-center justify-between px-2 mb-1">
            <span className="text-xs text-gray-400">文档树</span>
            <button onClick={handleNewDoc} className="text-blue-600 text-xs hover:underline">
              + 文档
            </button>
          </div>
          {renderTree(rootNodes)}
        </div>
      </aside>

      {/* 右侧：编辑器 / 问答 */}
      <main className="flex-1 flex flex-col">
        <div className="flex items-center bg-white border-b border-gray-200 px-4">
          <button
            onClick={() => setView('docs')}
            className={`px-4 py-2 text-sm font-medium border-b-2 ${
              view === 'docs'
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            文档
          </button>
          <button
            onClick={() => setView('chat')}
            className={`px-4 py-2 text-sm font-medium border-b-2 ${
              view === 'chat'
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            智能问答
          </button>
        </div>

        {view === 'chat' ? (
          <ChatPanel kbIds={selectedKbs} />
        ) : activeNode ? (
          <>
            <div className="flex items-center justify-between bg-white border-b border-gray-200 px-4 py-2">
              <h2 className="text-sm font-medium text-gray-900">{activeNode.title}</h2>
              <div className="flex items-center gap-3">
                {dirty && <span className="text-xs text-amber-600">未保存</span>}
                {indexMsg && <span className="text-xs text-gray-500">{indexMsg}</span>}
                <button
                  onClick={handleReindex}
                  title="重建该文档的向量索引"
                  className="px-3 py-1 text-sm rounded text-gray-600 hover:bg-gray-100"
                >
                  重建索引
                </button>
                <button
                  onClick={handleSave}
                  className="px-3 py-1 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
                >
                  保存
                </button>
                <button
                  onClick={handleDelete}
                  className="px-3 py-1 text-sm rounded text-red-600 hover:bg-red-50"
                >
                  删除
                </button>
              </div>
            </div>
            <Editor
              key={activeNode.id}
              content={content}
              onChange={(html) => {
                setContent(html)
                setDirty(true)
              }}
            />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            选择或新建一篇文档开始编辑
          </div>
        )}
      </main>
    </div>
  )
}
