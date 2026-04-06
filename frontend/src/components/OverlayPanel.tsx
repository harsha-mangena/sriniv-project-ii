import { useState } from 'react'
import { Minimize2, Maximize2, X, Radio } from 'lucide-react'
import clsx from 'clsx'

interface OverlayPanelProps {
  suggestion: string
  transcript: string[]
  connected: boolean
  onClose: () => void
}

export default function OverlayPanel({ suggestion, transcript, connected, onClose }: OverlayPanelProps) {
  const [minimized, setMinimized] = useState(false)

  return (
    <div className={clsx(
      'fixed bottom-4 right-4 bg-navy-800/95 backdrop-blur-lg border border-navy-600 rounded-2xl shadow-2xl transition-all duration-300 z-50',
      minimized ? 'w-48 h-12' : 'w-96'
    )}>
      <div className="flex items-center justify-between px-4 py-2 border-b border-navy-700">
        <div className="flex items-center gap-2">
          <Radio size={14} className={connected ? 'text-emerald-400 animate-pulse' : 'text-gray-500'} />
          <span className="text-xs font-medium text-gray-300">
            {connected ? 'Live' : 'Disconnected'}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => setMinimized(!minimized)} className="p-1 hover:bg-navy-600 rounded">
            {minimized ? <Maximize2 size={12} /> : <Minimize2 size={12} />}
          </button>
          <button onClick={onClose} className="p-1 hover:bg-navy-600 rounded text-gray-400">
            <X size={12} />
          </button>
        </div>
      </div>
      {!minimized && (
        <div className="p-4 max-h-80 overflow-y-auto space-y-3">
          {suggestion && (
            <div className="bg-accent/10 border border-accent/30 rounded-lg p-3">
              <p className="text-xs font-medium text-accent mb-1">Suggestion</p>
              <p className="text-sm text-gray-200 whitespace-pre-wrap">{suggestion}</p>
            </div>
          )}
          {transcript.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Transcript</p>
              {transcript.slice(-5).map((line, i) => (
                <p key={i} className="text-xs text-gray-400 mb-1">{line}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
