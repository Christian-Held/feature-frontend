import { useEffect, useState, type FormEvent } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import { AppShell } from '../../components/layout/AppShell'
import { Header } from '../../components/layout/Header'
import { Card, CardDescription, CardHeader, CardTitle } from '../../components/ui/Card'
import { Spinner } from '../../components/ui/Spinner'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { Modal } from '../../components/ui/Modal'
import { Input } from '../../components/ui/Input'
import { TextArea } from '../../components/ui/TextArea'
import { Progress } from '../../components/ui/Progress'
import { ChatPreview } from '../../components/rag/ChatPreview'
import {
  useWebsite,
  useUpdateWebsite,
  useTriggerCrawl,
  useCustomQAs,
  useCreateCustomQA,
  useDeleteCustomQA,
  useAnalytics,
} from '../../features/rag/hooks'
import type { CustomQACreate, Website, WidgetPosition } from '../../features/rag/api'
import { ApiError } from '../../lib/api'

const STATUS_COLORS: Record<Website['status'], string> = {
  PENDING: 'bg-slate-500/20 text-slate-300',
  CRAWLING: 'bg-blue-500/20 text-blue-300',
  READY: 'bg-emerald-500/20 text-emerald-300',
  ERROR: 'bg-red-500/20 text-red-300',
}

const DEFAULT_BRAND_COLOR = '#2563eb'

type AppearanceFormState = {
  name: string
  brand_color: string
  logo_url: string
  welcome_message: string
  position: WidgetPosition
}

const POSITION_OPTIONS: Record<WidgetPosition, string> = {
  BOTTOM_RIGHT: 'Bottom Right',
  BOTTOM_LEFT: 'Bottom Left',
  TOP_RIGHT: 'Top Right',
  TOP_LEFT: 'Top Left',
}

