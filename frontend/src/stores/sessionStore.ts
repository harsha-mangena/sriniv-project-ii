import { create } from 'zustand'

interface Message {
  role: 'ai' | 'user'
  text: string
  score?: number
  atoms?: { id: string; label: string; score: number }[]
}

interface SessionState {
  sessionId: string | null
  resumeId: string | null
  jdId: string | null
  messages: Message[]
  currentQuestion: string | null
  currentCategory: string | null
  currentDifficulty: number
  isLoading: boolean
  isActive: boolean
  setSession: (sessionId: string, resumeId: string, jdId: string) => void
  addMessage: (msg: Message) => void
  setQuestion: (question: string, category: string, difficulty: number) => void
  setLoading: (loading: boolean) => void
  setActive: (active: boolean) => void
  reset: () => void
}

export const useSessionStore = create<SessionState>((set) => ({
  sessionId: null,
  resumeId: null,
  jdId: null,
  messages: [],
  currentQuestion: null,
  currentCategory: null,
  currentDifficulty: 3,
  isLoading: false,
  isActive: false,
  setSession: (sessionId, resumeId, jdId) => set({ sessionId, resumeId, jdId, isActive: true }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setQuestion: (question, category, difficulty) => set({ currentQuestion: question, currentCategory: category, currentDifficulty: difficulty }),
  setLoading: (loading) => set({ isLoading: loading }),
  setActive: (active) => set({ isActive: active }),
  reset: () => set({ sessionId: null, resumeId: null, jdId: null, messages: [], currentQuestion: null, currentCategory: null, currentDifficulty: 3, isLoading: false, isActive: false }),
}))
