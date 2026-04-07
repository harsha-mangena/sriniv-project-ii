import { create } from 'zustand'

type LLMProvider = 'ollama' | 'gemini'
type OverlayPosition = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'

interface SettingsState {
  llmProvider: LLMProvider
  ollamaUrl: string
  ollamaModel: string
  geminiApiKey: string
  geminiModel: string
  theme: 'dark' | 'light'
  // Overlay settings (Tauri desktop app)
  overlayOpacity: number
  overlayPosition: OverlayPosition
  overlayWidth: number
  shortcutsEnabled: boolean
  autoScreenshot: boolean
  screenshotIntervalSecs: number
  setLLMProvider: (provider: LLMProvider) => void
  setOllamaUrl: (url: string) => void
  setOllamaModel: (model: string) => void
  setGeminiApiKey: (key: string) => void
  setGeminiModel: (model: string) => void
  setTheme: (theme: 'dark' | 'light') => void
  setOverlayOpacity: (opacity: number) => void
  setOverlayPosition: (position: OverlayPosition) => void
  setOverlayWidth: (width: number) => void
  setShortcutsEnabled: (enabled: boolean) => void
  setAutoScreenshot: (enabled: boolean) => void
  setScreenshotIntervalSecs: (secs: number) => void
}

export const useSettingsStore = create<SettingsState>((set) => ({
  llmProvider: 'ollama',
  ollamaUrl: 'http://localhost:11434',
  ollamaModel: 'qwen3:8b',
  geminiApiKey: '',
  geminiModel: 'gemini-2.0-flash',
  theme: 'dark',
  overlayOpacity: 0.9,
  overlayPosition: 'top-right',
  overlayWidth: 400,
  shortcutsEnabled: true,
  autoScreenshot: false,
  screenshotIntervalSecs: 10,
  setLLMProvider: (provider) => set({ llmProvider: provider }),
  setOllamaUrl: (url) => set({ ollamaUrl: url }),
  setOllamaModel: (model) => set({ ollamaModel: model }),
  setGeminiApiKey: (key) => set({ geminiApiKey: key }),
  setGeminiModel: (model) => set({ geminiModel: model }),
  setTheme: (theme) => set({ theme }),
  setOverlayOpacity: (opacity) => set({ overlayOpacity: opacity }),
  setOverlayPosition: (position) => set({ overlayPosition: position }),
  setOverlayWidth: (width) => set({ overlayWidth: width }),
  setShortcutsEnabled: (enabled) => set({ shortcutsEnabled: enabled }),
  setAutoScreenshot: (enabled) => set({ autoScreenshot: enabled }),
  setScreenshotIntervalSecs: (secs) => set({ screenshotIntervalSecs: secs }),
}))
