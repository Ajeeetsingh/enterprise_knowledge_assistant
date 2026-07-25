import { cn } from '@/utils/cn'

import { gradId } from './AuroraDefs'

export interface AuroraNetworkLayerProps {
  uid: string
  reducedMotion: boolean
}

/** Curved light trails following the organic wave S-curves */
const NETWORK_PATHS = [
  'M80 470 C 260 450, 400 400, 520 370 C 640 340, 720 355, 820 390 C 920 425, 1020 390, 1160 300 C 1280 230, 1360 180, 1480 130',
  'M120 510 C 300 485, 440 435, 560 400 C 680 365, 760 380, 860 415 C 960 450, 1060 410, 1200 320 C 1320 250, 1400 195, 1520 145',
  'M60 430 C 240 410, 380 365, 500 340 C 620 315, 700 335, 800 375 C 900 415, 1000 375, 1140 285 C 1260 210, 1340 160, 1460 110',
  'M160 545 C 340 515, 480 465, 600 430 C 720 395, 800 410, 900 445 C 1000 480, 1100 440, 1240 350 C 1360 280, 1440 230, 1560 180',
  'M40 400 C 220 385, 360 345, 480 320 C 600 295, 680 320, 780 360 C 880 400, 980 360, 1120 270 C 1240 195, 1320 145, 1440 95',
  'M200 490 C 360 460, 500 415, 640 385 C 760 360, 840 375, 940 410 C 1040 445, 1140 400, 1280 310 C 1380 250, 1460 200, 1580 155',
  'M100 450 C 280 425, 420 385, 560 360 C 680 340, 740 360, 840 400 C 940 440, 1040 400, 1180 305 C 1300 230, 1380 175, 1500 125',
  'M140 530 C 320 500, 460 450, 600 415 C 720 385, 780 400, 880 435 C 980 470, 1080 425, 1220 335 C 1340 265, 1420 215, 1540 165',
] as const

const NODES: ReadonlyArray<[number, number, number, boolean]> = [
  [520, 370, 4.2, true],
  [640, 340, 3.6, false],
  [720, 355, 4.8, true],
  [820, 390, 5.2, true],
  [920, 425, 3.8, false],
  [1020, 390, 4.5, true],
  [1160, 300, 4.0, false],
  [860, 415, 3.4, true],
  [780, 360, 3.2, false],
  [1100, 270, 3.8, true],
]

const GLINTS: ReadonlyArray<[number, number, number]> = [
  [720, 355, 9],
  [820, 390, 8],
  [1020, 390, 7],
  [920, 425, 6],
  [1160, 300, 7],
]

/** Layer B — curved trails that fade in/out at path ends */
export default function AuroraNetworkLayer({ uid, reducedMotion }: AuroraNetworkLayerProps) {
  const g = (name: string) => gradId(uid, name)

  return (
    <svg
      className="hero-aurora-layer hero-aurora-layer--network"
      viewBox="0 0 1440 720"
      preserveAspectRatio="xMidYMid slice"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        {/* Fade: 0 → bright center → 0 at edges */}
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

      <g className="hero-flow-parallax-aurora">
        <g className="aurora-network-paths" filter={`url(#${g('line-glow')})`}>
          {NETWORK_PATHS.map((d, i) => (
            <path
              key={`net-${i}`}
              className={cn(
                'aurora-network-path',
                !reducedMotion && 'aurora-network-path--live',
                i >= 5 && 'aurora-network-path--desktop',
              )}
              d={d}
              fill="none"
              stroke={`url(#${g('trail')})`}
              strokeWidth={i % 3 === 0 ? 1.45 : 1.15}
              strokeLinecap="round"
              style={!reducedMotion ? { animationDelay: `${i * 0.9}s` } : undefined}
            />
          ))}
        </g>

        <g className="aurora-network-nodes">
          {NODES.map(([cx, cy, r, pulse], i) => (
            <circle
              key={`node-${i}`}
              className={cn(
                'aurora-network-node',
                pulse && !reducedMotion && 'aurora-network-node--pulse',
                i >= 7 && 'aurora-network-node--desktop',
              )}
              cx={cx}
              cy={cy}
              r={r}
              fill="#FFFFFF"
              filter={`url(#${g('node-glow')})`}
              style={pulse && !reducedMotion ? { animationDelay: `${i * 0.45}s` } : undefined}
            />
          ))}
        </g>

        <g className="aurora-network-glints">
          {GLINTS.map(([cx, cy, size], i) => (
            <path
              key={`glint-${i}`}
              className={cn('aurora-network-glint', i >= 3 && 'aurora-network-glint--desktop')}
              d={`M${cx} ${cy - size} L${cx + size * 0.32} ${cy - size * 0.32} L${cx + size} ${cy} L${cx + size * 0.32} ${cy + size * 0.32} L${cx} ${cy + size} L${cx - size * 0.32} ${cy + size * 0.32} L${cx - size} ${cy} L${cx - size * 0.32} ${cy - size * 0.32} Z`}
              fill="#FFFFFF"
              opacity="0.85"
              filter={`url(#${g('node-glow')})`}
            />
          ))}
        </g>
      </g>
    </svg>
  )
}

export { NETWORK_PATHS }
