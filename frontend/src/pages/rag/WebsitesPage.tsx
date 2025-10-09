import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AppShell } from '../../components/layout/AppShell'
import { Header } from '../../components/layout/Header'
import { Card, CardDescription, CardHeader, CardTitle } from '../../components/ui/Card'
import { Spinner } from '../../components/ui/Spinner'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { Modal } from '../../components/ui/Modal'
import { Input } from '../../components/ui/Input'
import { Progress } from '../../components/ui/Progress'
import { useWebsites, useCreateWebsite, useDeleteWebsite } from '../../features/rag/hooks'
import type { Website, WebsiteCreate } from '../../features/rag/api'
import { ApiError } from '../../lib/api'

const STATUS_COLORS: Record<Website['status'], string> = {
  PENDING: 'bg-slate-500/20 text-slate-300',
  CRAWLING: 'bg-blue-500/20 text-blue-300',
  READY: 'bg-emerald-500/20 text-emerald-300',
  ERROR: 'bg-red-500/20 text-red-300',
}

export function WebsitesPage() {
  const navigate = useNavigate()
  const { data: websites, isLoading } = useWebsites()
  const createWebsite = useCreateWebsite()
  const deleteWebsite = useDeleteWebsite()

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [formData, setFormData] = useState<WebsiteCreate>({
    url: '',
    name: '',
    max_pages: 100,
  })
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const normalizeMaxPages = (value?: number) => {
    const maxPages = Number.isFinite(value) ? (value as number) : undefined
    if (maxPages === undefined) {
      return 100
    }
    return Math.min(1000, Math.max(1, Math.trunc(maxPages)))
  }

  const getCrawlProgress = (website: Website) => {
    if (website.status === 'READY') {
      return 100
    }

    if (website.status === 'ERROR' || website.max_pages <= 0) {
      return 0
    }

    const ratio = website.pages_indexed / website.max_pages
    return Math.max(0, Math.min(100, Math.round(ratio * 100)))
  }

  const handleCreate = async () => {
    setErrorMessage(null)
    try {
      const trimmedUrl = formData.url.trim()
      if (!trimmedUrl) {
        setErrorMessage('Please enter a valid website URL.')
        return
      }

      const sanitizedMaxPages = normalizeMaxPages(formData.max_pages)
      const website = await createWebsite.mutateAsync({
        ...formData,
        url: trimmedUrl,
        name: formData.name?.trim() ? formData.name.trim() : undefined,
        max_pages: sanitizedMaxPages,
      })
      setIsCreateModalOpen(false)
      setFormData({ url: '', name: '', max_pages: 100 })
      navigate(`/rag/websites/${website.id}`)
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.message)
      } else {
        setErrorMessage('Failed to create website. Please try again.')
      }
    }
  }

  const handleDelete = async (websiteId: string) => {
    if (!confirm('Are you sure you want to delete this website? This will remove all associated data.')) {
      return
    }
    try {
      await deleteWebsite.mutateAsync(websiteId)
    } catch (error) {
      console.error('Failed to delete website:', error)
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <AppShell>
      <Header
        title="AI Website Assistant"
        description="Manage your RAG-powered chatbot websites"
      />

      <div className="flex-1 p-6">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-white">Websites</h2>
          <Button onClick={() => setIsCreateModalOpen(true)}>
            + Add Website
          </Button>
        </div>

        {isLoading ? (
          <div className="flex min-h-[240px] items-center justify-center rounded-2xl border border-slate-800/60 bg-slate-950/40">
            <Spinner size="lg" />
          </div>
        ) : websites && websites.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {websites.map((website) => (
              <Card key={website.id} className="cursor-pointer transition-all hover:border-slate-700">
                <div onClick={() => navigate(`/rag/websites/${website.id}`)}>
                  <CardHeader>
                    <div className="flex-1">
                      <CardTitle>{website.name}</CardTitle>
                      <CardDescription className="mt-1 truncate">
                        {website.url}
                      </CardDescription>
                    </div>
                    <Badge className={STATUS_COLORS[website.status]}>
                      {website.status}
                    </Badge>
                  </CardHeader>

                  <div className="space-y-2 text-sm text-slate-400">
                    <div className="flex justify-between">
                      <span>Pages Indexed:</span>
                      <span className="text-white">{website.pages_indexed}</span>
                    </div>
                    {website.last_crawled_at && (
                      <div className="flex justify-between">
                        <span>Last Crawled:</span>
                        <span className="text-white">{formatDate(website.last_crawled_at)}</span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span>Status:</span>
                      <span className={website.is_active ? 'text-emerald-300' : 'text-slate-400'}>
                        {website.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </div>

                  {website.crawl_error && (
                    <div className="mt-3 rounded-lg border border-red-500/40 bg-red-500/10 p-2 text-xs text-red-300">
                      {website.crawl_error}
                    </div>
                  )}

                  {(website.status === 'PENDING' || website.status === 'CRAWLING') && (
                    <div className="mt-4 space-y-2">
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span>Crawling Progress</span>
                        <span className="text-slate-200">{getCrawlProgress(website)}%</span>
                      </div>
                      <Progress
                        value={getCrawlProgress(website)}
                        srLabel={`Crawling progress for ${website.name || website.url}`}
                      />
                      <p className="text-xs text-slate-500">
                        Indexed {website.pages_indexed} of {website.max_pages} pages
                      </p>
                    </div>
                  )}
                </div>

                <div className="mt-4 flex gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={(e) => {
                      e.stopPropagation()
                      navigate(`/rag/websites/${website.id}`)
                    }}
                    className="flex-1"
                  >
                    Manage
                  </Button>
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDelete(website.id)
                    }}
                  >
                    Delete
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <div className="py-12 text-center">
              <p className="mb-4 text-slate-400">No websites configured yet.</p>
              <Button onClick={() => setIsCreateModalOpen(true)}>
                + Add Your First Website
              </Button>
            </div>
          </Card>
        )}
      </div>

      <Modal
        open={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false)
          setErrorMessage(null)
        }}
        title="Add New Website"
      >
        <div className="space-y-4">
          {errorMessage && (
            <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
              {errorMessage}
            </div>
          )}

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Website URL *
            </label>
            <Input
              type="url"
              placeholder="https://example.com"
              value={formData.url}
              onChange={(e) => setFormData({ ...formData, url: e.target.value })}
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Name (optional)
            </label>
            <Input
              type="text"
              placeholder="My Website"
              value={formData.name || ''}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
            <p className="mt-1 text-xs text-slate-500">
              Defaults to website URL if not provided
            </p>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Max Pages to Crawl
            </label>
            <Input
              type="number"
              min="1"
              max="1000"
              value={formData.max_pages ?? ''}
              onChange={(e) => {
                const rawValue = e.target.value
                if (rawValue === '') {
                  setFormData({ ...formData, max_pages: undefined })
                  return
                }

                const parsedValue = parseInt(rawValue, 10)
                if (Number.isNaN(parsedValue)) {
                  return
                }

                setFormData({
                  ...formData,
                  max_pages: Math.min(1000, Math.max(1, parsedValue)),
                })
              }}
            />
            <p className="mt-1 text-xs text-slate-500">
              Maximum number of pages to index (1-1000)
            </p>
          </div>

          <div className="flex gap-3 pt-4">
            <Button
              onClick={handleCreate}
              disabled={!formData.url || createWebsite.isPending}
              className="flex-1"
            >
              {createWebsite.isPending ? 'Creating...' : 'Create Website'}
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setIsCreateModalOpen(false)
                setErrorMessage(null)
              }}
              type="button"
            >
              Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </AppShell>
  )
}
