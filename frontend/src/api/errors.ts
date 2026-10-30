// 从 axios 错误中提取人类可读的错误信息
// FastAPI 的 detail 可能是：字符串、{msg} 对象、或 [{loc, msg, type}] 数组
export function extractErrorMessage(err: any): string {
  const detail = err?.response?.data?.detail
  if (!detail) return '操作失败，请稍后重试'

  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d: any) => d?.msg)
      .filter(Boolean)
    if (msgs.length > 0) return msgs.join('；')
  }

  if (typeof detail === 'object' && detail?.msg) {
    return String(detail.msg)
  }

  return '操作失败，请稍后重试'
}
