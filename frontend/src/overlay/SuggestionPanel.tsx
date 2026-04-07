import type { Suggestion } from './OverlayApp'

interface Props {
  suggestions: Suggestion[]
}

export default function SuggestionPanel({ suggestions }: Props) {
  if (suggestions.length === 0) {
    return (
      <div className="overlay-empty">
        <p className="text-gray-500 text-xs">No suggestions yet</p>
        <p className="text-gray-600 text-xs mt-1">
          Suggestions appear when questions are detected
        </p>
      </div>
    )
  }

  return (
    <div className="overlay-panel suggestion-panel">
      {suggestions.map((suggestion, i) => (
        <div key={i} className="suggestion-card">
          {suggestion.question && (
            <div className="suggestion-question">
              <span className="question-icon">?</span>
              <span>{suggestion.question}</span>
            </div>
          )}
          <div className="suggestion-text">
            {suggestion.text.split('\n').map((line, j) => {
              const trimmed = line.trim()
              if (!trimmed) return null

              // Render bullet points
              if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
                return (
                  <div key={j} className="suggestion-bullet">
                    <span className="bullet">•</span>
                    <span>{trimmed.slice(2)}</span>
                  </div>
                )
              }

              return <p key={j} className="suggestion-line">{trimmed}</p>
            })}
          </div>
          <div className="suggestion-meta">
            <span className="confidence-badge">
              {Math.round(suggestion.confidence * 100)}% confidence
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}
