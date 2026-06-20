'use client'

import { useRef, useState, useCallback } from 'react'

/**
 * Enregistrement micro via MediaRecorder.
 * start() démarre la capture ; stop() renvoie le blob audio (webm/opus).
 */
export function useVoiceRecorder() {
  const [isRecording, setIsRecording] = useState(false)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)

  const start = useCallback(async (): Promise<boolean> => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices) return false
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const rec = new MediaRecorder(stream)
      chunksRef.current = []
      rec.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      rec.start()
      recorderRef.current = rec
      setIsRecording(true)
      return true
    } catch {
      return false
    }
  }, [])

  const stop = useCallback((): Promise<Blob | null> => {
    return new Promise(resolve => {
      const rec = recorderRef.current
      if (!rec) { resolve(null); return }
      rec.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        streamRef.current?.getTracks().forEach(t => t.stop())
        streamRef.current = null
        recorderRef.current = null
        setIsRecording(false)
        resolve(blob.size > 0 ? blob : null)
      }
      rec.stop()
    })
  }, [])

  return { isRecording, start, stop }
}
