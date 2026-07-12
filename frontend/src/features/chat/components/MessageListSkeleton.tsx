import Skeleton from '@/components/ui/Skeleton'

export default function MessageListSkeleton() {
  return (
    <div
      className="flex flex-1 flex-col gap-5 overflow-hidden px-4 py-5 sm:px-6"
      aria-hidden
    >
      <div className="flex justify-end">
        <Skeleton className="h-16 w-[min(72%,20rem)]" />
      </div>
      <div className="flex justify-start">
        <div className="flex w-[min(78%,24rem)] flex-col gap-2">
          <Skeleton className="h-4 w-full" variant="text" />
          <Skeleton className="h-4 w-[92%]" variant="text" />
          <Skeleton className="h-4 w-[68%]" variant="text" />
        </div>
      </div>
      <div className="flex justify-end">
        <Skeleton className="h-12 w-[min(60%,16rem)]" />
      </div>
      <div className="flex justify-start">
        <div className="flex w-[min(82%,26rem)] flex-col gap-2">
          <Skeleton className="h-4 w-full" variant="text" />
          <Skeleton className="h-4 w-[88%]" variant="text" />
          <Skeleton className="h-4 w-[75%]" variant="text" />
          <Skeleton className="h-4 w-[50%]" variant="text" />
        </div>
      </div>
    </div>
  )
}
