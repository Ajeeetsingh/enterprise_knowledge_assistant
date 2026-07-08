import Card from '@/components/ui/Card'

export default function ExportHistory() {
  return (
    <Card className="flex flex-col gap-2">
      <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">Export History</h3>
      <p className="text-sm text-neutral-500 dark:text-neutral-400">
        Export history will appear here in a future release. Downloads are currently saved directly
        to your device.
      </p>
    </Card>
  )
}
