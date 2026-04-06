import { useState } from 'react'
import { BookOpen, ChevronDown, ChevronUp } from 'lucide-react'
import { useProfileStore } from '../stores/profileStore'
import { generatePrep, type PrepResponse } from '../services/interviewService'
import clsx from 'clsx'

export default function PrepMode() {
  const profile = useProfileStore()
  const [prepData, setPrepData] = useState<PrepResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const handleGenerate = async () => {
    if (!profile.resumeId || !profile.jdId) return
    setLoading(true)
    try {
      const result = await generatePrep(profile.resumeId, profile.jdId, 30)
      setPrepData(result)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const difficultyColor = (d: number) => {
    if (d <= 2) return 'badge-green'
    if (d <= 3) return 'badge-yellow'
    return 'badge-red'
  }

  if (!profile.resumeId || !profile.jdId) {
    return (
      <div className="max-w-4xl mx-auto">
        <h2 className="text-2xl font-bold text-white mb-4">Prep Mode</h2>
        <div className="card text-center">
          <p className="text-gray-400">Upload your resume and job description on the Dashboard first.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Prep Mode</h2>
          <p className="text-gray-400 mt-1">Generate personalized interview questions with model answers.</p>
        </div>
        <button className="btn-primary flex items-center gap-2" onClick={handleGenerate} disabled={loading}>
          <BookOpen size={16} />
          {loading ? 'Generating...' : prepData ? 'Regenerate' : 'Generate Questions'}
        </button>
      </div>

      {loading && (
        <div className="card text-center">
          <div className="animate-pulse text-gray-400">
            Generating personalized questions... This may take a minute.
          </div>
        </div>
      )}

      {prepData && (
        <>
          <div className="grid grid-cols-3 gap-4">
            <div className="card text-center">
              <p className="text-2xl font-bold text-accent">{prepData.total_generated}</p>
              <p className="text-sm text-gray-400">Questions Generated</p>
            </div>
            <div className="card text-center">
              <p className="text-2xl font-bold text-emerald-400">
                {(prepData.match_score as Record<string, number>)?.overall_score?.toFixed(0) || '—'}%
              </p>
              <p className="text-sm text-gray-400">Resume Match</p>
            </div>
            <div className="card text-center">
              <p className="text-2xl font-bold text-amber-400">
                {((prepData.weakness_analysis as Record<string, unknown[]>)?.weak_areas || []).length}
              </p>
              <p className="text-sm text-gray-400">Areas to Improve</p>
            </div>
          </div>

          <div className="space-y-3">
            {prepData.questions.map((q, i) => (
              <div key={i} className="card cursor-pointer" onClick={() => setExpandedId(expandedId === i ? null : i)}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={clsx('badge', difficultyColor(q.difficulty))}>{q.category}</span>
                      <span className="text-xs text-gray-500">{'★'.repeat(q.difficulty)}</span>
                    </div>
                    <p className="text-sm text-gray-200">{q.question}</p>
                  </div>
                  {expandedId === i ? <ChevronUp size={16} className="text-gray-500" /> : <ChevronDown size={16} className="text-gray-500" />}
                </div>
                {expandedId === i && (
                  <div className="mt-4 pt-4 border-t border-navy-700 space-y-3">
                    <div>
                      <p className="text-xs font-medium text-accent mb-1">Model Answer</p>
                      <p className="text-sm text-gray-300 whitespace-pre-wrap">{q.model_answer}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-emerald-400 mb-1">Talking Points</p>
                      <ul className="list-disc list-inside text-sm text-gray-400 space-y-1">
                        {q.talking_points.map((tp, j) => <li key={j}>{tp}</li>)}
                      </ul>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {q.target_skills.map((s, j) => (
                        <span key={j} className="badge badge-blue">{s}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
