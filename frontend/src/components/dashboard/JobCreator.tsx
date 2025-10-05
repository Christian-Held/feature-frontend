import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api'
import type { CreateJobRequest, Job, ModelConfig } from '../../lib/api'
import { Button } from '../ui/Button'
import { Card, CardDescription, CardHeader, CardTitle } from '../ui/Card'
import { Input } from '../ui/Input'
import { TextArea } from '../ui/TextArea'
import { Spinner } from '../ui/Spinner'
import { queryClient } from '../../lib/queryClient'

interface JobCreatorProps {
  onJobCreated?(job: Job): void
}

export function JobCreator({ onJobCreated }: JobCreatorProps) {
  const { data: models, isLoading: modelsLoading } = useQuery({
    queryKey: ['models'],
    queryFn: () => apiClient.listModels(),
  })
  const [form, setForm] = useState({
    name: 'New inference job',
    modelId: '',
    payload: '{\n  "prompt": "Hello"\n}',
  })
  const [localError, setLocalError] = useState<string | null>(null)

  const selectedModel = useMemo<ModelConfig | undefined>(
    () => models?.find((model) => model.id === form.modelId) ?? models?.[0],
    [models, form.modelId],
  )

  useEffect(() => {
    if (models && models.length > 0 && !form.modelId) {
      setForm((prev) => ({ ...prev, modelId: models[0].id }))
    }
  }, [models, form.modelId])

  const mutation = useMutation({
    mutationFn: (payload: CreateJobRequest) => apiClient.createJob(payload),
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setLocalError(null)
      onJobCreated?.(job)
    },
  })

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!selectedModel) return
    let payload: Record<string, unknown> = {}
    try {
      payload = JSON.parse(form.payload)
    } catch {
      setLocalError('Payload muss gültiges JSON sein.')
      return
    }
    mutation.mutate({ name: form.name, modelId: selectedModel.id, payload })
  }

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="items-start justify-between">
        <div>
          <CardTitle>Create Job</CardTitle>
          <CardDescription>Trigger inference runs across your configured models.</CardDescription>
        </div>
      </CardHeader>
      <form onSubmit={handleSubmit} className="flex flex-1 flex-col gap-4">
        <div className="space-y-3">
          <label className="space-y-1 text-sm">
            <span className="text-slate-300">Job name</span>
            <Input
              value={form.name}
              onChange={(event) => {
                setLocalError(null)
                setForm((prev) => ({ ...prev, name: event.target.value }))
              }}
              placeholder="Marketing copy generation"
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-slate-300">Model</span>
            <select
              value={selectedModel?.id ?? ''}
              onChange={(event) => {
                setLocalError(null)
                setForm((prev) => ({ ...prev, modelId: event.target.value || models?.[0]?.id || '' }))
              }}
              className="w-full rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/60"
            >
              {(models ?? []).map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name} · {model.provider}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1 text-sm">
            <span className="flex items-center justify-between text-slate-300">
              Payload
              {modelsLoading && <Spinner size="sm" />}
            </span>
            <TextArea
              className="h-40 font-mono"
              value={form.payload}
              onChange={(event) => {
                setLocalError(null)
                setForm((prev) => ({ ...prev, payload: event.target.value }))
              }}
            />
          </label>
        </div>
        {(localError || mutation.isError) && (
          <p className="text-sm text-rose-300">{localError ?? (mutation.error as Error).message}</p>
        )}
        <Button type="submit" disabled={mutation.isPending || !selectedModel}>
          {mutation.isPending ? 'Creating…' : 'Start job'}
        </Button>
      </form>
    </Card>
  )
}
