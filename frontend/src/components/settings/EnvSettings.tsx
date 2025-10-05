import { useMutation, useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api'
import type { EnvVariable } from '../../lib/api'
import { Card, CardDescription, CardHeader, CardTitle } from '../ui/Card'
import { Input } from '../ui/Input'
import { Button } from '../ui/Button'
import { Spinner } from '../ui/Spinner'
import { queryClient } from '../../lib/queryClient'
import { useState } from 'react'

export function EnvSettings() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['env'],
    queryFn: () => apiClient.getEnvVariables(),
  })

  const mutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) => apiClient.updateEnvVariable(key, value),
    onSuccess: (_, variables) => {
      queryClient.setQueryData<EnvVariable[]>(['env'], (current = []) =>
        current.map((item) => (item.key === variables.key ? { ...item, value: variables.value } : item)),
      )
      setDrafts((prev) => {
        const next = { ...prev }
        delete next[variables.key]
        return next
      })
    },
  })

  const [drafts, setDrafts] = useState<Record<string, string>>({})

  return (
    <Card>
      <CardHeader className="items-start justify-between">
        <div>
          <CardTitle>Environment Variables</CardTitle>
          <CardDescription>Keep runtime configuration synchronized with the backend.</CardDescription>
        </div>
      </CardHeader>
      {isLoading && (
        <div className="flex h-40 items-center justify-center">
          <Spinner />
        </div>
      )}
      {isError && (
        <div className="space-y-2 text-sm text-rose-300">
          <p>Failed to load environment variables.</p>
          <p className="text-xs text-rose-400/80">{(error as Error).message}</p>
        </div>
      )}
      {!isLoading && !isError && (
        <div className="space-y-4">
          {(data ?? []).map((env) => {
            const pendingValue = drafts[env.key] ?? env.value
            return (
              <div key={env.key} className="rounded-xl border border-slate-800/80 bg-slate-950/50 p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-white">{env.key}</p>
                    {env.description && <p className="text-xs text-slate-400">{env.description}</p>}
                  </div>
                  <div className="flex items-center gap-3">
                    <Input
                      type={env.isSecret ? 'password' : 'text'}
                      value={pendingValue}
                      onChange={(event) =>
                        setDrafts((prev) => ({ ...prev, [env.key]: event.target.value }))
                      }
                      className="w-64"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      disabled={mutation.isPending || pendingValue === env.value}
                      onClick={() =>
                        mutation.mutate({ key: env.key, value: drafts[env.key] ?? env.value })
                      }
                    >
                      {mutation.isPending ? 'Saving…' : 'Save'}
                    </Button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}
