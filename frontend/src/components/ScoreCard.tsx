import clsx from 'clsx'

interface ScoreCardProps {
  label: string
  score: number
  subtitle?: string
  size?: 'sm' | 'lg'
}

export default function ScoreCard({ label, score, subtitle, size = 'sm' }: ScoreCardProps) {
  const pct = Math.round(score * 100)
  const r = size === 'lg' ? 45 : 32
  const circumference = 2 * Math.PI * r
  const offset = circumference - (score * circumference)
  const color = score >= 0.7 ? '#10b981' : score >= 0.4 ? '#f59e0b' : '#ef4444'

  return (
    <div className="flex flex-col items-center">
      <svg width={r * 2 + 16} height={r * 2 + 16} className="transform -rotate-90">
        <circle
          cx={r + 8} cy={r + 8} r={r}
          fill="none" stroke="#334155" strokeWidth={size === 'lg' ? 6 : 4}
        />
        <circle
          cx={r + 8} cy={r + 8} r={r}
          fill="none" stroke={color} strokeWidth={size === 'lg' ? 6 : 4}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="score-ring"
        />
      </svg>
      <div className={clsx(
        'absolute flex flex-col items-center justify-center',
        size === 'lg' ? 'w-24 h-24' : 'w-16 h-16'
      )}>
        <span className={clsx('font-bold', size === 'lg' ? 'text-2xl' : 'text-lg')} style={{ color }}>
          {pct}%
        </span>
      </div>
      <p className="text-sm font-medium text-gray-300 mt-2">{label}</p>
      {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
    </div>
  )
}
