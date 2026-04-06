import { useState, useEffect } from 'react'
import SkillHeatmap from '../components/SkillHeatmap'
import ProgressChart from '../components/ProgressChart'
import { api } from '../services/api'

interface AnalyticsData {
  total_sessions: number
  total_questions: number
  avg_score: number
  score_trend: { session_number: number; score: number }[]
  category_scores: Record<string, number>
  top_strengths: { category: string; score: number }[]
  top_weaknesses: { category: string; score: number }[]
  recommendations: string[]
}

interface HeatmapData {
  atoms: { id: string; label: string; category: string; cumulative_score: number; attempt_count: number }[]
}

export default function Analytics() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [heatmap, setHeatmap] = useState<HeatmapData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [profile, heat] = await Promise.all([
          api.get<AnalyticsData>('/analytics/profile'),
          api.get<HeatmapData>('/analytics/heatmap'),
        ])
        setAnalytics(profile)
        setHeatmap(heat)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto">
        <h2 className="text-2xl font-bold text-white mb-4">Analytics</h2>
        <div className="card text-center animate-pulse text-gray-500">Loading analytics...</div>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold text-white">Analytics</h2>

      <div className="grid grid-cols-4 gap-4">
        <div className="card text-center">
          <p className="text-2xl font-bold text-accent">{analytics?.total_sessions || 0}</p>
          <p className="text-sm text-gray-400">Sessions</p>
        </div>
        <div className="card text-center">
          <p className="text-2xl font-bold text-white">{analytics?.total_questions || 0}</p>
          <p className="text-sm text-gray-400">Questions</p>
        </div>
        <div className="card text-center">
          <p className="text-2xl font-bold text-emerald-400">
            {analytics?.avg_score ? (analytics.avg_score * 100).toFixed(0) : 0}%
          </p>
          <p className="text-sm text-gray-400">Avg Score</p>
        </div>
        <div className="card text-center">
          <p className="text-2xl font-bold text-amber-400">{analytics?.top_weaknesses?.length || 0}</p>
          <p className="text-sm text-gray-400">Weak Areas</p>
        </div>
      </div>

      <div className="card">
        <h3 className="text-sm font-medium text-gray-400 mb-4">Progress Over Time</h3>
        <ProgressChart data={analytics?.score_trend || []} />
      </div>

      <div className="card">
        <h3 className="text-sm font-medium text-gray-400 mb-4">Skill Heatmap</h3>
        {heatmap?.atoms?.length ? (
          <SkillHeatmap
            atoms={heatmap.atoms.map(a => ({
              id: a.id,
              label: a.label || a.id,
              category: a.category || 'General',
              score: a.cumulative_score || 0,
              attempts: a.attempt_count || 0,
            }))}
          />
        ) : (
          <p className="text-sm text-gray-500">Complete interviews to build your skill heatmap.</p>
        )}
      </div>

      {analytics?.recommendations && analytics.recommendations.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-medium text-gray-400 mb-3">Recommendations</h3>
          <ul className="space-y-2">
            {analytics.recommendations.map((r, i) => (
              <li key={i} className="text-sm text-gray-300 flex items-start gap-2">
                <span className="text-accent mt-0.5">→</span>
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
