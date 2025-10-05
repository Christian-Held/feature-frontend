import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { apiClient } from '../../lib/api'
import type { Job } from '../../lib/api'
import { Badge } from '../ui/Badge'
import { Spinner } from '../ui/Spinner'
import { Card, CardDescription, CardHeader, CardTitle } from '../ui/Card'

interface JobListProps {
  selectedJobId?: string
  onSelect(job: Job): void
}

const statusOrder: Record<Job['status'], number> = {
  running: 0,
  pending: 1,
  completed: 2,
  failed: 3,
  cancelled: 4,
}

export function JobList({ selectedJobId, onSelect }: JobListProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => apiClient.listJobs(),
    refetchInterval: 60_000,
  })

  const jobTimestamp = (job: Job) => new Date(job.updated_at ?? job.created_at ?? 0).getTime()

  const jobs = useMemo(() => {
    if (!data) return []
    return [...data].sort((a, b) => {
      const statusDiff = statusOrder[a.status] - statusOrder[b.status]
      if (statusDiff !== 0) return statusDiff
      const updatedA = jobTimestamp(a)
      const updatedB = jobTimestamp(b)
      return updatedB - updatedA
    })
  }, [data])

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="items-center justify-between">
        <div>
          <CardTitle>Job Queue</CardTitle>
          <CardDescription>Monitor current and historical workloads.</CardDescription>
        </div>
        <Badge variant="default">{jobs.length} jobs</Badge>
      </CardHeader>
      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="flex h-48 items-center justify-center text-sm text-slate-400">
            <Spinner />
          </div>
        )}
        {isError && (
          <div className="space-y-2 p-4 text-sm text-rose-300">
            <p>Failed to load jobs.</p>
            <p className="text-xs text-rose-400/80">{(error as Error).message}</p>
          </div>
        )}
        {!isLoading && !isError && jobs.length === 0 && (
          <div className="flex h-48 flex-col items-center justify-center gap-1 text-sm text-slate-400">
            <p>No jobs yet.</p>
            <p className="text-xs text-slate-500">Create your first orchestration task to see it here.</p>
          </div>
        )}
        <ul className="space-y-2">
          {jobs.map((job) => (
            <li key={job.id}>
              <button
                onClick={() => onSelect(job)}
                className={`group flex w-full flex-col gap-2 rounded-xl border border-slate-800/80 bg-slate-900/60 px-4 py-3 text-left transition hover:border-slate-600 hover:bg-slate-800/70 ${
                  selectedJobId === job.id ? 'border-sky-500/60 bg-slate-800' : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-white">{job.task}</p>
                  <Badge variant={job.status}>{job.status}</Badge>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <p>
                    Updated {new Date(job.updated_at ?? job.created_at ?? Date.now()).toLocaleTimeString()}
                  </p>
                  {typeof job.progress === 'number' && (
                    <span className="text-slate-300">{Math.round(job.progress * 100)}%</span>
                  )}
                </div>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </Card>
  )
}
