import { useState, useRef, useEffect } from 'react'
import { Radio, Play, Square } from 'lucide-react'
import OverlayPanel from '../components/OverlayPanel'

export default function RealTimeAssist() {
  const [connected, setConnected] = useState(false)
  const [transcript, setTranscript] = useState<string[]>([])
  const [suggestion, setSuggestion] = useState('')
  const [showOverlay, setShowOverlay] = useState(false)
  const ws = useRef<WebSocket | null>(null)

  const connect = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    ws.current = new WebSocket(`${protocol}//${window.location.host}/api/realtime/stream`)

    ws.current.onopen = () => {
      setConnected(true)
      setShowOverlay(true)
    }

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'suggestion') {
        setSuggestion(data.text)
      } else if (data.type === 'question_detected') {
        setTranscript(prev => [...prev, `[Question] ${data.question}`])
      }
    }

    ws.current.onclose = () => setConnected(false)
    ws.current.onerror = () => setConnected(false)
  }

  const disconnect = () => {
    ws.current?.close()
    setConnected(false)
    setShowOverlay(false)
  }

  useEffect(() => {
    return () => { ws.current?.close() }
  }, [])

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold text-white">Real-Time Assistant</h2>
      <p className="text-gray-400">
        Connect to get live suggestions during meetings. The assistant listens to the conversation
        and provides context-aware hints.
      </p>

      <div className="card text-center space-y-4">
        <div className="flex items-center justify-center gap-2">
          <Radio size={20} className={connected ? 'text-emerald-400 animate-pulse' : 'text-gray-500'} />
          <span className={connected ? 'text-emerald-400' : 'text-gray-500'}>
            {connected ? 'Connected — Listening' : 'Disconnected'}
          </span>
        </div>

        {!connected ? (
          <button className="btn-primary flex items-center gap-2 mx-auto" onClick={connect}>
            <Play size={16} /> Start Assistant
          </button>
        ) : (
          <button className="bg-red-500/20 text-red-400 px-6 py-2.5 rounded-lg hover:bg-red-500/30 transition-colors flex items-center gap-2 mx-auto" onClick={disconnect}>
            <Square size={16} /> Stop
          </button>
        )}

        <p className="text-xs text-gray-600">
          Requires an LLM provider (Ollama or Gemini). Configure in Settings.
        </p>
      </div>

      {transcript.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-medium text-gray-400 mb-2">Transcript</h3>
          <div className="space-y-1 max-h-60 overflow-y-auto">
            {transcript.map((line, i) => (
              <p key={i} className="text-xs text-gray-400">{line}</p>
            ))}
          </div>
        </div>
      )}

      {showOverlay && (
        <OverlayPanel
          suggestion={suggestion}
          transcript={transcript}
          connected={connected}
          onClose={() => setShowOverlay(false)}
        />
      )}
    </div>
  )
}
