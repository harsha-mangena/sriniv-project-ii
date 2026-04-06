import clsx from 'clsx'
import { Bot, User } from 'lucide-react'

interface ChatBubbleProps {
  role: 'ai' | 'user'
  text: string
  score?: number
  atoms?: { id: string; label: string; score: number }[]
}

export default function ChatBubble({ role, text, score, atoms }: ChatBubbleProps) {
  const isAI = role === 'ai'

  return (
    <div className={clsx('flex gap-3 mb-4', isAI ? 'flex-row' : 'flex-row-reverse')}>
      <div className={clsx(
        'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
        isAI ? 'bg-accent/20 text-accent' : 'bg-emerald-500/20 text-emerald-400'
      )}>
        {isAI ? <Bot size={16} /> : <User size={16} />}
      </div>
      <div className={clsx(
        'max-w-[75%] rounded-xl px-4 py-3',
        isAI ? 'bg-navy-700' : 'bg-accent/20'
      )}>
        <p className="text-sm text-gray-200 whitespace-pre-wrap">{text}</p>
        {score !== undefined && (
          <div className="mt-2 pt-2 border-t border-navy-600">
            <span className={clsx(
              'text-xs font-medium',
              score >= 0.7 ? 'text-emerald-400' : score >= 0.4 ? 'text-amber-400' : 'text-red-400'
            )}>
              Score: {(score * 100).toFixed(0)}%
            </span>
          </div>
        )}
        {atoms && atoms.length > 0 && (
          <div className="mt-2 pt-2 border-t border-navy-600 space-y-1">
            {atoms.map(a => (
              <div key={a.id} className="flex items-center justify-between text-xs">
                <span className="text-gray-400">{a.label}</span>
                <span className={clsx(
                  'font-medium',
                  a.score >= 0.7 ? 'text-emerald-400' : a.score >= 0.4 ? 'text-amber-400' : 'text-red-400'
                )}>
                  {(a.score * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
