import { useState, useCallback } from 'react'
import { Upload, FileText, Check } from 'lucide-react'
import clsx from 'clsx'

interface FileUploadProps {
  label: string
  onTextSubmit: (text: string) => void | Promise<void>
  loading?: boolean
  success?: boolean
}

export default function FileUpload({ label, onTextSubmit, loading, success }: FileUploadProps) {
  const [text, setText] = useState('')
  const [dragActive, setDragActive] = useState(false)

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true)
    else if (e.type === 'dragleave') setDragActive(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    const file = e.dataTransfer.files?.[0]
    if (file && file.type === 'text/plain') {
      const reader = new FileReader()
      reader.onload = (ev) => setText(ev.target?.result as string)
      reader.readAsText(file)
    }
  }, [])

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium text-gray-300">{label}</label>
      <div
        className={clsx(
          'border-2 border-dashed rounded-xl p-4 transition-colors',
          dragActive ? 'border-accent bg-accent/5' : 'border-navy-600',
          success && 'border-emerald-500/50 bg-emerald-500/5'
        )}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        {success ? (
          <div className="flex items-center gap-2 text-emerald-400">
            <Check size={18} /> Uploaded successfully
          </div>
        ) : (
          <div className="flex items-center gap-2 text-gray-500 mb-3">
            <Upload size={16} />
            <span className="text-sm">Paste text or drag a file here</span>
          </div>
        )}
        <textarea
          className="input w-full h-32 resize-none text-sm"
          placeholder={`Paste your ${label.toLowerCase()} text here...`}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </div>
      <button
        className="btn-primary w-full flex items-center justify-center gap-2"
        onClick={() => onTextSubmit(text)}
        disabled={!text.trim() || loading}
      >
        {loading ? (
          <span className="animate-pulse">Processing...</span>
        ) : (
          <>
            <FileText size={16} />
            Upload & Parse
          </>
        )}
      </button>
    </div>
  )
}
