import { useState, useRef, useCallback, useEffect } from 'react'

type SpeechRecognitionType = typeof window.SpeechRecognition

function getSpeechRecognition(): SpeechRecognitionType | null {
  // Fix 1.4 & 2.4: Detect BOTH standard and webkit SpeechRecognition
  if (typeof window === 'undefined') return null
  return (
    (window as any).SpeechRecognition ||
    (window as any).webkitSpeechRecognition ||
    null
  )
}

export function useAudio() {
  const [isRecording, setIsRecording] = useState(false)
  // Fix 2.1: Track speech API availability
  const [isSpeechSupported, setIsSpeechSupported] = useState(false)
  // Fix 2.2 & 2.3: User-visible error/status messages
  const [speechError, setSpeechError] = useState<string | null>(null)
  const recognitionRef = useRef<InstanceType<SpeechRecognitionType> | null>(null)
  const mediaRecorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])
  const transcriptRef = useRef<string>('')

  useEffect(() => {
    // Fix 2.1: Check availability on mount
    const SpeechRec = getSpeechRecognition()
    setIsSpeechSupported(SpeechRec !== null)
  }, [])

  const startRecording = useCallback(async () => {
    setSpeechError(null)

    const SpeechRec = getSpeechRecognition()
    if (!SpeechRec) {
      // Fix 2.2: Show user-friendly message when unavailable
      setSpeechError('Voice input not supported in this browser. Please type your answer or try Chrome/Edge.')
      return
    }

    try {
      // Start media recorder for audio blob
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorder.current = new MediaRecorder(stream)
      chunks.current = []

      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data)
      }
      mediaRecorder.current.start()

      // Start speech recognition for live transcription
      const recognition = new SpeechRec()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-US'
      transcriptRef.current = ''

      recognition.onresult = (event: any) => {
        let transcript = ''
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript
        }
        transcriptRef.current = transcript
      }

      // Fix 2.3: On speech error, display user-friendly message and auto-stop
      recognition.onerror = (event: any) => {
        const errorMessages: Record<string, string> = {
          'not-allowed': 'Microphone permission denied. Please allow microphone access in your browser settings.',
          'no-speech': 'No speech detected. Please try speaking again.',
          'network': 'Network error during speech recognition. Please check your connection.',
          'audio-capture': 'No microphone found. Please connect a microphone and try again.',
          'aborted': 'Speech recognition was interrupted. Please try again.',
        }
        const message = errorMessages[event.error] || `Speech recognition error: ${event.error}`
        setSpeechError(message)
        // Auto-stop recording on error
        stopRecordingInternal()
      }

      recognition.onend = () => {
        // Only update state if we haven't already stopped
        if (isRecording) {
          setIsRecording(false)
        }
      }

      recognitionRef.current = recognition
      recognition.start()
      setIsRecording(true)
    } catch (err) {
      // Fix 2.3: User-friendly error for getUserMedia failures
      setSpeechError('Could not access microphone. Please check browser permissions.')
      console.error('Audio recording failed:', err)
    }
  }, [isRecording])

  const stopRecordingInternal = useCallback(() => {
    // Stop speech recognition
    if (recognitionRef.current) {
      try { recognitionRef.current.stop() } catch { /* ignore */ }
      recognitionRef.current = null
    }
    // Stop media recorder and clean up tracks
    if (mediaRecorder.current && mediaRecorder.current.state !== 'inactive') {
      try { mediaRecorder.current.stop() } catch { /* ignore */ }
      mediaRecorder.current?.stream.getTracks().forEach(t => t.stop())
    }
    setIsRecording(false)
  }, [])

  const stopRecording = useCallback((): Promise<{ blob: Blob; transcript: string }> => {
    return new Promise((resolve) => {
      // Stop speech recognition
      if (recognitionRef.current) {
        try { recognitionRef.current.stop() } catch { /* ignore */ }
        recognitionRef.current = null
      }

      if (!mediaRecorder.current || mediaRecorder.current.state === 'inactive') {
        resolve({ blob: new Blob(), transcript: transcriptRef.current })
        setIsRecording(false)
        return
      }

      mediaRecorder.current.onstop = () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' })
        mediaRecorder.current?.stream.getTracks().forEach(t => t.stop())
        resolve({ blob, transcript: transcriptRef.current })
      }
      mediaRecorder.current.stop()
      setIsRecording(false)
    })
  }, [])

  const clearError = useCallback(() => {
    setSpeechError(null)
  }, [])

  return {
    isRecording,
    isSpeechSupported,
    speechError,
    startRecording,
    stopRecording,
    clearError,
  }
}
