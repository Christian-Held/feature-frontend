import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { apiClient } from '../../lib/api'
import type { ModelConfig } from '../../lib/api'
import { Card, CardDescription, CardHeader, CardTitle } from '../ui/Card'
import { Input } from '../ui/Input'
import { Button } from '../ui/Button'
import { Spinner } from '../ui/Spinner'
import { queryClient } from '../../lib/queryClient'

export function ModelSettings() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['models'],
    queryFn: () => apiClient.listModels(),
  })

  const [drafts, setDrafts] = useState<Record<string, ModelConfig['parameters']>>({})
  const [selectedVariants, setSelectedVariants] = useState<Record<string, string>>({})

  const mutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<ModelConfig> }) =>
      apiClient.updateModelConfig(id, payload),
    onSuccess: (model) => {
      queryClient.setQueryData<ModelConfig[]>(['models'], (current = []) =>
        current.map((item) => (item.id === model.id ? model : item)),
      )
      setDrafts((prev) => {
        const next = { ...prev }
        delete next[model.id]
        return next
      })
      setSelectedVariants((prev) => {
        const next = { ...prev }
        delete next[model.id]
        return next
      })
    },
  })

  const handleChange = (model: ModelConfig, key: string, value: string) => {
    setDrafts((prev) => ({
      ...prev,
      [model.id]: {
        ...(prev[model.id] ?? model.parameters),
        [key]: value,
      },
    }))
  }

  const handleSave = (model: ModelConfig) => {
    const nextParameters = drafts[model.id] ?? model.parameters ?? {}
    const nextVariant = selectedVariants[model.id] ?? model.selectedVariant
    mutation.mutate({
      id: model.id,
      payload: {
        parameters: nextParameters,
        ...(nextVariant ? { selectedVariant: nextVariant } : {}),
      },
    })
  }

  return (
    <Card>
      <CardHeader className="items-start justify-between">
        <div>
          <CardTitle>Model Catalog</CardTitle>
          <CardDescription>Manage provider options, variants and default parameters.</CardDescription>
        </div>
      </CardHeader>
      {isLoading && (
        <div className="flex h-40 items-center justify-center">
          <Spinner />
        </div>
      )}
      {isError && (
        <div className="space-y-2 text-sm text-rose-300">
          <p>Failed to load models.</p>
          <p className="text-xs text-rose-400/80">{(error as Error).message}</p>
        </div>
      )}
      {!isLoading && !isError && (
        <div className="space-y-6">
          {(data ?? []).map((model) => {
            const parameters = drafts[model.id] ?? model.parameters ?? {}
            const selectedVariant = selectedVariants[model.id] ?? model.selectedVariant ?? model.variants[0]?.id ?? ''
            return (
              <div key={model.id} className="rounded-2xl border border-slate-800/80 bg-slate-950/60 p-5">
                <div className="flex flex-col gap-2 border-b border-slate-800/60 pb-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-base font-semibold text-white">{model.name}</p>
                    <p className="text-xs uppercase tracking-wide text-slate-500">{model.provider}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <label className="text-xs text-slate-400">
                      Variant
                      <select
                        value={selectedVariant}
                        onChange={(event) =>
                          setSelectedVariants((prev) => ({ ...prev, [model.id]: event.target.value }))
                        }
                        className="mt-1 w-48 rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/60"
                      >
                        {model.variants.map((variant) => (
                          <option key={variant.id} value={variant.id}>
                            {variant.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <Button
                      variant="outline"
                      disabled={mutation.isPending}
                      onClick={() => handleSave(model)}
                    >
                      {mutation.isPending ? 'Saving…' : 'Save changes'}
                    </Button>
                  </div>
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  {Object.entries(parameters).map(([key, value]) => (
                    <label key={key} className="space-y-1 text-xs text-slate-400">
                      <span className="text-slate-300">{key}</span>
                      <Input
                        value={String(value)}
                        onChange={(event) => handleChange(model, key, event.target.value)}
                      />
                    </label>
                  ))}
                  {Object.keys(parameters).length === 0 && (
                    <p className="text-sm text-slate-500">This model has no configurable parameters.</p>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}
