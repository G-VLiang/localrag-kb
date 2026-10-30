import { useEffect, useState } from 'react'
import Modal from './Modal'

export interface FolderOption {
  id: string
  label: string
  depth: number
}

export default function MoveModal({
  open,
  title,
  folders,
  onClose,
  onConfirm,
}: {
  open: boolean
  title: string
  folders: FolderOption[]
  onClose: () => void
  onConfirm: (parentId: string | null) => void
}) {
  const [target, setTarget] = useState('root')

  useEffect(() => {
    if (open) setTarget('root')
  }, [open])

  return (
    <Modal open={open} title={title} onClose={onClose}>
      <div className="space-y-3">
        <label className="block text-xs text-gray-500">移动到</label>
        <select
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="root">（根目录）</option>
          {folders.map((f) => (
            <option key={f.id} value={f.id}>
              {'　'.repeat(f.depth)}
              {f.label}
            </option>
          ))}
        </select>
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm rounded border border-gray-300 text-gray-600"
          >
            取消
          </button>
          <button
            onClick={() => onConfirm(target === 'root' ? null : target)}
            className="px-3 py-1.5 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
          >
            移动
          </button>
        </div>
      </div>
    </Modal>
  )
}
