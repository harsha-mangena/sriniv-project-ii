import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import MockInterview from './pages/MockInterview'
import PrepMode from './pages/PrepMode'
import Analytics from './pages/Analytics'
import RealTimeAssist from './pages/RealTimeAssist'
import Settings from './pages/Settings'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/mock" element={<MockInterview />} />
        <Route path="/prep" element={<PrepMode />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/realtime" element={<RealTimeAssist />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  )
}
