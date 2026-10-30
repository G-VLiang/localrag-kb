export interface User {
  id: string
  email: string
  username: string
  is_active: boolean
  created_at: string
}

export interface Space {
  id: string
  name: string
  description: string | null
  kind: string
  created_at: string
}

export interface KnowledgeBase {
  id: string
  space_id: string
  name: string
  description: string | null
  created_at: string
}

export interface DocNode {
  id: string
  knowledge_base_id: string
  parent_id: string | null
  title: string
  kind: 'folder' | 'document'
  position: number
  created_at: string
  updated_at: string
}

export interface Document {
  id: string
  node_id: string
  content: string
  content_format: 'html' | 'markdown'
  version: number
  updated_at: string
}