export function WebsiteDetailPage() {
  const { websiteId } = useParams<{ websiteId: string }>()
  const navigate = useNavigate()

  const resolvedWebsiteId = websiteId ?? ''

  const { data: website, isLoading } = useWebsite(resolvedWebsiteId)
  const updateWebsite = useUpdateWebsite(resolvedWebsiteId)
  const triggerCrawl = useTriggerCrawl(resolvedWebsiteId)
  const { data: qas } = useCustomQAs(resolvedWebsiteId)
  const createQA = useCreateCustomQA(resolvedWebsiteId)
  const deleteQA = useDeleteCustomQA(resolvedWebsiteId)
  const { data: analytics } = useAnalytics(resolvedWebsiteId)

  const [activeTab, setActiveTab] = useState<'overview' | 'qas' | 'analytics' | 'preview' | 'embed'>('overview')
  const [isQAModalOpen, setIsQAModalOpen] = useState(false)
  const [qaFormData, setQAFormData] = useState<CustomQACreate>({
    question: '',
    answer: '',
    priority: 100,
  })
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [appearanceConfig, setAppearanceConfig] = useState<AppearanceFormState>({
    name: '',
    brand_color: DEFAULT_BRAND_COLOR,
    logo_url: '',
    welcome_message: '',
    position: 'BOTTOM_RIGHT',
  })

  const normalizePriority = (value?: number) => {
    if (value === undefined) {
      return undefined
    }
    return Math.min(1000, Math.max(0, Math.trunc(value)))
  }

  const getCrawlProgress = (site: Website) => {
    if (site.status === 'READY') {
      return 100
    }
    if (site.status === 'ERROR' || site.max_pages <= 0) {
      return 0
    }
    return Math.max(0, Math.min(100, Math.round((site.pages_indexed / site.max_pages) * 100)))
  }

  const handleCrawl = async () => {
    try {
      const response = await triggerCrawl.mutateAsync()
      if (response.status === 'error') {
        setErrorMessage(response.message || 'Failed to start crawl')
        setTimeout(() => setErrorMessage(null), 5000)
        return
      }

      setSuccessMessage(response.message || 'Crawl started successfully')
      setTimeout(() => setSuccessMessage(null), 3000)
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.message)
      } else {
        setErrorMessage('Failed to start crawl')
      }
      setTimeout(() => setErrorMessage(null), 5000)
    }
  }

  const handleToggleActive = async () => {
    try {
      await updateWebsite.mutateAsync({ is_active: !website?.is_active })
    } catch (error) {
      console.error('Failed to toggle active status:', error)
    }
  }

  const handleCreateQA = async () => {
    setErrorMessage(null)
    try {
      const trimmedQuestion = qaFormData.question.trim()
      const trimmedAnswer = qaFormData.answer.trim()

      if (!trimmedQuestion || !trimmedAnswer) {
        setErrorMessage('Question and answer are required.')
        return
      }

      const payload: CustomQACreate = {
        ...qaFormData,
        question: trimmedQuestion,
        answer: trimmedAnswer,
        priority: normalizePriority(qaFormData.priority),
        category: qaFormData.category?.trim() || undefined,
        keywords: qaFormData.keywords?.trim() || undefined,
      }

      await createQA.mutateAsync(payload)
      setIsQAModalOpen(false)
      setQAFormData({ question: '', answer: '', priority: 100 })
      setSuccessMessage('Q&A created successfully')
      setTimeout(() => setSuccessMessage(null), 3000)
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.message)
      } else {
        setErrorMessage('Failed to create Q&A')
      }
    }
  }

  const handleDeleteQA = async (qaId: string) => {
    if (!confirm('Are you sure you want to delete this Q&A?')) {
      return
    }
    try {
      await deleteQA.mutateAsync(qaId)
    } catch (error) {
      console.error('Failed to delete Q&A:', error)
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setSuccessMessage('Copied to clipboard!')
    setTimeout(() => setSuccessMessage(null), 2000)
  }

  useEffect(() => {
    if (!website) {
      return
    }

    setAppearanceConfig({
      name: website.name ?? '',
      brand_color: website.brand_color ?? DEFAULT_BRAND_COLOR,
      logo_url: website.logo_url ?? '',
      welcome_message: website.welcome_message ?? '',
      position: website.position,
    })
  }, [website])

  const handleAppearanceChange = <K extends keyof AppearanceFormState>(
    key: K,
    value: AppearanceFormState[K],
  ) => {
    setAppearanceConfig((prev) => ({ ...prev, [key]: value }))
  }

  const handleResetAppearance = () => {
    if (!website) {
      setAppearanceConfig({
        name: '',
        brand_color: DEFAULT_BRAND_COLOR,
        logo_url: '',
        welcome_message: '',
        position: 'BOTTOM_RIGHT',
      })
      return
    }

    setAppearanceConfig({
      name: website.name ?? '',
      brand_color: website.brand_color ?? DEFAULT_BRAND_COLOR,
      logo_url: website.logo_url ?? '',
      welcome_message: website.welcome_message ?? '',
      position: website.position,
    })
  }

  const handleSaveAppearance = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setErrorMessage(null)

    const hexPattern = /^#[0-9A-Fa-f]{6}$/
    if (appearanceConfig.brand_color && !hexPattern.test(appearanceConfig.brand_color)) {
      setErrorMessage('Brand color must be a valid hex value, e.g. #2563EB.')
      return
    }

    try {
      await updateWebsite.mutateAsync({
        name: appearanceConfig.name.trim() || undefined,
        brand_color: appearanceConfig.brand_color || undefined,
        logo_url: appearanceConfig.logo_url.trim() || undefined,
        welcome_message: appearanceConfig.welcome_message.trim() || undefined,
        position: appearanceConfig.position,
      })
      setSuccessMessage('Appearance updated successfully')
      setTimeout(() => setSuccessMessage(null), 3000)
    } catch (error) {
      console.error('Failed to update appearance:', error)
      setErrorMessage('Failed to save appearance settings.')
      setTimeout(() => setErrorMessage(null), 5000)
    }
  }

  if (isLoading) {
    return (
      <AppShell>
        <Header title="Loading..." description="" />
        <div className="flex min-h-[240px] items-center justify-center">
          <Spinner size="lg" />
        </div>
      </AppShell>
    )
  }

  if (!websiteId) {
    return <Navigate to="/rag/websites" replace />
  }

  if (!website) {
    return (
      <AppShell>
        <Header title="Website Not Found" description="" />
        <div className="p-6">
          <Card>
            <p className="text-slate-400">Website not found.</p>
            <Button onClick={() => navigate('/rag/websites')} className="mt-4">
              Back to Websites
            </Button>
          </Card>
        </div>
      </AppShell>
    )
  }

  const widgetBaseUrl =
    import.meta.env.VITE_WIDGET_BASE_URL ??
    (typeof window !== 'undefined' ? window.location.origin : '')

  const normalizedWidgetBaseUrl = widgetBaseUrl.replace(/\/$/, '')

  const embedCode = `<script>
(function() {
  var script = document.createElement('script');
  script.src = '${normalizedWidgetBaseUrl}/widget.js';
  script.async = true;
  script.setAttribute('data-embed-token', '${website.embed_token}');
  document.body.appendChild(script);
})();
</script>`

  return (
    <AppShell>
      <Header
        title={website.name}
        description={website.url}
      />

      <div className="flex-1 p-6">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex gap-2">
            <Badge className={STATUS_COLORS[website.status]}>
              {website.status}
            </Badge>
            <Badge className={website.is_active ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-500/20 text-slate-400'}>
              {website.is_active ? 'Active' : 'Inactive'}
            </Badge>
          </div>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={handleToggleActive}
              disabled={updateWebsite.isPending}
            >
              {website.is_active ? 'Deactivate' : 'Activate'}
            </Button>
            <Button onClick={() => navigate('/rag/websites')}>
              Back to Websites
            </Button>
          </div>
        </div>

        {successMessage && (
          <div className="mb-4 rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-3 text-sm text-emerald-200">
            {successMessage}
          </div>
        )}

        {errorMessage && (
          <div className="mb-4 rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
            {errorMessage}
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6 flex gap-2 border-b border-slate-800">
          {(['overview', 'qas', 'analytics', 'preview', 'embed'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'border-b-2 border-blue-500 text-blue-400'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Crawl Status</CardTitle>
              </CardHeader>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Pages Indexed:</span>
                  <span className="text-white font-semibold">{website.pages_indexed}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Max Pages:</span>
                  <span className="text-white">{website.max_pages}</span>
                </div>
                {website.last_crawled_at && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Last Crawled:</span>
                    <span className="text-white">{formatDate(website.last_crawled_at)}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-slate-400">Frequency:</span>
                  <span className="text-white">{website.crawl_frequency}</span>
                </div>
              </div>
              {(website.status === 'PENDING' || website.status === 'CRAWLING') && (
                <div className="mt-4 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>Crawling Progress</span>
                    <span className="text-slate-200">{getCrawlProgress(website)}%</span>
                  </div>
                  <Progress
                    value={getCrawlProgress(website)}
                    srLabel={`Crawling progress for ${website.name}`}
                  />
                  <p className="text-xs text-slate-500">
                    Indexed {website.pages_indexed} of {website.max_pages} pages
                  </p>
                </div>
              )}
              {website.crawl_error && (
                <div className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-300">
                  {website.crawl_error}
                </div>
              )}
              <Button
                onClick={handleCrawl}
                disabled={website.status === 'CRAWLING' || triggerCrawl.isPending}
                className="mt-4 w-full"
              >
                {website.status === 'CRAWLING' ? 'Crawling...' : 'Start Crawl'}
              </Button>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Configuration</CardTitle>
              </CardHeader>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="block text-slate-400 mb-1">Website URL</span>
                  <span className="text-white break-all">{website.url}</span>
                </div>
                <div>
                  <span className="block text-slate-400 mb-1">Embed Token</span>
                  <div className="flex gap-2">
                    <code className="flex-1 rounded bg-slate-950 px-2 py-1 text-xs text-emerald-400 font-mono">
                      {website.embed_token}
                    </code>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => copyToClipboard(website.embed_token)}
                    >
                      Copy
                    </Button>
                  </div>
                </div>
                <div>
                  <span className="block text-slate-400 mb-1">Language</span>
                  <span className="text-white">{website.language}</span>
                </div>
                {website.welcome_message && (
                  <div>
                    <span className="block text-slate-400 mb-1">Welcome Message</span>
                    <span className="text-white">{website.welcome_message}</span>
                  </div>
                )}
              </div>
            </Card>
          </div>
        )}

        {/* Q&As Tab */}
        {activeTab === 'qas' && (
          <div>
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Custom Q&A Pairs</h3>
              <Button onClick={() => setIsQAModalOpen(true)}>
                + Add Q&A
              </Button>
            </div>

            {qas && qas.length > 0 ? (
              <div className="space-y-3">
                {qas.map((qa) => (
                  <Card key={qa.id}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="mb-2 flex items-center gap-2">
                          <span className="text-sm font-semibold text-white">Q:</span>
                          <span className="text-sm text-slate-300">{qa.question}</span>
                        </div>
                        <div className="flex items-start gap-2">
                          <span className="text-sm font-semibold text-white">A:</span>
                          <span className="text-sm text-slate-400">{qa.answer}</span>
                        </div>
                        <div className="mt-2 flex gap-2">
                          {qa.category && (
                            <Badge className="bg-blue-500/20 text-blue-300 text-xs">
                              {qa.category}
                            </Badge>
                          )}
                          <Badge className="bg-slate-500/20 text-slate-300 text-xs">
                            Priority: {qa.priority}
                          </Badge>
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => handleDeleteQA(qa.id)}
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
                  <p className="mb-4 text-slate-400">No custom Q&As yet.</p>
                  <Button onClick={() => setIsQAModalOpen(true)}>
                    + Add Your First Q&A
                  </Button>
                </div>
              </Card>
            )}
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && (
          <div>
            <h3 className="mb-4 text-lg font-semibold text-white">Usage Analytics</h3>
            {analytics && analytics.length > 0 ? (
              <div className="space-y-3">
                {analytics.map((stat) => (
                  <Card key={stat.date}>
                    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                      <div>
                        <span className="block text-xs text-slate-400">Date</span>
                        <span className="text-sm font-semibold text-white">{stat.date}</span>
                      </div>
                      <div>
                        <span className="block text-xs text-slate-400">Conversations</span>
                        <span className="text-sm font-semibold text-white">{stat.conversations_count}</span>
                      </div>
                      <div>
                        <span className="block text-xs text-slate-400">Messages</span>
                        <span className="text-sm font-semibold text-white">{stat.messages_count}</span>
                      </div>
                      <div>
                        <span className="block text-xs text-slate-400">Cost</span>
                        <span className="text-sm font-semibold text-white">${stat.cost_usd.toFixed(4)}</span>
                      </div>
                    </div>
                    {stat.avg_satisfaction_rating && (
                      <div className="mt-3 pt-3 border-t border-slate-800">
                        <span className="text-xs text-slate-400">Avg Rating: </span>
                        <span className="text-sm text-emerald-300">{stat.avg_satisfaction_rating.toFixed(1)}/5</span>
                        <span className="ml-2 text-xs text-slate-500">({stat.total_ratings} ratings)</span>
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            ) : (
              <Card>
                <div className="py-12 text-center text-slate-400">
                  No analytics data available yet.
                </div>
              </Card>
            )}
          </div>
        )}

        {/* Preview Tab */}
        {activeTab === 'preview' && (
          <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
            <Card>
              <CardHeader>
                <div>
                  <CardTitle>Appearance Settings</CardTitle>
                  <CardDescription>
                    Tweak the branding for your assistant and preview the changes in real time.
                  </CardDescription>
                </div>
              </CardHeader>
              <form className="space-y-5" onSubmit={handleSaveAppearance}>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-300">
                    Assistant Name
                  </label>
                  <Input
                    type="text"
                    placeholder="Acme Assistant"
                    value={appearanceConfig.name}
                    onChange={(event) => handleAppearanceChange('name', event.target.value)}
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    Displayed in the chat header.
                  </p>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-300">
                    Brand Color
                  </label>
                  <div className="flex items-center gap-3">
                    <input
                      type="color"
                      value={appearanceConfig.brand_color || DEFAULT_BRAND_COLOR}
                      onChange={(event) => handleAppearanceChange('brand_color', event.target.value)}
                      className="h-10 w-16 cursor-pointer rounded-xl border border-slate-700/80 bg-slate-900/40"
                      aria-label="Brand color picker"
                    />
                    <Input
                      type="text"
                      value={appearanceConfig.brand_color}
                      onChange={(event) => handleAppearanceChange('brand_color', event.target.value)}
                      placeholder="#2563EB"
                    />
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    Provide a hex value (e.g. #2563EB). Leave blank to use the default accent.
                  </p>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-300">
                    Logo URL
                  </label>
                  <Input
                    type="url"
                    placeholder="https://example.com/logo.png"
                    value={appearanceConfig.logo_url}
                    onChange={(event) => handleAppearanceChange('logo_url', event.target.value)}
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    Optional square logo displayed in the header. Leave empty to use initials.
                  </p>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-300">
                    Welcome Message
                  </label>
                  <TextArea
                    rows={3}
                    value={appearanceConfig.welcome_message}
                    onChange={(event) => handleAppearanceChange('welcome_message', event.target.value)}
                    placeholder="Hi there! Ask me anything about our services."
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-300">
                    Widget Position
                  </label>
                  <select
                    value={appearanceConfig.position}
                    onChange={(event) => handleAppearanceChange('position', event.target.value as WidgetPosition)}
                    className="w-full rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                  >
                    {Object.entries(POSITION_OPTIONS).map(([value, label]) => (
                      <option key={value} value={value} className="bg-slate-900 text-slate-100">
                        {label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <Button type="button" variant="secondary" onClick={handleResetAppearance}>
                    Reset
                  </Button>
                  <Button type="submit" disabled={updateWebsite.isPending}>
                    Save Appearance
                  </Button>
                </div>
              </form>
            </Card>

            <Card className="overflow-hidden">
              <ChatPreview
                name={appearanceConfig.name || website.name || 'AI Assistant'}
                brandColor={appearanceConfig.brand_color || DEFAULT_BRAND_COLOR}
                logoUrl={appearanceConfig.logo_url || undefined}
                welcomeMessage={appearanceConfig.welcome_message || website.welcome_message || 'How can I help you today?'}
                position={appearanceConfig.position}
                token={website.embed_token}
              />
            </Card>
          </div>
        )}

        {/* Embed Tab */}
        {activeTab === 'embed' && (
          <div>
            <Card>
              <CardHeader>
                <CardTitle>Widget Embed Code</CardTitle>
                <CardDescription>
                  Copy and paste this code into your website's HTML
                </CardDescription>
              </CardHeader>

              <div className="space-y-4">
                <div className="rounded-lg bg-slate-950 p-4">
                  <pre className="overflow-x-auto text-xs text-emerald-400">
                    <code>{embedCode}</code>
                  </pre>
                </div>

                <Button onClick={() => copyToClipboard(embedCode)}>
                  Copy Embed Code
                </Button>

                <div className="mt-6 rounded-lg border border-blue-500/40 bg-blue-500/10 p-4">
                  <h4 className="mb-2 text-sm font-semibold text-blue-300">Installation Instructions</h4>
                  <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-400">
                    <li>Copy the embed code above</li>
                    <li>Paste it before the closing &lt;/body&gt; tag in your HTML</li>
                    <li>Make sure your website status is "Active"</li>
                    <li>The chat widget will appear in the bottom right corner</li>
                  </ol>
                </div>
              </div>
            </Card>
          </div>
        )}
      </div>

      {/* Create Q&A Modal */}
      <Modal
        open={isQAModalOpen}
        onClose={() => {
          setIsQAModalOpen(false)
          setErrorMessage(null)
        }}
        title="Add Custom Q&A"
      >
        <div className="space-y-4">
          {errorMessage && (
            <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
              {errorMessage}
            </div>
          )}

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Question *
            </label>
            <Input
              type="text"
              placeholder="What are your business hours?"
              value={qaFormData.question}
              onChange={(e) => setQAFormData({ ...qaFormData, question: e.target.value })}
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Answer *
            </label>
            <TextArea
              placeholder="We're open Monday-Friday, 9am-5pm EST"
              value={qaFormData.answer}
              onChange={(e) => setQAFormData({ ...qaFormData, answer: e.target.value })}
              rows={4}
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Priority
            </label>
            <Input
              type="number"
              min="0"
              max="1000"
              value={qaFormData.priority ?? ''}
              onChange={(e) => {
                const rawValue = e.target.value
                if (rawValue === '') {
                  setQAFormData({ ...qaFormData, priority: undefined })
                  return
                }

                const parsedValue = parseInt(rawValue, 10)
                if (Number.isNaN(parsedValue)) {
                  return
                }

                setQAFormData({
                  ...qaFormData,
                  priority: Math.min(1000, Math.max(0, parsedValue)),
                })
              }}
            />
            <p className="mt-1 text-xs text-slate-500">
              Higher priority Q&As are checked first (default: 100)
            </p>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Category (optional)
            </label>
            <Input
              type="text"
              placeholder="hours"
              value={qaFormData.category || ''}
              onChange={(e) => setQAFormData({ ...qaFormData, category: e.target.value })}
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Keywords (optional)
            </label>
            <Input
              type="text"
              placeholder="opening,time,schedule"
              value={qaFormData.keywords || ''}
              onChange={(e) => setQAFormData({ ...qaFormData, keywords: e.target.value })}
            />
            <p className="mt-1 text-xs text-slate-500">
              Comma-separated keywords for better matching
            </p>
          </div>

          <div className="flex gap-3 pt-4">
            <Button
              onClick={handleCreateQA}
              disabled={!qaFormData.question || !qaFormData.answer || createQA.isPending}
              className="flex-1"
            >
              {createQA.isPending ? 'Creating...' : 'Create Q&A'}
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setIsQAModalOpen(false)
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
