import { useSettingsStore } from '../stores/settingsStore'

export default function Settings() {
  const settings = useSettingsStore()

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold text-white">Settings</h2>

      <div className="card space-y-6">
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
          <label className="text-sm font-medium text-gray-300 block mb-2">LLM Model</label>
          <select
            className="input w-full"
            value={settings.model}
            onChange={(e) => settings.setModel(e.target.value)}
          >
            <option value="qwen3:8b">Qwen3 8B (recommended, 16GB RAM)</option>
            <option value="qwen3:4b">Qwen3 4B (faster, 8GB RAM)</option>
            <option value="llama3.1:8b">Llama 3.1 8B (16GB RAM)</option>
            <option value="llama3.2:3b">Llama 3.2 3B (fastest, 8GB RAM)</option>
            <option value="mistral:7b">Mistral 7B (16GB RAM)</option>
            <option value="deepseek-r1:8b">DeepSeek R1 8B (best reasoning)</option>
          </select>
        </div>

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

      <div className="card">
        <h3 className="text-sm font-medium text-gray-400 mb-3">About InterviewPilot</h3>
        <div className="text-sm text-gray-500 space-y-1">
          <p>Version 0.1.0</p>
          <p>Powered by AoT + ToT hybrid reasoning engine</p>
          <p>100% local — no data leaves your machine</p>
          <p>Open source — MIT License</p>
        </div>
      </div>
    </div>
  )
}
