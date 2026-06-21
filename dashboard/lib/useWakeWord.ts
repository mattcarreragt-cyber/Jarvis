'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Détection du mot d'activation « Hey Jarvis » via l'API Web Speech
 * (SpeechRecognition). Écoute en continu ; déclenche onWake() quand « jarvis »
 * est entendu. MVP webapp — pour une écoute en arrière-plan/écran éteint,
 * voir l'app Android native (Porcupine), cf. docs/MOBILE_ANDROID.md.
 *
 * Supporté sur Chrome / Edge / Chrome Android. Sinon `supported` = false.
 */

type SR = typeof window extends { webkitSpeechRecognition: infer T } ? T : unknown

function getSR(): any {
  if (typeof window === 'undefined') return null
  return (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition || null
}

const WAKE = /\b(hey\s+)?(jarvis|jarviss|jarvise)\b/i

export function useWakeWord(onWake: () => void) {
  const [supported, setSupported] = useState(false)
  const [listening, setListening] = useState(false)
  const recRef = useRef<any>(null)
  const wantRef = useRef(false)
  const onWakeRef = useRef(onWake)
  onWakeRef.current = onWake

  useEffect(() => { setSupported(!!getSR()) }, [])

  const start = useCallback(() => {
    const SRClass = getSR()
    if (!SRClass) return
    wantRef.current = true
    if (recRef.current) return
    const rec = new SRClass()
    rec.continuous = true
    rec.interimResults = true
    rec.lang = 'fr-FR'
    rec.onresult = (e: any) => {
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const txt = e.results[i][0].transcript as string
        if (WAKE.test(txt)) {
          onWakeRef.current()
          break
        }
      }
    }
    rec.onend = () => {
      recRef.current = null
      setListening(false)
      // redémarre tant que l'utilisateur veut l'écoute (le moteur s'arrête seul périodiquement)
      if (wantRef.current) {
        try { start() } catch { /* ignore */ }
      }
    }
    rec.onerror = () => { /* onend gère le redémarrage */ }
    try {
      rec.start()
      recRef.current = rec
      setListening(true)
    } catch { /* déjà démarré */ }
  }, [])

  const stop = useCallback(() => {
    wantRef.current = false
    const rec = recRef.current
    recRef.current = null
    setListening(false)
    if (rec) { try { rec.stop() } catch { /* ignore */ } }
  }, [])

  useEffect(() => () => stop(), [stop])

  return { supported, listening, start, stop }
}
