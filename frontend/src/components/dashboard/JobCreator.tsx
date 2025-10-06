import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
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

const DEFAULT_REPO_OWNER = 'Christian-Held'
const DEFAULT_REPO_NAME = 'test'
const DEFAULT_BRANCH = 'master'

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
    repo_owner: DEFAULT_REPO_OWNER,
    repo_name: DEFAULT_REPO_NAME,
    branch_base: DEFAULT_BRANCH,
    budgetUsd: 5,
    maxRequests: 300,
    maxMinutes: 720,
    modelCTO: '',
    modelCoder: '',
  })
  const [localError, setLocalError] = useState<string | null>(null)
  const [branchOptions, setBranchOptions] = useState<string[] | null>(null)
  const [branchFetchFailed, setBranchFetchFailed] = useState(false)
  const [branchLoading, setBranchLoading] = useState(false)
  const branchRequestId = useRef(0)

  const fetchBranches = useCallback(
    async (ownerValue: string, repoValue: string) => {
      const owner = ownerValue.trim()
      const repo = repoValue.trim()

      if (!owner || !repo) {
        branchRequestId.current += 1
        setBranchOptions(null)
        setBranchFetchFailed(false)
        setBranchLoading(false)
        return
      }

      const requestId = branchRequestId.current + 1
      branchRequestId.current = requestId
      setBranchLoading(true)

      try {
        const response = await apiClient.listBranches(owner, repo)
        if (branchRequestId.current !== requestId) {
          return
        }

        const branches = response.branches ?? []
        if (branches.length === 0) {
          setBranchOptions(null)
          setBranchFetchFailed(false)
          setBranchLoading(false)
          return
        }

        setBranchFetchFailed(false)
        setBranchOptions(branches)
        setBranchLoading(false)
        setForm((prev) => {
          const preferredBranch = branches.includes(DEFAULT_BRANCH)
            ? DEFAULT_BRANCH
            : branches.includes(prev.branch_base)
            ? prev.branch_base
            : branches[0]

          if (prev.branch_base === preferredBranch) {
            return prev
          }

          return { ...prev, branch_base: preferredBranch }
        })
      } catch {
        if (branchRequestId.current !== requestId) {
          return
        }

        setBranchOptions(null)
        setBranchFetchFailed(true)
        setBranchLoading(false)
      }
    },
    [],
  )

  useEffect(() => {
    fetchBranches(DEFAULT_REPO_OWNER, DEFAULT_REPO_NAME).catch(() => null)
  }, [fetchBranches])

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
                onBlur={(event) => {
                  fetchBranches(event.currentTarget.value, form.repo_name).catch(() => null)
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
                onKeyUp={(event) => {
                  fetchBranches(form.repo_owner, event.currentTarget.value).catch(() => null)
                }}
                onBlur={(event) => {
                  fetchBranches(form.repo_owner, event.currentTarget.value).catch(() => null)
                }}
                placeholder="project-repo"
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-slate-300">Base branch</span>
              {branchOptions && !branchFetchFailed ? (
                <select
                  value={form.branch_base}
                  onChange={(event) => {
                    setLocalError(null)
                    setForm((prev) => ({ ...prev, branch_base: event.target.value }))
                  }}
                  className="w-full rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/60"
                  disabled={branchLoading}
                >
                  {branchOptions.map((branch) => (
                    <option key={branch} value={branch}>
                      {branch}
                    </option>
                  ))}
                </select>
              ) : (
                <Input
                  value={form.branch_base}
                  onChange={(event) => {
                    setLocalError(null)
                    setForm((prev) => ({ ...prev, branch_base: event.target.value }))
                  }}
                  placeholder="main"
                />
              )}
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
