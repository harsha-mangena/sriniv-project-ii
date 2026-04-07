import { useState, useRef, useEffect } from 'react'
import { Send, Mic, MicOff, StopCircle, ArrowRight, AlertCircle } from 'lucide-react'
import ChatBubble from '../components/ChatBubble'
import { useInterview } from '../hooks/useInterview'
import { useAudio } from '../hooks/useAudio'
import { useProfileStore } from '../stores/profileStore'

export default function MockInterview() {
  const profile = useProfileStore()
  const interview = useInterview()
  const audio = useAudio()
  const [input, setInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [interview.messages])

  const handleStart = async () => {
    if (!profile.resumeId || !profile.jdId) return
    setError(null)
    try {
      await interview.start(profile.resumeId, profile.jdId)
    } catch (err: any) {
      setError(err?.message || 'Failed to start interview. Please try again.')
    }
  }

  const handleSend = async () => {
    if (!input.trim() || interview.isLoading) return
    const text = input.trim()
    setInput('')
    setError(null)
    try {
      await interview.answer(text)
    } catch (err: any) {
      // Fix 2.17: Handle error responses, clear "Evaluating..." state
      setError(err?.message || 'Failed to evaluate answer. Please try again.')
    }
  }

  const handleNext = async () => {
    setError(null)
    try {
      await interview.next()
    } catch (err: any) {
      setError(err?.message || 'Failed to get next question.')
    }
  }

  const handleEnd = async () => {
    setError(null)
    try {
      const result = await interview.end()
      if (result) {
        interview.addMessage({
          role: 'ai',
          text: `Interview complete! Final score: ${((result as Record<string, number>).overall_score * 100).toFixed(0)}%`,
        })
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to end interview.')
    }
  }

  // Fix 2.1/2.3: Handle mic toggle with speech recognition
  const handleMicToggle = async () => {
    if (audio.isRecording) {
      const result = await audio.stopRecording()
      if (result.transcript) {
        setInput(prev => prev ? `${prev} ${result.transcript}` : result.transcript)
      }
    } else {
      audio.clearError()
      await audio.startRecording()
    }
  }

  if (!interview.isActive) {
    return (
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-bold text-white mb-4">Mock Interview</h2>
        {!profile.resumeId || !profile.jdId ? (
          <div className="card text-center">
            <p className="text-gray-400">Upload your resume and job description on the Dashboard first.</p>
          </div>
        ) : (
          <div className="card text-center space-y-4">
            <p className="text-gray-300">Ready to start a mock interview session?</p>
            <p className="text-sm text-gray-500">
              The AI will ask questions based on your resume and the job description,
              evaluate your answers atom-by-atom, and adapt difficulty in real time.
            </p>
            <button className="btn-primary" onClick={handleStart} disabled={interview.isLoading}>
              {interview.isLoading ? 'Starting...' : 'Start Interview'}
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-white">Mock Interview</h2>
          {interview.currentCategory && (
            <div className="flex items-center gap-2 mt-1">
              <span className="badge badge-purple">{interview.currentCategory}</span>
              <span className="text-xs text-gray-500">Difficulty: {'★'.repeat(interview.currentDifficulty)}</span>
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary text-sm" onClick={handleNext}>
            <ArrowRight size={14} className="mr-1 inline" /> Next Question
          </button>
          <button className="bg-red-500/20 text-red-400 px-4 py-2 rounded-lg text-sm hover:bg-red-500/30 transition-colors" onClick={handleEnd}>
            <StopCircle size={14} className="mr-1 inline" /> End
          </button>
        </div>
      </div>

      {/* Fix 2.3/2.17: Display user-facing error messages */}
      {(error || audio.speechError) && (
        <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-2 rounded-lg mb-3">
          <AlertCircle size={16} className="shrink-0" />
          <span>{error || audio.speechError}</span>
          <button
            className="ml-auto text-red-400 hover:text-red-300"
            onClick={() => { setError(null); audio.clearError() }}
          >
            &times;
          </button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-2 mb-4 pr-2">
        {interview.messages.map((msg, i) => (
          <ChatBubble key={i} {...msg} />
        ))}
        {interview.isLoading && (
          <div className="flex items-center gap-2 text-gray-500 text-sm">
            <div className="animate-pulse flex gap-1">
              <span className="w-2 h-2 bg-accent rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-accent rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-accent rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
            Evaluating...
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <div className="flex gap-2 border-t border-navy-700 pt-4">
        <textarea
          className="input flex-1 resize-none h-20"
          placeholder="Type your answer here..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
        />
        <div className="flex flex-col gap-2">
          <button className="btn-primary h-full" onClick={handleSend} disabled={!input.trim() || interview.isLoading}>
            <Send size={16} />
          </button>
          {/* Fix 2.1/2.4: Mic button disabled/hidden when API unavailable */}
          <button
            className={`px-3 py-2 rounded-lg text-sm transition-colors ${
              audio.isRecording
                ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                : audio.isSpeechSupported
                  ? 'bg-navy-700 text-gray-300 hover:bg-navy-600'
                  : 'bg-navy-800 text-gray-600 cursor-not-allowed'
            }`}
            onClick={handleMicToggle}
            disabled={!audio.isSpeechSupported || interview.isLoading}
            title={
              !audio.isSpeechSupported
                ? 'Voice input not supported in this browser. Please type your answer or try Chrome/Edge.'
                : audio.isRecording ? 'Stop recording' : 'Start voice input'
            }
          >
            {audio.isRecording ? <MicOff size={16} /> : <Mic size={16} />}
          </button>
        </div>
      </div>

      {/* Fix 2.2: Show unsupported message below mic */}
      {!audio.isSpeechSupported && (
        <p className="text-xs text-gray-600 mt-1 text-right">
          Voice input not supported in this browser. Please type your answer or try Chrome/Edge.
        </p>
      )}
    </div>
  )
}
