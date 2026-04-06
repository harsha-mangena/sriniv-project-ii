import clsx from 'clsx'

interface SkillAtom {
  id: string
  label: string
  category: string
  score: number
  attempts: number
}

interface SkillHeatmapProps {
  atoms: SkillAtom[]
}

function getColor(score: number, attempts: number): string {
  if (attempts === 0) return 'bg-navy-700 text-gray-600'
  if (score >= 0.8) return 'bg-emerald-500/30 text-emerald-400'
  if (score >= 0.6) return 'bg-emerald-500/15 text-emerald-300'
  if (score >= 0.4) return 'bg-amber-500/20 text-amber-400'
  if (score >= 0.2) return 'bg-orange-500/20 text-orange-400'
  return 'bg-red-500/20 text-red-400'
}

export default function SkillHeatmap({ atoms }: SkillHeatmapProps) {
  const categories = Array.from(new Set(atoms.map(a => a.category)))

  return (
    <div className="space-y-4">
      {categories.map(cat => (
        <div key={cat}>
          <h4 className="text-sm font-medium text-gray-400 mb-2">{cat}</h4>
          <div className="flex flex-wrap gap-2">
            {atoms.filter(a => a.category === cat).map(atom => (
              <div
                key={atom.id}
                className={clsx(
                  'px-3 py-1.5 rounded-lg text-xs font-medium cursor-default transition-colors',
                  getColor(atom.score, atom.attempts)
                )}
                title={`${atom.label}: ${(atom.score * 100).toFixed(0)}% (${atom.attempts} attempts)`}
              >
                {atom.label}
                {atom.attempts > 0 && (
                  <span className="ml-1 opacity-70">{(atom.score * 100).toFixed(0)}%</span>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
