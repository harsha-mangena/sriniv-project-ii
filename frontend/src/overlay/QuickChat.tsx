import { useState, useRef, useEffect } from 'react'
import type { TranscriptSegment, Suggestion } from './OverlayApp'

interface Props {
  transcript: TranscriptSegment[]
  onSuggestion: (suggestion: Suggestion) => void
}

export default function QuickChat({ transcript, onSuggestion }: Props) {
  const [input, setInput] = useState('')
  const [response, setResponse] = useState('')
  const [loading, setLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // Focus input on mount and when triggered by Cmd+Enter
  useEffect(() => {
    inputRef.current?.focus()

    const tauri = window.__TAURI__
    if (!tauri) return

    let unlisten: (() => void) | undefined
    tauri.event.listen('focus-chat-input', () => {
      inputRef.current?.focus()
    }).then(fn => { unlisten = fn })

    return () => unlisten?.()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const tauri = window.__TAURI__
    if (!tauri) return

    setLoading(true)
    setResponse('')

    try {
      const result = await tauri.core.invoke('send_chat_message', {
        message: input.trim(),
      }) as string

      setResponse(result)

      // Also push to suggestions
      onSuggestion({
        text: result,
        confidence: 0.9,
        question: input.trim(),
      })
    } catch (e: any) {
      setResponse(`Error: ${e?.message || e}`)
    } finally {
      setLoading(false)
    }
  }

  const quickPrompts = [
    'What should I say?',
    'Summarize the question',
    'Give me key points to mention',
  ]

  return (
    <div className="overlay-panel chat-panel">
      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          ref={inputRef}
          type="text"
          className="chat-input"
          placeholder="What should I say?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="chat-submit"
          disabled={!input.trim() || loading}
        >
          {loading ? '...' : '→'}
        </button>
      </form>

      <div className="quick-prompts">
        {quickPrompts.map((prompt) => (
          <button
            key={prompt}
            className="quick-prompt-btn"
            onClick={() => {
              setInput(prompt)
              inputRef.current?.focus()
            }}
          >
            {prompt}
          </button>
        ))}
      </div>

      {response && (
        <div className="chat-response">
          {response.split('\n').map((line, i) => {
            const trimmed = line.trim()
            if (!trimmed) return null
            if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
              return (
                <div key={i} className="suggestion-bullet">
                  <span className="bullet">•</span>
                  <span>{trimmed.slice(2)}</span>
                </div>
              )
            }
            return <p key={i} className="chat-line">{trimmed}</p>
          })}
        </div>
      )}

      {transcript.length > 0 && (
        <div className="chat-context">
          <p className="context-label">Recent context ({transcript.length} segments)</p>
        </div>
      )}
    </div>
  )
}
