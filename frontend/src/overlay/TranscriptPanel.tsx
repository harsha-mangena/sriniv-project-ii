import { useEffect, useRef } from 'react'
import type { TranscriptSegment } from './OverlayApp'

interface Props {
  segments: TranscriptSegment[]
}

export default function TranscriptPanel({ segments }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new segments
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [segments.length])

  if (segments.length === 0) {
    return (
      <div className="overlay-empty">
        <p className="text-gray-500 text-xs">Waiting for audio...</p>
        <p className="text-gray-600 text-xs mt-1">
          Press Cmd+Shift+Space to start recording
        </p>
      </div>
    )
  }

  // Group consecutive segments by speaker
  const grouped: Array<{ speaker: string; texts: string[]; timestamp: number }> = []
  for (const seg of segments) {
    const last = grouped[grouped.length - 1]
    if (last && last.speaker === seg.speaker) {
      last.texts.push(seg.text)
    } else {
      grouped.push({
        speaker: seg.speaker,
        texts: [seg.text],
        timestamp: seg.timestamp_ms,
      })
    }
  }

  return (
    <div className="overlay-panel transcript-panel">
      {grouped.map((group, i) => (
        <div
          key={`${group.timestamp}-${i}`}
          className={`transcript-group ${group.speaker === 'user' ? 'speaker-user' : 'speaker-interviewer'}`}
        >
          <div className="transcript-speaker">
            <span className={`speaker-dot ${group.speaker === 'user' ? 'dot-green' : 'dot-blue'}`} />
            <span className="speaker-label">
              {group.speaker === 'user' ? 'You' : 'Interviewer'}
            </span>
          </div>
          <p className="transcript-text">{group.texts.join(' ')}</p>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
