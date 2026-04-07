interface Props {
  activeView: 'transcript' | 'suggestions' | 'chat'
  onViewChange: (view: 'transcript' | 'suggestions' | 'chat') => void
  isRecording: boolean
  onToggleRecording: () => void
  onScreenshot: () => void
}

export default function OverlayControls({
  activeView,
  onViewChange,
  isRecording,
  onToggleRecording,
  onScreenshot,
}: Props) {
  return (
    <div className="overlay-controls">
      <div className="control-tabs">
        <button
          className={`tab-btn ${activeView === 'transcript' ? 'tab-active' : ''}`}
          onClick={() => onViewChange('transcript')}
          title="Live transcript"
        >
          Transcript
        </button>
        <button
          className={`tab-btn ${activeView === 'suggestions' ? 'tab-active' : ''}`}
          onClick={() => onViewChange('suggestions')}
          title="AI suggestions"
        >
          Hints
        </button>
        <button
          className={`tab-btn ${activeView === 'chat' ? 'tab-active' : ''}`}
          onClick={() => onViewChange('chat')}
          title="Ask AI (Cmd+Enter)"
        >
          Ask
        </button>
      </div>

      <div className="control-actions">
        <button
          className={`action-btn ${isRecording ? 'recording' : ''}`}
          onClick={onToggleRecording}
          title={isRecording ? 'Stop recording (Cmd+Shift+Space)' : 'Start recording (Cmd+Shift+Space)'}
        >
          {isRecording ? '⏹' : '⏺'}
        </button>
        <button
          className="action-btn"
          onClick={onScreenshot}
          title="Take screenshot (Cmd+H)"
        >
          📷
        </button>
      </div>
    </div>
  )
}
