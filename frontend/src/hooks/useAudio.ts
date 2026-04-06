import { useState, useRef, useCallback } from 'react'

export function useAudio() {
  const [isRecording, setIsRecording] = useState(false)
  const mediaRecorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorder.current = new MediaRecorder(stream)
      chunks.current = []

      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data)
      }

      mediaRecorder.current.start()
      setIsRecording(true)
    } catch (err) {
      console.error('Audio recording failed:', err)
    }
  }, [])

  const stopRecording = useCallback((): Promise<Blob> => {
    return new Promise((resolve) => {
      if (!mediaRecorder.current) {
        resolve(new Blob())
        return
      }
      mediaRecorder.current.onstop = () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' })
        resolve(blob)
        // Clean up tracks
        mediaRecorder.current?.stream.getTracks().forEach(t => t.stop())
      }
      mediaRecorder.current.stop()
      setIsRecording(false)
    })
  }, [])

  return { isRecording, startRecording, stopRecording }
}
