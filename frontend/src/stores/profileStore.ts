import { create } from 'zustand'

interface ProfileState {
  resumeId: string | null
  jdId: string | null
  resumeParsed: Record<string, unknown> | null
  jdParsed: Record<string, unknown> | null
  matchScore: Record<string, unknown> | null
  setResume: (id: string, parsed: Record<string, unknown>) => void
  setJD: (id: string, parsed: Record<string, unknown>) => void
  setMatchScore: (score: Record<string, unknown>) => void
  reset: () => void
}

export const useProfileStore = create<ProfileState>((set) => ({
  resumeId: null,
  jdId: null,
  resumeParsed: null,
  jdParsed: null,
  matchScore: null,
  setResume: (id, parsed) => set({ resumeId: id, resumeParsed: parsed }),
  setJD: (id, parsed) => set({ jdId: id, jdParsed: parsed }),
  setMatchScore: (score) => set({ matchScore: score }),
  reset: () => set({ resumeId: null, jdId: null, resumeParsed: null, jdParsed: null, matchScore: null }),
}))
