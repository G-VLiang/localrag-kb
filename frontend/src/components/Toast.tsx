export interface ToastState {
  message: string
  type?: 'info' | 'success' | 'error'
}

export default function Toast({ toast }: { toast: ToastState | null }) {
  if (!toast || !toast.message) return null
  const color =
    toast.type === 'error' ? 'bg-red-600' : toast.type === 'success' ? 'bg-green-600' : 'bg-gray-800'
  return (
    <div className={`fixed bottom-6 right-6 z-50 ${color} text-white text-sm px-4 py-2 rounded shadow-lg`}>
      {toast.message}
    </div>
  )
}
