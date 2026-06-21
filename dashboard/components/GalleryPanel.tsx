'use client'

import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { LayoutGrid, X, Trash2, Download, Film } from 'lucide-react'
import { fetchMedia, deleteMedia, apiUrl, MediaAsset } from '@/lib/api'

interface Props { onClose: () => void }

export default function GalleryPanel({ onClose }: Props) {
  const [assets, setAssets] = useState<MediaAsset[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setAssets(await fetchMedia())
    setLoading(false)
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 10000)   // capte les nouveaux rendus
    return () => clearInterval(id)
  }, [load])

  const remove = async (id: string) => {
    if (await deleteMedia(id)) setAssets(a => a.filter(x => x.id !== id))
  }

  return (
    <motion.div
      className="absolute inset-0 z-20 flex flex-col panel"
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }} transition={{ duration: 0.2 }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(0,212,255,0.15)]">
        <div className="flex items-center gap-2">
          <LayoutGrid size={14} className="text-[var(--cyan)]" />
          <span className="text-xs tracking-widest text-[var(--cyan)] glow-sm">GALERIE MÉDIA</span>
        </div>
        <button onClick={onClose} className="text-[var(--text-dim)] hover:text-[var(--cyan)]">
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {loading ? (
          <p className="text-xs text-[var(--text-dim)] tracking-widest">CHARGEMENT…</p>
        ) : assets.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-2 text-center text-[var(--text-dim)]">
            <LayoutGrid size={28} />
            <p className="text-xs">Aucun média généré.</p>
            <p className="text-[10px] opacity-60">Tes images et vidéos apparaîtront ici.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {assets.map(a => (
              <div key={a.id}
                className="group relative border border-[rgba(0,212,255,0.15)] rounded overflow-hidden">
                {a.kind === 'image' ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={apiUrl(a.view_url)} alt={a.prompt || ''}
                    className="w-full h-32 object-cover" />
                ) : (
                  <video src={apiUrl(a.view_url)} muted loop
                    className="w-full h-32 object-cover"
                    onMouseEnter={e => e.currentTarget.play()}
                    onMouseLeave={e => e.currentTarget.pause()} />
                )}
                {a.kind === 'video' && (
                  <Film size={12} className="absolute top-1 left-1 text-white drop-shadow" />
                )}
                {/* Overlay actions */}
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity
                                flex flex-col justify-between p-2">
                  <p className="text-[9px] text-white line-clamp-3">{a.prompt}</p>
                  <div className="flex justify-end gap-2">
                    <a href={apiUrl(a.view_url)} download
                      className="p-1 rounded bg-[rgba(0,212,255,0.2)] text-[var(--cyan)] hover:bg-[rgba(0,212,255,0.4)]">
                      <Download size={12} />
                    </a>
                    <button onClick={() => remove(a.id)}
                      className="p-1 rounded bg-[rgba(239,68,68,0.2)] text-red-300 hover:bg-[rgba(239,68,68,0.4)]">
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}
