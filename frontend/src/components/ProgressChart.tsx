import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface ProgressData {
  session_number: number
  score: number
}

interface ProgressChartProps {
  data: ProgressData[]
}

export default function ProgressChart({ data }: ProgressChartProps) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500 text-sm">
        No session data yet. Complete interviews to see progress.
      </div>
    )
  }

  const chartData = data.map(d => ({
    ...d,
    score: Math.round((d.score || 0) * 100),
  }))

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          dataKey="session_number"
          stroke="#64748b"
          fontSize={12}
          label={{ value: 'Session', position: 'insideBottom', offset: -5, fill: '#64748b' }}
        />
        <YAxis
          stroke="#64748b"
          fontSize={12}
          domain={[0, 100]}
          label={{ value: 'Score %', angle: -90, position: 'insideLeft', fill: '#64748b' }}
        />
        <Tooltip
          contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
          labelStyle={{ color: '#94a3b8' }}
        />
        <Line
          type="monotone"
          dataKey="score"
          stroke="#6366f1"
          strokeWidth={2}
          dot={{ fill: '#6366f1', r: 4 }}
          activeDot={{ r: 6, fill: '#818cf8' }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
