'use client'

import { useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Clapperboard, X, ImagePlus, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { animateImage } from '@/lib/api'

interface Props { onClose: () => void; onLaunched?: () => void }

type State = 'idle' | 'uploading' | 'success' | 'error'

export default function AnimatePanel({ onClose, onLaunched }: Props) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [state, setState] = useState<State>('idle')
  const [message, setMsg] = useState('')
  const [seconds, setSeconds] = useState(5)
  const [preview, setPreview] = useState<string>('')

  const pick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setPreview(URL.createObjectURL(f))
    setState('uploading'); setMsg('')
    try {
      await animateImage(f, seconds)
      setState('success')
      setMsg('Animation lancée — suis-la dans le panneau Jobs 🎬')
      onLaunched?.()
    } catch (err) {
      setState('error')
      setMsg(err instanceof Error ? err.message : 'Échec')
    }
  }

  return (
    <motion.div
      className="absolute inset-0 z-20 flex flex-col panel"
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }} transition={{ duration: 0.2 }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(0,212,255,0.15)]">
        <div className="flex items-center gap-2">
          <Clapperboard size={14} className="text-[var(--cyan)]" />
          <span className="text-xs tracking-widest text-[var(--cyan)] glow-sm">IMAGE → VIDÉO</span>
        </div>
        <button onClick={onClose} className="text-[var(--text-dim)] hover:text-[var(--cyan)]">
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 flex flex-col gap-4 px-6 py-5">
        <div>
          <label className="text-[10px] tracking-widest text-[var(--text-dim)] block mb-1">
            DURÉE : {seconds}s
          </label>
          <input type="range" min={2} max={10} value={seconds}
            onChange={e => setSeconds(Number(e.target.value))}
            className="w-full accent-[var(--cyan)]" disabled={state === 'uploading'} />
        </div>

        <button
          onClick={() => fileRef.current?.click()}
          disabled={state === 'uploading'}
          className="flex-1 flex flex-col items-center justify-center gap-3 border border-dashed
                     border-[rgba(0,212,255,0.3)] rounded-lg hover:border-[var(--cyan)]
                     hover:bg-[rgba(0,212,255,0.03)] transition-colors disabled:opacity-50 min-h-[140px]"
        >
          {preview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt="preview" className="max-h-28 rounded" />
          ) : (
            <ImagePlus size={28} className="text-[var(--text-dim)]" />
          )}
          <span className="text-xs tracking-widest text-[var(--text-dim)]">
            {state === 'uploading' ? 'ENVOI…' : 'CHOISIR UNE IMAGE À ANIMER'}
          </span>
          <span className="text-[10px] text-[var(--text-dim)] opacity-60">.png · .jpg</span>
        </button>
        <input ref={fileRef} type="file" accept=".png,.jpg,.jpeg,.webp" className="hidden" onChange={pick} />

        <AnimatePresence>
          {state !== 'idle' && message && (
            <motion.div
              initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className={`flex items-start gap-2 text-xs px-3 py-2 rounded ${
                state === 'success' ? 'text-[var(--cyan)] bg-[rgba(0,212,255,0.08)]'
                : 'text-red-400 bg-[rgba(239,68,68,0.08)]'}`}
            >
              {state === 'uploading' ? <Loader2 size={14} className="mt-0.5 animate-spin" />
                : state === 'success' ? <CheckCircle size={14} className="mt-0.5 shrink-0" />
                : <AlertCircle size={14} className="mt-0.5 shrink-0" />}
              <span>{message}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}
