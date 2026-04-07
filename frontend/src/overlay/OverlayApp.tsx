import { useState, useEffect } from 'react'
import TranscriptPanel from './TranscriptPanel'
import SuggestionPanel from './SuggestionPanel'
import OverlayControls from './OverlayControls'
import QuickChat from './QuickChat'
import StatusBar from './StatusBar'

declare global {
  interface Window {
    __TAURI__?: {
      event: {
        listen: (event: string, handler: (payload: any) => void) => Promise<() => void>
      }
      core: {
        invoke: (cmd: string, args?: Record<string, unknown>) => Promise<any>
      }
    }
  }
}

export interface TranscriptSegment {
  text: string
  speaker: string
  start_ms: number
  end_ms: number
  timestamp_ms: number
}

export interface Suggestion {
  text: string
  confidence: number
  question?: string
}

type OverlayView = 'transcript' | 'suggestions' | 'chat'

export default function OverlayApp() {
  const [view, setView] = useState<OverlayView>('transcript')
  const [isRecording, setIsRecording] = useState(false)
  const [segments, setSegments] = useState<TranscriptSegment[]>([])
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const tauri = window.__TAURI__
    if (!tauri) return

    const unlisteners: Array<() => void> = []

    // Listen for transcript updates
    tauri.event.listen('transcript-update', (event: any) => {
      const data = event.payload as { segments: TranscriptSegment[]; full_text: string; speaker: string }
      setSegments(prev => [...prev, ...data.segments].slice(-200))
      setConnected(true)
    }).then(fn => unlisteners.push(fn))

    // Listen for recording status changes
    tauri.event.listen('recording-status', (event: any) => {
      setIsRecording(event.payload as boolean)
    }).then(fn => unlisteners.push(fn))

    // Listen for suggestions
    tauri.event.listen('suggestion', (event: any) => {
      const suggestion = event.payload as Suggestion
      setSuggestions(prev => [suggestion, ...prev].slice(0, 10))
      setView('suggestions')
    }).then(fn => unlisteners.push(fn))

    // Listen for focus-chat-input (Cmd+Enter shortcut)
    tauri.event.listen('focus-chat-input', () => {
      setView('chat')
    }).then(fn => unlisteners.push(fn))

    // Listen for context clear
    tauri.event.listen('context-cleared', () => {
      setSegments([])
      setSuggestions([])
    }).then(fn => unlisteners.push(fn))

    // Check initial state
    tauri.core.invoke('get_recording_status').then((status: boolean) => {
      setIsRecording(status)
    }).catch(() => {})

    return () => {
      unlisteners.forEach(fn => fn())
    }
  }, [])

  const handleToggleRecording = async () => {
    const tauri = window.__TAURI__
    if (!tauri) return

    try {
      if (isRecording) {
        await tauri.core.invoke('stop_recording')
      } else {
        await tauri.core.invoke('start_recording')
      }
    } catch (e) {
      console.error('Failed to toggle recording:', e)
    }
  }

  const handleScreenshot = async () => {
    const tauri = window.__TAURI__
    if (!tauri) return

    try {
      await tauri.core.invoke('take_screenshot')
    } catch (e) {
      console.error('Failed to take screenshot:', e)
    }
  }

  return (
    <div className="overlay-root">
      <StatusBar
        isRecording={isRecording}
        connected={connected}
        segmentCount={segments.length}
      />

      <OverlayControls
        activeView={view}
        onViewChange={setView}
        isRecording={isRecording}
        onToggleRecording={handleToggleRecording}
        onScreenshot={handleScreenshot}
      />

      <div className="overlay-content">
        {view === 'transcript' && (
          <TranscriptPanel segments={segments} />
        )}
        {view === 'suggestions' && (
          <SuggestionPanel suggestions={suggestions} />
        )}
        {view === 'chat' && (
          <QuickChat
            transcript={segments}
            onSuggestion={(s) => setSuggestions(prev => [s, ...prev])}
          />
        )}
      </div>
    </div>
  )
}
