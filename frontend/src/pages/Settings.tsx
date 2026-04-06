import { useState } from 'react'
import { useSettingsStore } from '../stores/settingsStore'
import { api } from '../services/api'

export default function Settings() {
  const settings = useSettingsStore()
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState<string | null>(null)

  const handleSave = async () => {
    setSaving(true)
    setStatus(null)
    try {
      await api.post('/settings', {
        llm_provider: settings.llmProvider,
        ollama_url: settings.ollamaUrl,
        ollama_model: settings.ollamaModel,
        gemini_api_key: settings.geminiApiKey || undefined,
        gemini_model: settings.geminiModel,
      })
      setStatus('Settings saved successfully!')
    } catch (e) {
      setStatus(`Error: ${e instanceof Error ? e.message : 'Failed to save'}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold text-white">Settings</h2>

      {/* LLM Provider Selection */}
      <div className="card space-y-6">
        <div>
          <label className="text-sm font-medium text-gray-300 block mb-2">LLM Provider</label>
          <div className="flex gap-3">
            <button
              className={`px-4 py-2 rounded-lg text-sm ${settings.llmProvider === 'ollama' ? 'bg-accent text-white' : 'bg-navy-700 text-gray-400'}`}
              onClick={() => settings.setLLMProvider('ollama')}
            >
              Ollama (Local)
            </button>
            <button
              className={`px-4 py-2 rounded-lg text-sm ${settings.llmProvider === 'gemini' ? 'bg-accent text-white' : 'bg-navy-700 text-gray-400'}`}
              onClick={() => settings.setLLMProvider('gemini')}
            >
              Google Gemini (Cloud)
            </button>
          </div>
        </div>

        {/* Ollama Settings */}
        {settings.llmProvider === 'ollama' && (
          <>
            <div>
              <label className="text-sm font-medium text-gray-300 block mb-2">Ollama URL</label>
              <input
                className="input w-full"
                value={settings.ollamaUrl}
                onChange={(e) => settings.setOllamaUrl(e.target.value)}
              />
              <p className="text-xs text-gray-500 mt-1">Default: http://localhost:11434</p>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-300 block mb-2">Ollama Model</label>
              <select
                className="input w-full"
                value={settings.ollamaModel}
                onChange={(e) => settings.setOllamaModel(e.target.value)}
              >
                <option value="qwen3:8b">Qwen3 8B (recommended, 16GB RAM)</option>
                <option value="qwen3:4b">Qwen3 4B (faster, 8GB RAM)</option>
                <option value="llama3.1:8b">Llama 3.1 8B (16GB RAM)</option>
                <option value="llama3.2:3b">Llama 3.2 3B (fastest, 8GB RAM)</option>
                <option value="mistral:7b">Mistral 7B (16GB RAM)</option>
                <option value="deepseek-r1:8b">DeepSeek R1 8B (best reasoning)</option>
              </select>
            </div>
          </>
        )}

        {/* Gemini Settings */}
        {settings.llmProvider === 'gemini' && (
          <>
            <div>
              <label className="text-sm font-medium text-gray-300 block mb-2">Gemini API Key</label>
              <input
                className="input w-full"
                type="password"
                value={settings.geminiApiKey}
                onChange={(e) => settings.setGeminiApiKey(e.target.value)}
                placeholder="Enter your Google Gemini API key"
              />
              <p className="text-xs text-gray-500 mt-1">
                Get a free API key at{' '}
                <span className="text-accent">aistudio.google.com</span>
              </p>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-300 block mb-2">Gemini Model</label>
              <select
                className="input w-full"
                value={settings.geminiModel}
                onChange={(e) => settings.setGeminiModel(e.target.value)}
              >
                <option value="gemini-2.0-flash">Gemini 2.0 Flash (recommended, free tier)</option>
                <option value="gemini-2.0-flash-lite">Gemini 2.0 Flash Lite (fastest)</option>
                <option value="gemini-1.5-flash">Gemini 1.5 Flash (legacy)</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro (most capable)</option>
              </select>
            </div>
          </>
        )}

        {/* Save Button */}
        <div className="flex items-center gap-4">
          <button
            className="px-6 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent/90 disabled:opacity-50"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          {status && (
            <p className={`text-sm ${status.startsWith('Error') ? 'text-red-400' : 'text-green-400'}`}>
              {status}
            </p>
          )}
        </div>
      </div>

      {/* Theme */}
      <div className="card space-y-4">
        <div>
          <label className="text-sm font-medium text-gray-300 block mb-2">Theme</label>
          <div className="flex gap-3">
            <button
              className={`px-4 py-2 rounded-lg text-sm ${settings.theme === 'dark' ? 'bg-accent text-white' : 'bg-navy-700 text-gray-400'}`}
              onClick={() => settings.setTheme('dark')}
            >
              Dark
            </button>
            <button
              className={`px-4 py-2 rounded-lg text-sm ${settings.theme === 'light' ? 'bg-accent text-white' : 'bg-navy-700 text-gray-400'}`}
              onClick={() => settings.setTheme('light')}
            >
              Light
            </button>
          </div>
        </div>
      </div>

      {/* About */}
      <div className="card">
        <h3 className="text-sm font-medium text-gray-400 mb-3">About InterviewPilot</h3>
        <div className="text-sm text-gray-500 space-y-1">
          <p>Version 0.1.0</p>
          <p>Powered by AoT + ToT hybrid reasoning engine</p>
          <p>Supports Ollama (local) and Google Gemini (cloud) LLM providers</p>
          <p>Open source — MIT License</p>
        </div>
      </div>
    </div>
  )
}
