import { useState, useEffect } from 'react'

interface Props {
  isRecording: boolean
  connected: boolean
  segmentCount: number
}

export default function StatusBar({ isRecording, connected, segmentCount }: Props) {
  const [elapsed, setElapsed] = useState(0)

  // Timer for recording duration
  useEffect(() => {
    if (!isRecording) {
      setElapsed(0)
      return
    }

    const start = Date.now()
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000))
    }, 1000)

    return () => clearInterval(interval)
  }, [isRecording])

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  return (
    <div className="status-bar">
      <div className="status-left">
        <span className={`status-dot ${isRecording ? 'recording-dot' : 'idle-dot'}`} />
        <span className="status-text">
          {isRecording ? `Recording ${formatTime(elapsed)}` : 'Idle'}
        </span>
      </div>

      <div className="status-right">
        <span className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? '●' : '○'}
        </span>
        {segmentCount > 0 && (
          <span className="segment-count">{segmentCount} segments</span>
        )}
      </div>
    </div>
  )
}
