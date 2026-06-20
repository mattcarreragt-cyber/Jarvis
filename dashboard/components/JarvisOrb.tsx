'use client'

import { motion, AnimatePresence } from 'framer-motion'

export type OrbState = 'idle' | 'listening' | 'thinking' | 'speaking'

const STATE_COLORS: Record<OrbState, string> = {
  idle:      '#00d4ff',
  listening: '#00ffcc',
  thinking:  '#aa88ff',
  speaking:  '#00d4ff',
}

const STATE_LABELS: Record<OrbState, string> = {
  idle:      'EN ATTENTE',
  listening: 'ÉCOUTE...',
  thinking:  'TRAITEMENT...',
  speaking:  'RÉPOND...',
}

interface Props {
  state: OrbState
  onClick?: () => void
}

export default function JarvisOrb({ state, onClick }: Props) {
  const color = STATE_COLORS[state]
  const label = STATE_LABELS[state]

  return (
    <div
      className={`relative flex items-center justify-center select-none state-${state}`}
      style={{ width: 320, height: 320 }}
      onClick={onClick}
    >
      {/* ── Glow backdrop ─────────────────────────── */}
      <motion.div
        className="absolute inset-0 rounded-full"
        animate={{ scale: state === 'listening' ? [1, 1.15, 1] : [1, 1.04, 1] }}
        transition={{ duration: state === 'listening' ? 0.7 : 3, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          background: `radial-gradient(circle, ${color}18 0%, ${color}06 50%, transparent 70%)`,
          filter: 'blur(20px)',
        }}
      />

      {/* ── SVG rings ─────────────────────────────── */}
      <svg
        viewBox="0 0 320 320"
        width={320}
        height={320}
        className="absolute"
        style={{ overflow: 'visible' }}
      >
        {/* Outer dashed ring */}
        <g className="ring-slow" style={{ transformOrigin: '160px 160px' }}>
          <circle
            cx="160" cy="160" r="145"
            fill="none"
            stroke={color}
            strokeWidth="1"
            strokeOpacity="0.3"
            strokeDasharray="4 8"
          />
          {/* Corner markers */}
          {[0, 60, 120, 180, 240, 300].map(deg => (
            <rect
              key={deg}
              x="157" y="13"
              width="6" height="6"
              fill={color}
              fillOpacity="0.7"
              transform={`rotate(${deg} 160 160)`}
            />
          ))}
        </g>

        {/* Middle ring */}
        <g className="ring-medium" style={{ transformOrigin: '160px 160px' }}>
          <circle
            cx="160" cy="160" r="118"
            fill="none"
            stroke={color}
            strokeWidth="1.5"
            strokeOpacity="0.25"
            strokeDasharray="60 20 10 20"
          />
        </g>

        {/* Thinking arc — visible only when thinking */}
        {state === 'thinking' && (
          <motion.circle
            cx="160" cy="160" r="100"
            fill="none"
            stroke={color}
            strokeWidth="2"
            strokeOpacity="0.8"
            strokeDasharray="120 508"
            strokeLinecap="round"
            style={{ transformOrigin: '160px 160px', rotate: '-90deg' }}
            animate={{ strokeDashoffset: [-0, -628] }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          />
        )}

        {/* Inner spinning ring */}
        <g className="ring-fast" style={{ transformOrigin: '160px 160px' }}>
          <circle
            cx="160" cy="160" r="88"
            fill="none"
            stroke={color}
            strokeWidth="1"
            strokeOpacity="0.2"
            strokeDasharray="12 6"
          />
        </g>

        {/* HUD tick marks */}
        {Array.from({ length: 24 }, (_, i) => {
          const angle = (i * 15 * Math.PI) / 180
          const r1 = 74, r2 = i % 6 === 0 ? 68 : 71
          return (
            <line
              key={i}
              x1={160 + r1 * Math.sin(angle)} y1={160 - r1 * Math.cos(angle)}
              x2={160 + r2 * Math.sin(angle)} y2={160 - r2 * Math.cos(angle)}
              stroke={color}
              strokeWidth={i % 6 === 0 ? 2 : 1}
              strokeOpacity={i % 6 === 0 ? 0.7 : 0.3}
            />
          )
        })}

        {/* Core orb */}
        <motion.circle
          cx="160" cy="160" r="52"
          fill="none"
          stroke={color}
          strokeWidth="1.5"
          strokeOpacity="0.6"
          animate={{
            r: state === 'listening' ? [52, 58, 52] : [52, 54, 52],
            strokeOpacity: state === 'speaking' ? [0.6, 1, 0.6] : [0.5, 0.8, 0.5],
          }}
          transition={{ duration: state === 'listening' ? 0.6 : 2.5, repeat: Infinity, ease: 'easeInOut' }}
        />

        {/* Core fill */}
        <motion.circle
          cx="160" cy="160"
          r="38"
          animate={{
            fill: [
              `${color}18`,
              `${color}30`,
              `${color}18`,
            ],
          }}
          transition={{ duration: state === 'listening' ? 0.6 : 2.5, repeat: Infinity, ease: 'easeInOut' }}
        />

        {/* Center dot */}
        <motion.circle
          cx="160" cy="160" r="6"
          fill={color}
          animate={{ r: state === 'thinking' ? [6, 8, 6] : [5, 7, 5] }}
          transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
        />

        {/* J.A.R.V.I.S. label */}
        <text
          x="160" y="164"
          textAnchor="middle"
          dominantBaseline="middle"
          fill={color}
          fontSize="10"
          letterSpacing="4"
          fontFamily="'Courier New', monospace"
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        >
          J.A.R.V.I.S.
        </text>

        {/* State label arc */}
        <text
          x="160" y="198"
          textAnchor="middle"
          fill={color}
          fontSize="7"
          letterSpacing="3"
          fontFamily="'Courier New', monospace"
          fillOpacity="0.7"
        >
          {label}
        </text>

        {/* Decorative corner brackets */}
        {[
          { x: 30,  y: 30,  d: 'M 30 46 L 30 30 L 46 30'  },
          { x: 290, y: 30,  d: 'M 274 30 L 290 30 L 290 46' },
          { x: 30,  y: 290, d: 'M 30 274 L 30 290 L 46 290' },
          { x: 290, y: 290, d: 'M 274 290 L 290 290 L 290 274' },
        ].map((br, i) => (
          <path
            key={i}
            d={br.d}
            fill="none"
            stroke={color}
            strokeWidth="1.5"
            strokeOpacity="0.5"
            className="hud-flicker"
          />
        ))}
      </svg>

      {/* ── Listening wave bars ────────────────────── */}
      <AnimatePresence>
        {state === 'listening' && (
          <motion.div
            className="absolute bottom-10 flex gap-1 items-end"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            {[4, 8, 12, 8, 16, 10, 6, 14, 8, 4].map((h, i) => (
              <motion.div
                key={i}
                className="w-1 rounded-full"
                style={{ background: color }}
                animate={{ height: [h, h * 2, h] }}
                transition={{
                  duration: 0.5,
                  repeat: Infinity,
                  delay: i * 0.07,
                  ease: 'easeInOut',
                }}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
