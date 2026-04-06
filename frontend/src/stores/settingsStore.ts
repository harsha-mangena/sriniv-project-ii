import { create } from 'zustand'

interface SettingsState {
  ollamaUrl: string
  model: string
  theme: 'dark' | 'light'
  setOllamaUrl: (url: string) => void
  setModel: (model: string) => void
  setTheme: (theme: 'dark' | 'light') => void
}

export const useSettingsStore = create<SettingsState>((set) => ({
  ollamaUrl: 'http://localhost:11434',
  model: 'qwen3:8b',
  theme: 'dark',
  setOllamaUrl: (url) => set({ ollamaUrl: url }),
  setModel: (model) => set({ model }),
  setTheme: (theme) => set({ theme }),
}))
