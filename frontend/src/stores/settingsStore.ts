import { create } from 'zustand'

type LLMProvider = 'ollama' | 'gemini'

interface SettingsState {
  llmProvider: LLMProvider
  ollamaUrl: string
  ollamaModel: string
  geminiApiKey: string
  geminiModel: string
  theme: 'dark' | 'light'
  setLLMProvider: (provider: LLMProvider) => void
  setOllamaUrl: (url: string) => void
  setOllamaModel: (model: string) => void
  setGeminiApiKey: (key: string) => void
  setGeminiModel: (model: string) => void
  setTheme: (theme: 'dark' | 'light') => void
}

export const useSettingsStore = create<SettingsState>((set) => ({
  llmProvider: 'ollama',
  ollamaUrl: 'http://localhost:11434',
  ollamaModel: 'qwen3:8b',
  geminiApiKey: '',
  geminiModel: 'gemini-2.0-flash',
  theme: 'dark',
  setLLMProvider: (provider) => set({ llmProvider: provider }),
  setOllamaUrl: (url) => set({ ollamaUrl: url }),
  setOllamaModel: (model) => set({ ollamaModel: model }),
  setGeminiApiKey: (key) => set({ geminiApiKey: key }),
  setGeminiModel: (model) => set({ geminiModel: model }),
  setTheme: (theme) => set({ theme }),
}))
