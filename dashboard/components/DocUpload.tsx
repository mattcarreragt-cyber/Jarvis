'use client'

import { useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, X, FileText, CheckCircle, AlertCircle } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const KEY = process.env.NEXT_PUBLIC_API_KEY ?? ''

interface Props { onClose: () => void }

type State = 'idle' | 'uploading' | 'success' | 'error'

export default function DocUpload({ onClose }: Props) {
  const fileRef   = useRef<HTMLInputElement>(null)
  const [state, setState]   = useState<State>('idle')
  const [message, setMsg]   = useState('')
  const [tags, setTags]     = useState('xenum')
  const [kind, setKind]     = useState('doc')
  const [filename, setFilename] = useState('')

  const upload = async (file: File) => {
    setState('uploading')
    setMsg('')
    const form = new FormData()
    form.append('file', file)
    form.append('tags', tags)
    form.append('kind', kind)

    try {
      const headers: HeadersInit = KEY ? { 'X-API-Key': KEY } : {}
      const r = await fetch(`${API}/api/docs/ingest`, {
        method: 'POST', headers, body: form,
      })
      const data = await r.json()
      if (!r.ok) { setState('error'); setMsg(data.detail || 'Erreur'); return }
      setState('success')
      setMsg(`${data.chunks_count} extraits ingérés depuis "${data.source}"`)
    } catch (e) {
      setState('error')
      setMsg('Impossible de joindre l\'API')
    }
  }

  const pick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFilename(f.name)
    upload(f)
  }

  return (
    <motion.div
      className="absolute inset-0 z-20 flex flex-col panel"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ duration: 0.2 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(0,212,255,0.15)]">
        <div className="flex items-center gap-2">
          <Upload size={14} className="text-[var(--cyan)]" />
          <span className="text-xs tracking-widest text-[var(--cyan)] glow-sm">INGESTION DOCUMENT</span>
        </div>
        <button onClick={onClose} className="text-[var(--text-dim)] hover:text-[var(--cyan)]">
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 flex flex-col gap-4 px-6 py-5">

        {/* Tags */}
        <div>
          <label className="text-[10px] tracking-widest text-[var(--text-dim)] block mb-1">TAGS (CSV)</label>
          <input
            className="w-full bg-transparent border border-[rgba(0,212,255,0.2)] rounded px-3 py-1.5
                       text-sm text-[var(--text)] outline-none focus:border-[var(--cyan)]"
            value={tags}
            onChange={e => setTags(e.target.value)}
            placeholder="xenum, marketing, fiche-produit"
          />
        </div>

        {/* Kind */}
        <div>
          <label className="text-[10px] tracking-widest text-[var(--text-dim)] block mb-1">TYPE</label>
          <select
            className="w-full bg-[var(--bg-panel)] border border-[rgba(0,212,255,0.2)] rounded px-3 py-1.5
                       text-sm text-[var(--text)] outline-none focus:border-[var(--cyan)]"
            value={kind}
            onChange={e => setKind(e.target.value)}
          >
            <option value="doc">Document général</option>
            <option value="fiche">Fiche produit</option>
            <option value="brand">Brand guidelines</option>
            <option value="content">Contenu existant</option>
          </select>
        </div>

        {/* Drop zone */}
        <button
          onClick={() => fileRef.current?.click()}
          disabled={state === 'uploading'}
          className="flex-1 flex flex-col items-center justify-center gap-3 border
                     border-dashed border-[rgba(0,212,255,0.3)] rounded-lg
                     hover:border-[var(--cyan)] hover:bg-[rgba(0,212,255,0.03)]
                     transition-colors disabled:opacity-50 min-h-[120px]"
        >
          <FileText size={28} className="text-[var(--text-dim)]" />
          <span className="text-xs tracking-widest text-[var(--text-dim)]">
            {state === 'uploading' ? 'TRAITEMENT…' : 'CLIQUER POUR CHOISIR UN FICHIER'}
          </span>
          <span className="text-[10px] text-[var(--text-dim)] opacity-60">.txt · .md · .pdf · .docx · .xlsx · .pptx · images</span>
        </button>
        <input ref={fileRef} type="file"
               accept=".txt,.md,.pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.gif,.webp,.bmp"
               className="hidden" onChange={pick} />

        {/* Status */}
        <AnimatePresence>
          {state !== 'idle' && message && (
            <motion.div
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className={`flex items-start gap-2 text-xs px-3 py-2 rounded ${
                state === 'success'
                  ? 'text-[var(--cyan)] bg-[rgba(0,212,255,0.08)]'
                  : 'text-red-400 bg-[rgba(239,68,68,0.08)]'
              }`}
            >
              {state === 'success'
                ? <CheckCircle size={14} className="mt-0.5 shrink-0" />
                : <AlertCircle  size={14} className="mt-0.5 shrink-0" />
              }
              <span>{message}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {state === 'success' && (
          <button
            onClick={() => { setState('idle'); setMsg(''); setFilename('') }}
            className="text-[10px] tracking-widest text-[var(--text-dim)] hover:text-[var(--cyan)]"
          >
            INGÉRER UN AUTRE DOCUMENT
          </button>
        )}
      </div>
    </motion.div>
  )
}
