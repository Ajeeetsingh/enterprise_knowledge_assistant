import Skeleton from '@/components/ui/Skeleton'

export default function ConversationListSkeleton() {
  return (
    <div className="space-y-1 px-3 py-2" aria-hidden>
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="flex flex-col gap-2 rounded-md px-3 py-3">
          <Skeleton className="h-4 w-[78%]" variant="text" />
          <Skeleton className="h-3 w-[45%]" variant="text" />
        </div>
      ))}
    </div>
  )
}
