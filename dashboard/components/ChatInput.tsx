'use client'

import { useState, useRef, KeyboardEvent } from 'react'
import { Mic, MicOff, Send } from 'lucide-react'

interface Props {
  onSend: (text: string) => void
  onVoiceToggle: () => void
  isListening: boolean
  disabled: boolean
}

export default function ChatInput({ onSend, onVoiceToggle, isListening, disabled }: Props) {
  const [value, setValue] = useState('')
  const ref = useRef<HTMLTextAreaElement>(null)

  const submit = () => {
    const text = value.trim()
    if (!text || disabled) return
    onSend(text)
    setValue('')
    ref.current?.focus()
  }

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="flex items-end gap-2 p-3 panel mx-4 mb-4">
      {/* Textarea */}
      <textarea
        ref={ref}
        className="flex-1 resize-none bg-transparent outline-none text-sm text-[var(--text)]
                   placeholder-[var(--text-dim)] leading-relaxed min-h-[36px] max-h-32"
        placeholder="Commande ou question..."
        value={value}
        onChange={e => setValue(e.target.value)}
        onKeyDown={onKey}
        rows={1}
        disabled={disabled}
      />

      {/* Voice toggle */}
      <button
        onClick={onVoiceToggle}
        title={isListening ? 'Arrêter l\'écoute' : 'Parler à JARVIS'}
        className={`p-2 rounded transition-all ${
          isListening
            ? 'text-[#00ffcc] glow-sm bg-[rgba(0,255,200,0.1)]'
            : 'text-[var(--text-dim)] hover:text-[var(--cyan)]'
        }`}
      >
        {isListening ? <MicOff size={18} /> : <Mic size={18} />}
      </button>

      {/* Send */}
      <button
        onClick={submit}
        disabled={!value.trim() || disabled}
        className="p-2 rounded text-[var(--cyan)] hover:text-white disabled:opacity-30
                   disabled:cursor-not-allowed transition-colors"
      >
        <Send size={18} />
      </button>
    </div>
  )
}
