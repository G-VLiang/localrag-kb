import { useCallback, useEffect, useState } from 'react'
import Modal from './Modal'
import { addMember, listMembers, removeMember, updateMember } from '../api/members'
import type { SpaceMember } from '../api/members'
import { extractErrorMessage } from '../api/errors'

const ROLES = ['admin', 'editor', 'reader']

export default function MembersModal({
  spaceId,
  open,
  onClose,
}: {
  spaceId: string
  open: boolean
  onClose: () => void
}) {
  const [members, setMembers] = useState<SpaceMember[]>([])
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('editor')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    if (!spaceId) return
    listMembers(spaceId)
      .then(({ data }) => setMembers(data))
      .catch((e) => setErr(extractErrorMessage(e)))
  }, [spaceId])

  useEffect(() => {
    if (open) {
      setErr('')
      load()
    }
  }, [open, load])

  const handleAdd = async () => {
    if (!email.trim()) return
    setBusy(true)
    setErr('')
    try {
      await addMember(spaceId, { email: email.trim(), role })
      setEmail('')
      load()
    } catch (e: any) {
      setErr(extractErrorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const handleRole = async (m: SpaceMember, newRole: string) => {
    try {
      await updateMember(spaceId, m.id, { role: newRole })
      load()
    } catch (e: any) {
      setErr(extractErrorMessage(e))
    }
  }

  const handleRemove = async (m: SpaceMember) => {
    if (!confirm(`移除成员 ${m.user.username || m.user.email}？`)) return
    try {
      await removeMember(spaceId, m.id)
      load()
    } catch (e: any) {
      setErr(extractErrorMessage(e))
    }
  }

  return (
    <Modal open={open} title="空间成员" onClose={onClose}>
      <div className="space-y-3">
        <div className="flex gap-2">
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="成员邮箱"
            className="flex-1 border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="border border-gray-300 rounded px-2 text-sm"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <button
            onClick={handleAdd}
            disabled={busy}
            className="px-3 py-1.5 text-sm rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            邀请
          </button>
        </div>
        {err && <p className="text-xs text-red-600">{err}</p>}
        <div className="divide-y divide-gray-100 max-h-72 overflow-y-auto">
          {members.map((m) => (
            <div key={m.id} className="flex items-center justify-between py-2 text-sm">
              <div className="min-w-0">
                <p className="text-gray-800 truncate">{m.user.username || m.user.email}</p>
                <p className="text-xs text-gray-400 truncate">{m.user.email}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {m.role === 'owner' ? (
                  <span className="text-xs text-gray-500">owner</span>
                ) : (
                  <>
                    <select
                      value={m.role}
                      onChange={(e) => handleRole(m, e.target.value)}
                      className="border border-gray-300 rounded px-1 text-xs"
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                    <button onClick={() => handleRemove(m)} className="text-xs text-red-500 hover:underline">
                      移除
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
          {members.length === 0 && <p className="text-xs text-gray-400 py-4 text-center">暂无成员</p>}
        </div>
        <p className="text-xs text-gray-400">
          邀请需对方已注册。角色：admin 可管理成员，editor 可读写，reader 只读。
        </p>
      </div>
    </Modal>
  )
}
