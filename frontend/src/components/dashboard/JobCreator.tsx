import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api'
import type { CreateTaskRequest, Job, ModelConfig } from '../../lib/api'
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
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.getHealth(),
  })
  const [form, setForm] = useState<CreateTaskRequest>({
    task: '',
    repo_owner: '',
    repo_name: '',
    branch_base: 'main',
    budgetUsd: 5,
    maxRequests: 300,
    maxMinutes: 720,
    modelCTO: '',
    modelCoder: '',
  })
  const [localError, setLocalError] = useState<string | null>(null)

  const ctoModel = useMemo<ModelConfig | undefined>(
    () => models?.find((model) => model.id === 'cto'),
    [models],
  )
  const coderModel = useMemo<ModelConfig | undefined>(
    () => models?.find((model) => model.id === 'coder'),
    [models],
  )

  useEffect(() => {
    if (health?.budgetGuard) {
      setForm((prev) => ({
        ...prev,
        budgetUsd: health.budgetGuard.budget_usd_max,
        maxRequests: health.budgetGuard.max_requests,
        maxMinutes: health.budgetGuard.max_wallclock_minutes,
      }))
    }
  }, [health])

  useEffect(() => {
    setForm((prev) => ({
      ...prev,
      modelCTO: prev.modelCTO || ctoModel?.selectedVariant || '',
      modelCoder: prev.modelCoder || coderModel?.selectedVariant || '',
    }))
  }, [ctoModel, coderModel])

  const mutation = useMutation({
    mutationFn: (payload: CreateTaskRequest) => apiClient.createTask(payload),
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setLocalError(null)
      onJobCreated?.(job)
    },
  })

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!form.task.trim()) {
      setLocalError('Please describe the task the agents should execute.')
      return
    }
    if (!form.repo_owner.trim() || !form.repo_name.trim()) {
      setLocalError('Repository owner and name are required.')
      return
    }
    mutation.mutate(form)
  }

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="items-start justify-between">
        <div>
          <CardTitle>Create Task</CardTitle>
          <CardDescription>
            Dispatch a new autonomous run with repository context and guardrails.
          </CardDescription>
        </div>
      </CardHeader>
      <form onSubmit={handleSubmit} className="flex flex-1 flex-col gap-4">
        <div className="space-y-3">
          <label className="space-y-1 text-sm">
            <span className="text-slate-300">Task description</span>
            <TextArea
              className="h-28"
              value={form.task}
              onChange={(event) => {
                setLocalError(null)
                setForm((prev) => ({ ...prev, task: event.target.value }))
              }}
              placeholder="Outline the objective for the orchestrator to complete."
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="space-y-1 text-sm">
              <span className="text-slate-300">Repository owner</span>
              <Input
                value={form.repo_owner}
                onChange={(event) => {
                  setLocalError(null)
                  setForm((prev) => ({ ...prev, repo_owner: event.target.value }))
                }}
                placeholder="auto-dev"
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate-300">Repository name</span>
              <Input
                value={form.repo_name}
                onChange={(event) => {
                  setLocalError(null)
                  setForm((prev) => ({ ...prev, repo_name: event.target.value }))
                }}
                placeholder="project-repo"
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate-300">Base branch</span>
              <Input
                value={form.branch_base}
                onChange={(event) => {
                  setLocalError(null)
                  setForm((prev) => ({ ...prev, branch_base: event.target.value }))
                }}
                placeholder="main"
              />
            </label>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="space-y-1 text-sm">
              <span className="text-slate-300">Budget (USD)</span>
              <Input
                type="number"
                min={0}
                step={0.5}
                value={form.budgetUsd}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, budgetUsd: Number(event.target.value) }))
                }
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate-300">Max requests</span>
              <Input
                type="number"
                min={1}
                value={form.maxRequests}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, maxRequests: Number(event.target.value) }))
                }
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate-300">Max minutes</span>
              <Input
                type="number"
                min={1}
                value={form.maxMinutes}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, maxMinutes: Number(event.target.value) }))
                }
              />
            </label>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="flex items-center justify-between text-slate-300">
                CTO model
                {modelsLoading && <Spinner size="sm" />}
              </span>
              <select
                value={form.modelCTO}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, modelCTO: event.target.value }))
                }
                className="w-full rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/60"
              >
                <option value="">Use backend default</option>
                {(ctoModel?.variants ?? []).map((variant) => (
                  <option key={variant.id} value={variant.id}>
                    {variant.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate-300">Coder model</span>
              <select
                value={form.modelCoder}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, modelCoder: event.target.value }))
                }
                className="w-full rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/60"
              >
                <option value="">Use backend default</option>
                {(coderModel?.variants ?? []).map((variant) => (
                  <option key={variant.id} value={variant.id}>
                    {variant.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
        {(localError || mutation.isError) && (
          <p className="text-sm text-rose-300">{localError ?? (mutation.error as Error).message}</p>
        )}
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Creating…' : 'Start orchestration'}
        </Button>
      </form>
    </Card>
  )
}
