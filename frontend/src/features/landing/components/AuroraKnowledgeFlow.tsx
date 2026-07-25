import AuroraNetworkLayer from './aurora/AuroraNetworkLayer'
import AuroraWaveLayer from './aurora/AuroraWaveLayer'

export interface AuroraKnowledgeFlowProps {
  uid: string
  reducedMotion: boolean
}

/**
 * Hero background — full-bleed wave mesh + network trails.
 * Wave layer is rendered by the parent outside the max-width stage.
 */
export default function AuroraKnowledgeFlow({
  uid,
  reducedMotion,
}: AuroraKnowledgeFlowProps) {
  return <AuroraNetworkLayer uid={uid} reducedMotion={reducedMotion} />
}

export { AuroraWaveLayer }
