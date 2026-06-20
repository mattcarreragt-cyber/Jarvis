'use client'

import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent?: string
}

interface Props {
  messages: Message[]
  loading: boolean
}

export default function ChatPanel({ messages, loading }: Props) {
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
