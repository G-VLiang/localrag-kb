import { useEffect, useState } from 'react'
import Modal from './Modal'

export default function PromptModal({
  open,
  title,
  label,
  defaultValue = '',
  placeholder = '',
  onClose,
  onConfirm,
}: {
  open: boolean
  title: string
  label?: string
  defaultValue?: string
  placeholder?: string
  onClose: () => void
  onConfirm: (value: string) => void
}) {
  const [value, setValue] = useState(defaultValue)

  useEffect(() => {
    if (open) setValue(defaultValue)
  }, [open, defaultValue])

  const submit = () => {
    if (value.trim()) onConfirm(value.trim())
  }

  return (
    <Modal open={open} title={title} onClose={onClose}>
      <div className="space-y-3">
        {label && <label className="block text-xs text-gray-500">{label}</label>}
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          autoFocus
          className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          onKeyDown={(e) => {
            if (e.key === 'Enter') submit()
          }}
        />
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm rounded border border-gray-300 text-gray-600"
          >
            取消
          </button>
          <button
            onClick={submit}
            className="px-3 py-1.5 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
          >
            确定
          </button>
        </div>
      </div>
    </Modal>
  )
}
