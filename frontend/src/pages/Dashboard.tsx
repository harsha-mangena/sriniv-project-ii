import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MessageSquare, BookOpen, BarChart3, Upload, CheckCircle2 } from 'lucide-react'
import FileUpload from '../components/FileUpload'
import { useProfileStore } from '../stores/profileStore'
import { uploadDocument } from '../services/documentService'

export default function Dashboard() {
  const navigate = useNavigate()
  const profile = useProfileStore()
  const [resumeLoading, setResumeLoading] = useState(false)
  const [jdLoading, setJdLoading] = useState(false)

  const handleResumeUpload = async (text: string) => {
    setResumeLoading(true)
    try {
      const doc = await uploadDocument(text, 'resume')
      profile.setResume(doc.id, doc.parsed_data)
    } catch (e) {
      console.error(e)
    } finally {
      setResumeLoading(false)
    }
  }

  const handleJDUpload = async (text: string) => {
    setJdLoading(true)
    try {
      const doc = await uploadDocument(text, 'job_description')
      profile.setJD(doc.id, doc.parsed_data)
    } catch (e) {
      console.error(e)
    } finally {
      setJdLoading(false)
    }
  }

  const canStart = profile.resumeId && profile.jdId

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-white">Dashboard</h2>
        <p className="text-gray-400 mt-1">Upload your resume and job description to get started.</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <FileUpload
          label="Resume"
          onTextSubmit={handleResumeUpload}
          loading={resumeLoading}
          success={!!profile.resumeId}
        />
        <FileUpload
          label="Job Description"
          onTextSubmit={handleJDUpload}
          loading={jdLoading}
          success={!!profile.jdId}
        />
      </div>

      {profile.resumeParsed && (
        <div className="card">
          <h3 className="text-sm font-medium text-gray-400 mb-2">Parsed Resume</h3>
          <div className="flex flex-wrap gap-2">
            {Object.values((profile.resumeParsed as Record<string, unknown>)?.skills || {}).flat().filter(Boolean).map((skill, i) => (
              <span key={i} className="badge badge-blue">{String(skill)}</span>
            ))}
          </div>
        </div>
      )}

      {canStart && (
        <div className="card bg-accent/5 border-accent/30">
          <div className="flex items-center gap-2 text-accent mb-4">
            <CheckCircle2 size={18} />
            <span className="font-medium">Ready to start</span>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <button className="btn-primary flex items-center justify-center gap-2" onClick={() => navigate('/mock')}>
              <MessageSquare size={16} /> Mock Interview
            </button>
            <button className="btn-secondary flex items-center justify-center gap-2" onClick={() => navigate('/prep')}>
              <BookOpen size={16} /> Prep Mode
            </button>
            <button className="btn-secondary flex items-center justify-center gap-2" onClick={() => navigate('/analytics')}>
              <BarChart3 size={16} /> Analytics
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
