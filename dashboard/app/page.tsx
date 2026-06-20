'use client'

import { useState, useCallback, useId } from 'react'
import { motion } from 'framer-motion'
import JarvisOrb, { OrbState } from '@/components/JarvisOrb'
import ChatPanel, { Message } from '@/components/ChatPanel'
import ChatInput from '@/components/ChatInput'
import StatusBar from '@/components/StatusBar'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

let msgCounter = 0
const uid = () => `msg-${++msgCounter}`
const SESSION_ID = typeof crypto !== 'undefined'
  ? crypto.randomUUID()
  : `session-${Date.now()}`

export default function Home() {
  const [messages, setMessages]   = useState<Message[]>([])
  const [orbState, setOrbState]   = useState<OrbState>('idle')
  const [loading, setLoading]     = useState(false)
  const [isListening, setIsListening] = useState(false)

  const addMsg = useCallback((msg: Omit<Message, 'id'>) => {
    setMessages(prev => [...prev, { ...msg, id: uid() }])
  }, [])

  const sendMessage = useCallback(async (text: string) => {
    if (loading) return
    addMsg({ role: 'user', content: text })
    setLoading(true)
    setOrbState('thinking')

    try {
      const res = await fetch(`${API}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: SESSION_ID, message: text }),
      })
      const data = await res.json()
      setOrbState('speaking')
      addMsg({ role: 'assistant', content: data.content || '…', agent: data.agent })
      setTimeout(() => setOrbState('idle'), 1500)
    } catch {
      addMsg({ role: 'assistant', content: 'Erreur de connexion à l\'API.', agent: 'system' })
      setOrbState('idle')
    } finally {
      setLoading(false)
    }
  }, [loading, addMsg])

  const toggleVoice = useCallback(() => {
    if (isListening) {
      setIsListening(false)
      setOrbState('idle')
    } else {
      setIsListening(true)
      setOrbState('listening')
      // STT sera branché ici (Faster-Whisper, étape 9)
    }
  }, [isListening])

  return (
    <div
      className="relative h-full w-full flex overflow-hidden"
      style={{ background: 'radial-gradient(ellipse at center, #041420 0%, #020d14 70%)' }}
    >
      {/* ── Grid background ─────────────────────────── */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: 'linear-gradient(var(--cyan) 1px, transparent 1px), linear-gradient(90deg, var(--cyan) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      {/* ── Left column — Orb ───────────────────────── */}
      <div className="relative flex flex-col items-center justify-center w-[420px] shrink-0 z-10">

        {/* Top HUD info */}
        <div className="absolute top-6 left-0 right-0 flex justify-between px-8 text-[9px] tracking-[3px] text-[var(--text-dim)] hud-flicker">
          <span>SYS.ONLINE</span>
          <span>v0.1.0</span>
        </div>

        {/* Corner decoration top-left */}
        <motion.div
          className="absolute top-4 left-4 w-12 h-12 border-l border-t border-[rgba(0,212,255,0.3)]"
          animate={{ opacity: [0.4, 0.8, 0.4] }}
          transition={{ duration: 3, repeat: Infinity }}
        />
        <motion.div
          className="absolute top-4 right-4 w-12 h-12 border-r border-t border-[rgba(0,212,255,0.3)]"
          animate={{ opacity: [0.4, 0.8, 0.4] }}
          transition={{ duration: 3, repeat: Infinity, delay: 1.5 }}
        />
        <motion.div
          className="absolute bottom-4 left-4 w-12 h-12 border-l border-b border-[rgba(0,212,255,0.3)]"
          animate={{ opacity: [0.4, 0.8, 0.4] }}
          transition={{ duration: 3, repeat: Infinity, delay: 0.75 }}
        />
        <motion.div
          className="absolute bottom-4 right-4 w-12 h-12 border-r border-b border-[rgba(0,212,255,0.3)]"
          animate={{ opacity: [0.4, 0.8, 0.4] }}
          transition={{ duration: 3, repeat: Infinity, delay: 2.25 }}
        />

        <JarvisOrb state={orbState} onClick={toggleVoice} />

        {/* Hint */}
        <p className="mt-4 text-[10px] tracking-widest text-[var(--text-dim)]">
          {isListening ? 'CLIQUEZ POUR ARRÊTER' : 'CLIQUER = ACTIVER MIC'}
        </p>

        {/* Bottom HUD info */}
        <div className="absolute bottom-6 left-0 right-0 flex justify-between px-8 text-[9px] tracking-[3px] text-[var(--text-dim)]">
          <span>MÉMOIRE: OK</span>
          <span>LOCAL-FIRST</span>
        </div>
      </div>

      {/* ── Separator ───────────────────────────────── */}
      <div
        className="w-px self-stretch my-8 shrink-0"
        style={{ background: 'linear-gradient(to bottom, transparent, rgba(0,212,255,0.25) 30%, rgba(0,212,255,0.25) 70%, transparent)' }}
      />

      {/* ── Right column — Chat ──────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 z-10">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[rgba(0,212,255,0.1)]">
          <div>
            <p className="text-xs tracking-[4px] text-[var(--cyan)] glow-sm">INTERFACE TEXTUELLE</p>
            <p className="text-[10px] text-[var(--text-dim)] tracking-widest mt-0.5">SESSION · {SESSION_ID.slice(0, 8).toUpperCase()}</p>
          </div>
          <div className="flex items-center gap-2">
            <motion.div
              className="w-2 h-2 rounded-full bg-[var(--cyan)]"
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            <span className="text-[10px] tracking-widest text-[var(--text-dim)]">EN LIGNE</span>
          </div>
        </div>

        {/* Messages */}
        <ChatPanel messages={messages} loading={loading} />

        {/* Input */}
        <ChatInput
          onSend={sendMessage}
          onVoiceToggle={toggleVoice}
          isListening={isListening}
          disabled={loading}
        />

        {/* Status */}
        <StatusBar />
      </div>
    </div>
  )
}
