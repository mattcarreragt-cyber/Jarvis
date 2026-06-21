'use client'

import { useState, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { History, Upload, Cloud, Volume2, VolumeX, Film, Brain, Clapperboard, Bell, LayoutGrid, SlidersHorizontal } from 'lucide-react'
import JarvisOrb, { OrbState } from '@/components/JarvisOrb'
import ChatPanel, { Message, ConfirmationData } from '@/components/ChatPanel'
import ChatInput from '@/components/ChatInput'
import StatusBar from '@/components/StatusBar'
import HistoryPanel from '@/components/HistoryPanel'
import DocUpload from '@/components/DocUpload'
import NextcloudPanel from '@/components/NextcloudPanel'
import JobsPanel from '@/components/JobsPanel'
import MemoryPanel from '@/components/MemoryPanel'
import AnimatePanel from '@/components/AnimatePanel'
import AgendaPanel from '@/components/AgendaPanel'
import GalleryPanel from '@/components/GalleryPanel'
import SystemPanel from '@/components/SystemPanel'
import { apiFetch, transcribeAudio, speak, fetchNotifications } from '@/lib/api'
import { useVoiceRecorder } from '@/lib/useVoiceRecorder'

let msgCounter = 0
const uid = () => `msg-${++msgCounter}`
const SESSION_ID = typeof crypto !== 'undefined'
  ? crypto.randomUUID()
  : `session-${Date.now()}`

export default function Home() {
  const [messages, setMessages]     = useState<Message[]>([])
  const [orbState, setOrbState]     = useState<OrbState>('idle')
  const [loading, setLoading]       = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [showUpload, setShowUpload]   = useState(false)
  const [showCloud, setShowCloud]     = useState(false)
  const [showJobs, setShowJobs]       = useState(false)
  const [showMemory, setShowMemory]   = useState(false)
  const [showAnimate, setShowAnimate] = useState(false)
  const [showAgenda, setShowAgenda]   = useState(false)
  const [showGallery, setShowGallery] = useState(false)
  const [showSystem, setShowSystem]   = useState(false)
  const [unread, setUnread]           = useState(0)
  const [voiceOut, setVoiceOut]       = useState(false)

  const closePanels = useCallback(() => {
    setShowUpload(false); setShowCloud(false); setShowHistory(false)
    setShowJobs(false); setShowMemory(false); setShowAnimate(false)
    setShowAgenda(false); setShowGallery(false); setShowSystem(false)
  }, [])

  useEffect(() => {
    const poll = () => fetchNotifications().then(n => setUnread(n.unread)).catch(() => {})
    poll()
    const id = setInterval(poll, 15000)
    return () => clearInterval(id)
  }, [])

  const recorder = useVoiceRecorder()

  const addMsg = useCallback((msg: Omit<Message, 'id'>) =>
    setMessages(prev => [...prev, { ...msg, id: uid() }]), [])

  const playTTS = useCallback(async (text: string) => {
    const url = await speak(text)
    if (url) { try { await new Audio(url).play() } catch { /* lecture refusée */ } }
  }, [])

  const sendMessage = useCallback(async (text: string) => {
    if (loading) return
    addMsg({ role: 'user', content: text })
    setLoading(true)
    setOrbState('thinking')
    try {
      const res  = await apiFetch('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ session_id: SESSION_ID, message: text }),
      })
      const data = await res.json()
      setOrbState('speaking')
      addMsg({
        role: 'assistant',
        content: data.content || '…',
        agent: data.agent,
        confirmation: data.status === 'needs_confirmation' ? data.confirmation as ConfirmationData : undefined,
        artifacts: data.artifacts,
      })
      if (voiceOut && data.content) playTTS(data.content)
      setTimeout(() => setOrbState('idle'), 1500)
    } catch {
      addMsg({ role: 'assistant', content: 'Erreur de connexion à l\'API.', agent: 'system' })
      setOrbState('idle')
    } finally {
      setLoading(false)
    }
  }, [loading, addMsg, voiceOut, playTTS])

  const toggleVoice = useCallback(async () => {
    if (recorder.isRecording) {
      // Fin d'enregistrement → transcription → envoi
      setIsListening(false)
      setOrbState('thinking')
      const blob = await recorder.stop()
      if (!blob) { setOrbState('idle'); return }
      try {
        const text = await transcribeAudio(blob)
        if (text) await sendMessage(text)
        else setOrbState('idle')
      } catch {
        addMsg({ role: 'assistant', content: 'Transcription indisponible (Kubuntu éteint ?).', agent: 'system' })
        setOrbState('idle')
      }
    } else {
      const ok = await recorder.start()
      if (ok) { setIsListening(true); setOrbState('listening') }
      else addMsg({ role: 'assistant', content: 'Micro inaccessible (permission refusée ?).', agent: 'system' })
    }
  }, [recorder, sendMessage, addMsg])

  const handleConfirm = useCallback(async (requestId: string, confirmed: boolean, msgId: string) => {
    setMessages(prev => prev.map(m => m.id === msgId ? { ...m, confirmResolved: true } : m))
    try {
      const res = await apiFetch(`/api/chat/confirm?request_id=${requestId}&confirmed=${confirmed}`, { method: 'POST' })
      const data = await res.json()
      addMsg({ role: 'assistant', content: data.content || '…', agent: data.agent })
    } catch {
      addMsg({ role: 'assistant', content: 'Erreur lors de la confirmation.', agent: 'system' })
    }
  }, [addMsg])

  const restoreSession = useCallback((msgs: Omit<Message, 'id'>[]) => {
    setMessages(msgs.map(m => ({ ...m, id: uid() })))
  }, [])

  return (
    <div
      className="relative h-full w-full flex overflow-hidden"
      style={{ background: 'radial-gradient(ellipse at center, #041420 0%, #020d14 70%)' }}
    >
      {/* Grid background */}
      <div
        className="absolute inset-0 opacity-[0.04] pointer-events-none"
        style={{
          backgroundImage: 'linear-gradient(var(--cyan) 1px, transparent 1px), linear-gradient(90deg, var(--cyan) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      {/* ── Left — Orb ──────────────────────────────── */}
      <div className="relative flex flex-col items-center justify-center w-[420px] shrink-0 z-10">
        <div className="absolute top-6 left-0 right-0 flex justify-between px-8 text-[9px] tracking-[3px] text-[var(--text-dim)] hud-flicker">
          <span>SYS.ONLINE</span><span>v0.1.0</span>
        </div>

        {/* Brackets */}
        {[
          'absolute top-4 left-4 w-12 h-12 border-l border-t border-[rgba(0,212,255,0.3)]',
          'absolute top-4 right-4 w-12 h-12 border-r border-t border-[rgba(0,212,255,0.3)]',
          'absolute bottom-4 left-4 w-12 h-12 border-l border-b border-[rgba(0,212,255,0.3)]',
          'absolute bottom-4 right-4 w-12 h-12 border-r border-b border-[rgba(0,212,255,0.3)]',
        ].map((cls, i) => (
          <motion.div key={i} className={cls}
            animate={{ opacity: [0.4, 0.8, 0.4] }}
            transition={{ duration: 3, repeat: Infinity, delay: i * 0.75 }}
          />
        ))}

        <JarvisOrb state={orbState} onClick={toggleVoice} />
        <p className="mt-4 text-[10px] tracking-widest text-[var(--text-dim)]">
          {isListening ? 'CLIQUER POUR ARRÊTER' : 'CLIQUER = ACTIVER MIC'}
        </p>

        <div className="absolute bottom-6 left-0 right-0 flex justify-between px-8 text-[9px] tracking-[3px] text-[var(--text-dim)]">
          <span>MÉMOIRE: OK</span><span>LOCAL-FIRST</span>
        </div>
      </div>

      {/* Separator */}
      <div className="w-px self-stretch my-8 shrink-0"
        style={{ background: 'linear-gradient(to bottom, transparent, rgba(0,212,255,0.25) 30%, rgba(0,212,255,0.25) 70%, transparent)' }}
      />

      {/* ── Right — Chat ─────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 z-10 relative">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[rgba(0,212,255,0.1)]">
          <div>
            <p className="text-xs tracking-[4px] text-[var(--cyan)] glow-sm">INTERFACE TEXTUELLE</p>
            <p className="text-[10px] text-[var(--text-dim)] tracking-widest mt-0.5">
              SESSION · {SESSION_ID.slice(0, 8).toUpperCase()}
            </p>
          </div>
          <div className="flex items-center gap-4">
            {/* Notifications / agenda */}
            <button
              onClick={() => { const n = !showAgenda; closePanels(); setShowAgenda(n); if (n) setUnread(0) }}
              title="Agenda & notifications"
              className={`relative p-1.5 rounded transition-colors ${
                showAgenda
                  ? 'text-[var(--cyan)] bg-[rgba(0,212,255,0.1)]'
                  : 'text-[var(--text-dim)] hover:text-[var(--cyan)]'
              }`}
            >
              <Bell size={16} />
              {unread > 0 && (
                <span className="absolute -top-0.5 -right-0.5 min-w-[14px] h-[14px] px-1 rounded-full
                                 bg-[var(--cyan)] text-[#02131a] text-[9px] font-bold flex items-center justify-center">
                  {unread > 9 ? '9+' : unread}
                </span>
              )}
            </button>
            {/* Voix sortie (TTS auto) */}
            <button
              onClick={() => setVoiceOut(v => !v)}
              title={voiceOut ? 'Couper la voix' : 'Activer la lecture vocale'}
              className={`p-1.5 rounded transition-colors ${
                voiceOut
                  ? 'text-[var(--cyan)] bg-[rgba(0,212,255,0.1)]'
                  : 'text-[var(--text-dim)] hover:text-[var(--cyan)]'
              }`}
            >
              {voiceOut ? <Volume2 size={16} /> : <VolumeX size={16} />}
            </button>
            {/* Upload doc */}
            <button
              onClick={() => { const n = !showUpload; closePanels(); setShowUpload(n) }}
              title="Ingérer un document"
              className={`p-1.5 rounded transition-colors ${
                showUpload
                  ? 'text-[var(--cyan)] bg-[rgba(0,212,255,0.1)]'
                  : 'text-[var(--text-dim)] hover:text-[var(--cyan)]'
              }`}
            >
              <Upload size={16} />
            </button>
            {/* Nextcloud */}
            <button
              onClick={() => { const n = !showCloud; closePanels(); setShowCloud(n) }}
              title="Nextcloud — RAG local"
              className={`p-1.5 rounded transition-colors ${
                showCloud
                  ? 'text-[var(--cyan)] bg-[rgba(0,212,255,0.1)]'
                  : 'text-[var(--text-dim)] hover:text-[var(--cyan)]'
              }`}
            >
              <Cloud size={16} />
            </button>
            {/* Jobs (générations) */}
            <button
              onClick={() => { const n = !showJobs; closePanels(); setShowJobs(n) }}
              title="Jobs de génération (vidéo)"
              className={`p-1.5 rounded transition-colors ${
                showJobs
                  ? 'text-[var(--cyan)] bg-[rgba(0,212,255,0.1)]'
                  : 'text-[var(--text-dim)] hover:text-[var(--cyan)]'
              }`}
            >
              <Film size={16} />
            </button>
            {/* Image → vidéo */}
            <button
              onClick={() => { const n = !showAnimate; closePanels(); setShowAnimate(n) }}
              title="Animer une image (image → vidéo)"
              className={`p-1.5 rounded transition-colors ${
                showAnimate
                  ? 'text-[var(--cyan)] bg-[rgba(0,212,255,0.1)]'
                  : 'text-[var(--text-dim)] hover:text-[var(--cyan)]'
              }`}
            >
              <Clapperboard size={16} />
            </button>
            {/* Galerie média */}
            <button
              onClick={() => { const n = !showGallery; closePanels(); setShowGallery(n) }}
              title="Galerie média"
              className={`p-1.5 rounded transition-colors ${
                showGallery
                  ? 'text-[var(--cyan)] bg-[rgba(0,212,255,0.1)]'
                  : 'text-[var(--text-dim)] hover:text-[var(--cyan)]'
              }`}
            >
              <LayoutGrid size={16} />
            </button>
            {/* Système */}
            <button
              onClick={() => { const n = !showSystem; closePanels(); setShowSystem(n) }}
              title="Système & paliers"
              className={`p-1.5 rounded transition-colors ${
                showSystem
                  ? 'text-[var(--cyan)] bg-[rgba(0,212,255,0.1)]'
                  : 'text-[var(--text-dim)] hover:text-[var(--cyan)]'
              }`}
            >
              <SlidersHorizontal size={16} />
            </button>
            {/* Memory */}
            <button
              onClick={() => { const n = !showMemory; closePanels(); setShowMemory(n) }}
              title="Mémoire long terme"
              className={`p-1.5 rounded transition-colors ${
                showMemory
                  ? 'text-[var(--cyan)] bg-[rgba(0,212,255,0.1)]'
                  : 'text-[var(--text-dim)] hover:text-[var(--cyan)]'
              }`}
            >
              <Brain size={16} />
            </button>
            {/* History button */}
            <button
              onClick={() => { const n = !showHistory; closePanels(); setShowHistory(n) }}
              title="Historique des sessions"
              className={`p-1.5 rounded transition-colors ${
                showHistory
                  ? 'text-[var(--cyan)] bg-[rgba(0,212,255,0.1)]'
                  : 'text-[var(--text-dim)] hover:text-[var(--cyan)]'
              }`}
            >
              <History size={16} />
            </button>
            {/* Online dot */}
            <div className="flex items-center gap-2">
              <motion.div className="w-2 h-2 rounded-full bg-[var(--cyan)]"
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
              <span className="text-[10px] tracking-widest text-[var(--text-dim)]">EN LIGNE</span>
            </div>
          </div>
        </div>

        {/* Chat or History */}
        <div className="flex-1 relative min-h-0 flex flex-col">
          <ChatPanel messages={messages} loading={loading} onConfirm={handleConfirm} />

          <AnimatePresence>
            {showHistory && (
              <HistoryPanel
                onRestore={restoreSession}
                onClose={() => setShowHistory(false)}
              />
            )}
            {showUpload && (
              <DocUpload onClose={() => setShowUpload(false)} />
            )}
            {showCloud && (
              <NextcloudPanel onClose={() => setShowCloud(false)} />
            )}
            {showJobs && (
              <JobsPanel onClose={() => setShowJobs(false)} />
            )}
            {showMemory && (
              <MemoryPanel onClose={() => setShowMemory(false)} />
            )}
            {showAnimate && (
              <AnimatePanel
                onClose={() => setShowAnimate(false)}
                onLaunched={() => { setShowAnimate(false); setShowJobs(true) }}
              />
            )}
            {showAgenda && (
              <AgendaPanel onClose={() => setShowAgenda(false)} />
            )}
            {showGallery && (
              <GalleryPanel onClose={() => setShowGallery(false)} />
            )}
            {showSystem && (
              <SystemPanel onClose={() => setShowSystem(false)} />
            )}
          </AnimatePresence>
        </div>

        <ChatInput onSend={sendMessage} onVoiceToggle={toggleVoice}
                   isListening={isListening} disabled={loading} />
        <StatusBar />
      </div>
    </div>
  )
}
