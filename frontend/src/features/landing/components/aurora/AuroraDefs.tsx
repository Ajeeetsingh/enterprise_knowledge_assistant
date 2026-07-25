export interface AuroraDefsProps {
  uid: string
  layer: 'waves' | 'network'
}

export function gradId(uid: string, name: string) {
  return `${name}-${uid}`
}

export default function AuroraDefs({ uid, layer }: AuroraDefsProps) {
  const g = (name: string) => gradId(uid, name)

  if (layer === 'waves') {
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

  return (
    <defs>
      <linearGradient
        id={g('trail')}
        gradientUnits="userSpaceOnUse"
        x1="0"
        y1="0"
        x2="1440"
        y2="0"
      >
        <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0" />
        <stop offset="15%" stopColor="#FFFFFF" stopOpacity="0.9" />
        <stop offset="50%" stopColor="#EFF6FF" stopOpacity="0.95" />
        <stop offset="85%" stopColor="#FFFFFF" stopOpacity="0.9" />
        <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0" />
      </linearGradient>
      <filter id={g('line-glow')} x="-25%" y="-25%" width="150%" height="150%">
        <feDropShadow dx="0" dy="0" stdDeviation="2" floodColor="#FFFFFF" floodOpacity="0.85" />
        <feDropShadow dx="0" dy="0" stdDeviation="4.5" floodColor="#A78BFA" floodOpacity="0.5" />
      </filter>
      <filter id={g('node-glow')} x="-90%" y="-90%" width="280%" height="280%">
        <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#FFFFFF" floodOpacity="0.95" />
        <feDropShadow dx="0" dy="0" stdDeviation="5" floodColor="#A78BFA" floodOpacity="0.55" />
      </filter>
    </defs>
  )
}
