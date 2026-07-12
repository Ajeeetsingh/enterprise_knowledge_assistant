import PlaceholderState from '@/components/ui/PlaceholderState'
import Card from '@/components/ui/Card'

export default function ExportHistory() {
  return (
    <Card className="flex flex-col gap-2">
      <h3 className="text-lg font-semibold text-foreground">Export History</h3>
      <PlaceholderState>
        Export history will appear here in a future release. Downloads are currently saved directly
        to your device.
      </PlaceholderState>
    </Card>
  )
}
