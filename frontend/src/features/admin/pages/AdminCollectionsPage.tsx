import { useMemo, useState } from 'react'

import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { useToast } from '@/contexts/ToastContext'

import {
  ArchiveCollectionDialog,
  CollectionDetailsModal,
  CollectionsBackendNotice,
  CollectionsTable,
  CreateCollectionDialog,
  RenameCollectionDialog,
  filterCollectionsByName,
  useAdminCollections,
  type AdminCollection,
} from '../collections'
import { useDebouncedValue } from '../hooks/useDebouncedValue'

export default function AdminCollectionsPage() {
  const { showSuccess, showError } = useToast()
  const [search, setSearch] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [viewTarget, setViewTarget] = useState<AdminCollection | null>(null)
  const [renameTarget, setRenameTarget] = useState<AdminCollection | null>(null)
  const [renameConfirmOpen, setRenameConfirmOpen] = useState(false)
  const [pendingRename, setPendingRename] = useState('')
  const [renameError, setRenameError] = useState<string | null>(null)
  const [archiveTarget, setArchiveTarget] = useState<AdminCollection | null>(null)
  const [archiveError, setArchiveError] = useState<string | null>(null)

  const debouncedSearch = useDebouncedValue(search, 300)

  const {
    activeCollections,
    isCreating,
    isUpdating,
    isArchiving,
    createCollection,
    renameCollection,
    archiveCollection,
  } = useAdminCollections()

  const visibleCollections = useMemo(
    () => filterCollectionsByName(activeCollections, debouncedSearch),
    [activeCollections, debouncedSearch],
  )

  function openCreate() {
    setCreateError(null)
    setCreateOpen(true)
  }

  function closeCreate() {
    if (isCreating) return
    setCreateOpen(false)
    setCreateError(null)
  }

  async function handleCreate(input: { name: string; description: string }) {
    setCreateError(null)

    try {
      await createCollection({
        name: input.name,
        description: input.description || null,
      })
      setCreateOpen(false)
      showSuccess('Collection created in local preview.')
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unable to create collection.'
      setCreateError(message)
      showError(message)
    }
  }

  function openRename(collection: AdminCollection) {
    setRenameError(null)
    setRenameConfirmOpen(false)
    setPendingRename('')
    setRenameTarget(collection)
  }

  function closeRename() {
    if (isUpdating) return
    setRenameTarget(null)
    setRenameConfirmOpen(false)
    setRenameError(null)
    setPendingRename('')
  }

  function handleRenameApply(name: string) {
    setPendingRename(name)
    setRenameConfirmOpen(true)
  }

  async function handleRenameConfirm() {
    if (!renameTarget || !pendingRename) return
    setRenameError(null)

    try {
      await renameCollection(renameTarget.id, { name: pendingRename })
      setRenameTarget(null)
      setRenameConfirmOpen(false)
      setPendingRename('')
      showSuccess('Collection renamed in local preview.')
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unable to update collection.'
      setRenameError(message)
      showError(message)
    }
  }

  function openArchive(collection: AdminCollection) {
    setArchiveError(null)
    setArchiveTarget(collection)
  }

  function closeArchive() {
    if (isArchiving) return
    setArchiveTarget(null)
    setArchiveError(null)
  }

  async function handleArchiveConfirm() {
    if (!archiveTarget) return
    setArchiveError(null)

    try {
      await archiveCollection(archiveTarget.id)
      setArchiveTarget(null)
      showSuccess('Collection archived in local preview.')
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unable to archive collection.'
      setArchiveError(message)
      showError(message)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">
            Collections Management
          </h2>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Organize enterprise knowledge into logical groups such as HR, Finance, and Compliance.
          </p>
        </div>

        <Button onClick={openCreate}>Create collection</Button>
      </div>

      <CollectionsBackendNotice />

      <section
        aria-label="Collection search"
        className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-900"
      >
        <Input
          label="Search collections"
          type="search"
          value={search}
          placeholder="Search by collection name"
          onChange={(event) => setSearch(event.target.value)}
        />
      </section>

      <CollectionsTable
        collections={visibleCollections}
        onView={setViewTarget}
        onRename={openRename}
        onArchive={openArchive}
      />

      <CreateCollectionDialog
        isOpen={createOpen}
        isSubmitting={isCreating}
        error={createError}
        onClose={closeCreate}
        onSubmit={(input) => void handleCreate(input)}
      />

      <CollectionDetailsModal
        isOpen={viewTarget !== null}
        collection={viewTarget}
        onClose={() => setViewTarget(null)}
      />

      <RenameCollectionDialog
        collection={renameTarget}
        isOpen={renameTarget !== null}
        confirmOpen={renameConfirmOpen}
        isSubmitting={isUpdating}
        error={renameError}
        onClose={closeRename}
        onApply={handleRenameApply}
        onConfirm={() => void handleRenameConfirm()}
        onBack={() => setRenameConfirmOpen(false)}
      />

      <ArchiveCollectionDialog
        collection={archiveTarget}
        isOpen={archiveTarget !== null}
        isSubmitting={isArchiving}
        error={archiveError}
        onClose={closeArchive}
        onConfirm={() => void handleArchiveConfirm()}
      />
    </div>
  )
}
