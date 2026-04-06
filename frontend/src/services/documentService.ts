import { api } from './api'

export interface ParsedDocument {
  id: string
  doc_type: string
  parsed_data: Record<string, unknown>
  match_score?: Record<string, unknown>
  created_at: string
}

export async function uploadDocument(text: string, docType: 'resume' | 'job_description'): Promise<ParsedDocument> {
  return api.post<ParsedDocument>('/documents/upload', { text, doc_type: docType })
}

export async function getDocument(docId: string): Promise<ParsedDocument> {
  return api.get<ParsedDocument>(`/documents/${docId}`)
}
