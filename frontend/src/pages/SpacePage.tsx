import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  createKB,
  createNode,
  deleteNode,
  getDocument,
  getTree,
  importDocument,
  listKB,
  saveDocument,
  searchInKb,
  updateNode,
} from '../api'
import type { KbSearchHit } from '../api'
import type { DocNode, KnowledgeBase } from '../api/types'
import { indexDocument } from '../api/rag'
import type { SearchHit } from '../api/rag'
import { extractErrorMessage } from '../api/errors'
import Editor from '../components/Editor'
import ChatPanel from '../components/ChatPanel'
import PromptModal from '../components/PromptModal'
import MoveModal from '../components/MoveModal'
import type { FolderOption } from '../components/MoveModal'
import MembersModal from '../components/MembersModal'
import Toast from '../components/Toast'
import type { ToastState } from '../components/Toast'

type View = 'docs' | 'chat'

interface PromptState {
  open: boolean
  title: string
  label?: string
  defaultValue?: string
  onConfirm: (v: string) => void
}

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

  const [membersOpen, setMembersOpen] = useState(false)
  const [moveNode, setMoveNode] = useState<DocNode | null>(null)
  const [promptState, setPromptState] = useState<PromptState>({ open: false, title: '', onConfirm: () => {} })
  const [searchQ, setSearchQ] = useState('')
  const [searchResults, setSearchResults] = useState<KbSearchHit[]>([])
  const [searching, setSearching] = useState(false)
  const [toast, setToast] = useState<ToastState | null>(null)
  const toastTimer = useRef<number | undefined>(undefined)
  const fileRef = useRef<HTMLInputElement>(null)

  const showToast = (message: string, type: ToastState['type'] = 'info') => {
    setToast({ message, type })
    window.clearTimeout(toastTimer.current)
    toastTimer.current = window.setTimeout(() => setToast(null), 2600)
  }

  const openPrompt = (
    title: string,
    label: string,
    defaultValue: string,
    work: (v: string) => void | Promise<void>,
  ) => {
    setPromptState({
      open: true,
      title,
      label,
      defaultValue,
      onConfirm: (v) => {
        setPromptState((p) => ({ ...p, open: false }))
        void work(v)
      },
    })
  }

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
      setSearchResults([])
      setSearchQ('')
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

  // 点击问答引用 → 切到文档视图并打开对应文档
  const openHit = async (hit: SearchHit) => {
    if (!hit.node_id || !hit.knowledge_base_id) return
    setView('docs')
    const fake: DocNode = {
      id: hit.node_id,
      knowledge_base_id: hit.knowledge_base_id,
      parent_id: null,
      title: hit.document_title || '文档',
      kind: 'document',
      position: 0,
      created_at: '',
      updated_at: '',
    }
    await openNode(fake)
  }

  const handleSave = async () => {
    if (!activeNode || !activeKb) return
    try {
      await saveDocument(activeKb, activeNode.id, { content, content_format: contentFormat })
      setDirty(false)
    } catch (err: any) {
      showToast('保存失败：' + extractErrorMessage(err), 'error')
      return
    }
    try {
      const { data } = await indexDocument('document', activeNode.id)
      setIndexMsg(`已索引 ${data.chunk_count} 个片段`)
      showToast('已保存并索引', 'success')
    } catch (err: any) {
      const msg = extractErrorMessage(err)
      setIndexMsg(msg)
      showToast('已保存，索引失败：' + msg, 'error')
    }
  }

  const handleReindex = async () => {
    if (!activeNode) return
    setIndexMsg('索引中...')
    try {
      const { data } = await indexDocument('document', activeNode.id)
      setIndexMsg(`已索引 ${data.chunk_count} 个片段`)
      showToast('重新索引完成', 'success')
    } catch (err: any) {
      setIndexMsg(extractErrorMessage(err))
      showToast(extractErrorMessage(err), 'error')
    }
  }

  const askNewDoc = () => {
    if (!activeKb) return
    openPrompt('新建文档', '文档标题', '', async (title) => {
      try {
        const { data } = await createNode(activeKb, { title, kind: 'document' })
        await loadTree()
        await openNode(data)
        showToast('已创建文档', 'success')
      } catch (err: any) {
        showToast(extractErrorMessage(err), 'error')
      }
    })
  }

  const askNewFolder = () => {
    if (!activeKb) return
    openPrompt('新建文件夹', '文件夹名称', '', async (title) => {
      try {
        await createNode(activeKb, { title, kind: 'folder' })
        await loadTree()
        showToast('已创建文件夹', 'success')
      } catch (err: any) {
        showToast(extractErrorMessage(err), 'error')
      }
    })
  }

  const askRename = (n: DocNode) => {
    if (!activeKb) return
    openPrompt('重命名', '新名称', n.title, async (title) => {
      try {
        await updateNode(activeKb, n.id, { title })
        await loadTree()
        if (activeNode && activeNode.id === n.id) setActiveNode({ ...activeNode, title })
        showToast('已重命名', 'success')
      } catch (err: any) {
        showToast(extractErrorMessage(err), 'error')
      }
    })
  }

  const handleDelete = async (n: DocNode) => {
    if (!activeKb) return
    if (!confirm(`删除「${n.title}」？该操作不可撤销。`)) return
    try {
      await deleteNode(activeKb, n.id)
      if (activeNode?.id === n.id) {
        setActiveNode(null)
        setContent('')
      }
      await loadTree()
      showToast('已删除', 'success')
    } catch (err: any) {
      showToast(extractErrorMessage(err), 'error')
    }
  }

  const handleMove = async (parentId: string | null) => {
    if (!activeKb || !moveNode) return
    try {
      await updateNode(activeKb, moveNode.id, { parent_id: parentId })
      setMoveNode(null)
      await loadTree()
      showToast('已移动', 'success')
    } catch (err: any) {
      showToast(extractErrorMessage(err), 'error')
    }
  }

  const handleImport = async (file: File) => {
    if (!activeKb) return
    showToast('导入中...', 'info')
    try {
      const { data } = await importDocument(activeKb, file)
      await loadTree()
      showToast('导入成功，已自动建索引', 'success')
      if (data.kind === 'document') await openNode(data)
    } catch (err: any) {
      showToast('导入失败：' + extractErrorMessage(err), 'error')
    }
  }

  const doSearch = async () => {
    const q = searchQ.trim()
    if (!q || !activeKb) {
      setSearchResults([])
      return
    }
    setSearching(true)
    try {
      const { data } = await searchInKb(activeKb, q)
      setSearchResults(data)
    } catch (err: any) {
      showToast(extractErrorMessage(err), 'error')
    } finally {
      setSearching(false)
    }
  }

  const openSearchResult = async (hit: KbSearchHit) => {
    if (hit.kind !== 'document' || !activeKb) return
    const fake: DocNode = {
      id: hit.node_id,
      knowledge_base_id: activeKb,
      parent_id: null,
      title: hit.title,
      kind: 'document',
      position: 0,
      created_at: '',
      updated_at: '',
    }
    await openNode(fake)
  }

  const handleNewKB = () => {
    if (!spaceId) return
    openPrompt('新建知识库', '知识库名称', '', async (name) => {
      try {
        const { data } = await createKB(spaceId, { name })
        setKbs((prev) => [...prev, data])
        setActiveKb(data.id)
        showToast('已创建知识库', 'success')
      } catch (err: any) {
        showToast(extractErrorMessage(err), 'error')
      }
    })
  }

  const toggleKb = (kbId: string) => {
    setSelectedKbs((prev) =>
      prev.includes(kbId) ? prev.filter((id) => id !== kbId) : [...prev, kbId],
    )
  }

  const folderOptions: FolderOption[] = useMemo(() => {
    if (!moveNode) return []
    const excluded = new Set<string>([moveNode.id])
    const walk = (pid: string) => {
      tree
        .filter((n) => n.parent_id === pid)
        .forEach((c) => {
          excluded.add(c.id)
          walk(c.id)
        })
    }
    walk(moveNode.id)
    const opts: FolderOption[] = []
    const build = (parentId: string | null, depth: number) => {
      tree
        .filter((n) => n.parent_id === parentId && n.kind === 'folder' && !excluded.has(n.id))
        .forEach((n) => {
          opts.push({ id: n.id, label: n.title, depth })
          build(n.id, depth + 1)
        })
    }
    build(null, 0)
    return opts
  }, [moveNode, tree])

  const renderTree = (nodes: DocNode[], depth = 0) =>
    nodes.map((n) => (
      <div key={n.id} className="group relative">
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
        <div className="absolute right-1 top-1 hidden group-hover:flex items-center gap-0.5 bg-white/90 rounded px-1">
          <button
            title="重命名"
            onClick={(e) => {
              e.stopPropagation()
              askRename(n)
            }}
            className="text-xs text-gray-400 hover:text-blue-600 px-0.5"
          >
            ✎
          </button>
          <button
            title="移动"
            onClick={(e) => {
              e.stopPropagation()
              setMoveNode(n)
            }}
            className="text-xs text-gray-400 hover:text-blue-600 px-0.5"
          >
            ➜
          </button>
          <button
            title="删除"
            onClick={(e) => {
              e.stopPropagation()
              handleDelete(n)
            }}
            className="text-xs text-gray-400 hover:text-red-600 px-0.5"
          >
            🗑
          </button>
        </div>
        {renderTree(
          tree.filter((c) => c.parent_id === n.id),
          depth + 1,
        )}
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
            <div className="flex items-center gap-2">
              <button onClick={askNewFolder} className="text-blue-600 text-xs hover:underline">
                + 文件夹
              </button>
              <button onClick={askNewDoc} className="text-blue-600 text-xs hover:underline">
                + 文档
              </button>
              <button
                onClick={() => fileRef.current?.click()}
                className="text-blue-600 text-xs hover:underline"
              >
                导入
              </button>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.doc,.docx,.md,.txt"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) handleImport(f)
                  e.target.value = ''
                }}
              />
            </div>
          </div>

          {/* 全文搜索 */}
          <div className="px-2 mb-2">
            <input
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') doSearch()
              }}
              placeholder="搜索文档内容，回车"
              className="w-full border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {(searching || searchResults.length > 0) && (
              <div className="mt-1 border border-gray-200 rounded max-h-40 overflow-y-auto bg-white">
                {searching && <p className="text-xs text-gray-400 px-2 py-1">搜索中...</p>}
                {!searching && searchResults.length === 0 && (
                  <p className="text-xs text-gray-400 px-2 py-1">无匹配</p>
                )}
                {searchResults.map((r) => (
                  <button
                    key={r.node_id}
                    onClick={() => openSearchResult(r)}
                    className="block w-full text-left px-2 py-1 text-xs text-gray-700 hover:bg-gray-100 truncate"
                  >
                    {r.kind === 'folder' ? '📁' : '📄'} {r.title}
                  </button>
                ))}
              </div>
            )}
          </div>

          {renderTree(rootNodes)}
        </div>
      </aside>

      {/* 右侧：编辑器 / 问答 */}
      <main className="flex-1 flex flex-col">
        <div className="flex items-center justify-between bg-white border-b border-gray-200 px-4">
          <div className="flex items-center">
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
          <button
            onClick={() => setMembersOpen(true)}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            成员
          </button>
        </div>

        {view === 'chat' ? (
          <ChatPanel kbIds={selectedKbs} onOpenHit={openHit} />
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
                  onClick={() => handleDelete(activeNode)}
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

      {spaceId && (
        <MembersModal spaceId={spaceId} open={membersOpen} onClose={() => setMembersOpen(false)} />
      )}
      <MoveModal
        open={!!moveNode}
        title={`移动「${moveNode?.title || ''}」`}
        folders={folderOptions}
        onClose={() => setMoveNode(null)}
        onConfirm={handleMove}
      />
      <PromptModal
        open={promptState.open}
        title={promptState.title}
        label={promptState.label}
        defaultValue={promptState.defaultValue}
        onClose={() => setPromptState((p) => ({ ...p, open: false }))}
        onConfirm={promptState.onConfirm}
      />
      <Toast toast={toast} />
    </div>
  )
}
