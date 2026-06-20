'use client'

import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, XCircle } from 'lucide-react'
import { apiUrl } from '@/lib/api'
import VideoArtifact from './VideoArtifact'

export interface ConfirmationData {
  request_id: string
  tool: string
  args: Record<string, unknown>
  summary: string
}

export interface ImageArtifact {
  kind: string
  name: string
  url: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent?: string
  confirmation?: ConfirmationData
  confirmResolved?: boolean
  artifacts?: ImageArtifact[]
}

interface Props {
  messages: Message[]
  loading: boolean
  onConfirm?: (requestId: string, confirmed: boolean, msgId: string) => void
}

export default function ChatPanel({ messages, loading, onConfirm }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  if (messages.length === 0 && !loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--text-dim)] text-xs tracking-widest">
        SYSTÈMES EN LIGNE — EN ATTENTE DE COMMANDE
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
      <AnimatePresence initial={false}>
        {messages.map(msg => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] px-3 py-2 rounded text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'panel text-[var(--text)] border-[rgba(0,212,255,0.3)]'
                  : 'text-[var(--cyan)]'
              }`}
              style={msg.role === 'assistant' ? {
                textShadow: '0 0 6px rgba(0,212,255,0.3)',
              } : {}}
            >
              {msg.role === 'assistant' && (
                <span className="text-[var(--text-dim)] text-[10px] tracking-widest block mb-1">
                  {msg.agent ? `[${msg.agent.toUpperCase()}]` : '[JARVIS]'}
                </span>
              )}
              <span className="whitespace-pre-wrap">{msg.content}</span>

              {/* Media artifacts */}
              {msg.artifacts?.map((a, i) =>
                a.kind === 'image' ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    key={i}
                    src={apiUrl(a.url)}
                    alt={a.name}
                    className="mt-2 rounded-lg border border-[rgba(0,212,255,0.25)] max-w-full"
                    style={{ maxHeight: 420 }}
                  />
                ) : a.kind === 'video_job' ? (
                  <VideoArtifact key={i} statusUrl={a.url} />
                ) : null
              )}

              {/* Confirmation buttons */}
              {msg.confirmation && !msg.confirmResolved && onConfirm && (
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => onConfirm(msg.confirmation!.request_id, true, msg.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] tracking-widest
                               border border-[var(--cyan)] text-[var(--cyan)] rounded
                               hover:bg-[rgba(0,212,255,0.1)] transition-colors"
                  >
                    <CheckCircle size={12} />
                    CONFIRMER
                  </button>
                  <button
                    onClick={() => onConfirm(msg.confirmation!.request_id, false, msg.id)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] tracking-widest
                               border border-red-500/50 text-red-400 rounded
                               hover:bg-red-500/10 transition-colors"
                  >
                    <XCircle size={12} />
                    ANNULER
                  </button>
                </div>
              )}
              {msg.confirmation && msg.confirmResolved && (
                <span className="block mt-2 text-[10px] text-[var(--text-dim)] tracking-widest">
                  — action traitée —
                </span>
              )}
            </div>
          </motion.div>
        ))}

        {loading && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex justify-start"
          >
            <div className="text-[var(--cyan)] text-sm px-3 py-2">
              <span className="text-[var(--text-dim)] text-[10px] tracking-widest block mb-1">[JARVIS]</span>
              <span className="inline-flex gap-1">
                {[0, 1, 2].map(i => (
                  <motion.span
                    key={i}
                    animate={{ opacity: [0.2, 1, 0.2] }}
                    transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.3 }}
                    className="w-1.5 h-1.5 rounded-full bg-[var(--cyan)] inline-block"
                  />
                ))}
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <div ref={bottomRef} />
    </div>
  )
}
