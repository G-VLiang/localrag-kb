import api from './client'

export interface SearchHit {
  chunk_id: string
  document_id: string
  node_id: string
  content: string
  score: number
  document_title: string
  knowledge_base_id: string
}

export interface AskResponse {
  answer: string
  hits: SearchHit[]
}

export const askQuestion = (query: string, kb_ids: string[], top_k = 5) =>
  api.post<AskResponse>('/rag/ask', { query, kb_ids, top_k })

export const searchDocs = (query: string, kb_ids: string[], top_k = 5) =>
  api.post<{ hits: SearchHit[] }>('/rag/search', { query, kb_ids, top_k })

export const indexDocument = (scope: string, node_id?: string) =>
  api.post<{ status: string; chunk_count: number }>('/rag/index', { scope, node_id })
