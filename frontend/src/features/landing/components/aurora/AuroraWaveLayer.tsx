import { gradId } from './AuroraDefs'

export interface AuroraWaveLayerProps {
  uid: string
}

/**
 * Full-bleed multi-radial mesh aura — airy pastel densities.
 */
export default function AuroraWaveLayer({ uid }: AuroraWaveLayerProps) {
  const g = (name: string) => gradId(uid, name)

  return (
    <div className="hero-aurora-wave-bleed" aria-hidden="true">
      <svg
        className="hero-aurora-layer hero-aurora-layer--waves"
        viewBox="0 0 1440 720"
        preserveAspectRatio="xMidYMid slice"
        xmlns="http://www.w3.org/2000/svg"
      >
        <AuroraWaveDefs uid={uid} />

        <g className="hero-flow-parallax-aurora aurora-wave-mesh">
          <ellipse
            className="aurora-wave-blob aurora-wave aurora-wave--3"
            cx="120"
            cy="280"
            rx="520"
            ry="340"
            fill={`url(#${g('radial-left')})`}
            opacity="0.7"
            filter={`url(#${g('blur-deep')})`}
          />

          <ellipse
            className="aurora-wave-blob aurora-wave aurora-wave--2"
            cx="520"
            cy="480"
            rx="480"
            ry="300"
            fill={`url(#${g('radial-center-left')})`}
            opacity="0.72"
            filter={`url(#${g('blur-mid')})`}
          />

          <path
            className="aurora-wave-blob aurora-wave aurora-wave--2"
            fill={`url(#${g('wave-core')})`}
            opacity="0.75"
            filter={`url(#${g('blur-mid')})`}
            d="M-120 160
               C 100 140, 260 240, 400 380
               C 540 520, 660 620, 820 600
               C 980 580, 1100 440, 1240 260
               C 1340 140, 1420 40, 1580 -40
               L 1580 180
               C 1400 260, 1280 400, 1140 500
               C 980 620, 820 660, 660 620
               C 500 580, 380 460, 240 320
               C 100 180, -20 140, -120 150 Z"
          />

          <ellipse
            className="aurora-wave-blob aurora-wave aurora-wave--1"
            cx="1040"
            cy="320"
            rx="420"
            ry="360"
            fill={`url(#${g('radial-center-right')})`}
            opacity="0.76"
            filter={`url(#${g('blur-soft')})`}
          />

          <ellipse
            className="aurora-wave-blob aurora-wave aurora-wave--1"
            cx="1380"
            cy="120"
            rx="380"
            ry="320"
            fill={`url(#${g('radial-right')})`}
            opacity="0.78"
            filter={`url(#${g('blur-soft')})`}
          />
        </g>
      </svg>
    </div>
  )
}

function AuroraWaveDefs({ uid }: { uid: string }) {
  const g = (name: string) => gradId(uid, name)
  return (
    <defs>
      <radialGradient id={g('radial-left')} cx="35%" cy="45%" r="70%">
        <stop offset="0%" stopColor="#E9D5FF" stopOpacity="0.6" />
        <stop offset="45%" stopColor="#E0E7FF" stopOpacity="0.5" />
        <stop offset="100%" stopColor="#E0E7FF" stopOpacity="0" />
      </radialGradient>

      <radialGradient id={g('radial-center-left')} cx="45%" cy="55%" r="65%">
        <stop offset="0%" stopColor="#7DD3FC" stopOpacity="0.65" />
        <stop offset="40%" stopColor="#93C5FD" stopOpacity="0.55" />
        <stop offset="100%" stopColor="#38BDF8" stopOpacity="0" />
      </radialGradient>

      {/* Softer amethyst — airy, not heavy */}
      <radialGradient id={g('radial-center-right')} cx="50%" cy="45%" r="70%">
        <stop offset="0%" stopColor="#C084FC" stopOpacity="0.72" />
        <stop offset="45%" stopColor="#A78BFA" stopOpacity="0.65" />
        <stop offset="100%" stopColor="#A78BFA" stopOpacity="0" />
      </radialGradient>

      <radialGradient id={g('radial-right')} cx="60%" cy="35%" r="75%">
        <stop offset="0%" stopColor="#A78BFA" stopOpacity="0.75" />
        <stop offset="40%" stopColor="#818CF8" stopOpacity="0.68" />
        <stop offset="100%" stopColor="#818CF8" stopOpacity="0" />
      </radialGradient>

      <linearGradient id={g('wave-core')} x1="0%" y1="50%" x2="100%" y2="20%">
        <stop offset="0%" stopColor="#E0E7FF" stopOpacity="0.6" />
        <stop offset="28%" stopColor="#7DD3FC" stopOpacity="0.62" />
        <stop offset="55%" stopColor="#C084FC" stopOpacity="0.7" />
        <stop offset="78%" stopColor="#A78BFA" stopOpacity="0.72" />
        <stop offset="100%" stopColor="#818CF8" stopOpacity="0.68" />
      </linearGradient>

      <filter id={g('blur-soft')} x="-35%" y="-35%" width="170%" height="170%">
        <feGaussianBlur stdDeviation="42" />
      </filter>
      <filter id={g('blur-mid')} x="-40%" y="-40%" width="180%" height="180%">
        <feGaussianBlur stdDeviation="52" />
      </filter>
      <filter id={g('blur-deep')} x="-45%" y="-45%" width="190%" height="190%">
        <feGaussianBlur stdDeviation="60" />
      </filter>
    </defs>
  )
}
