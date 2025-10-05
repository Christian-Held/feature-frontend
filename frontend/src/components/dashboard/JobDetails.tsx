import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api'
import { Badge } from '../ui/Badge'
import { Card, CardDescription, CardHeader, CardTitle } from '../ui/Card'
import { TextArea } from '../ui/TextArea'
import { Spinner } from '../ui/Spinner'

interface JobDetailsProps {
  jobId?: string
}

export function JobDetails({ jobId }: JobDetailsProps) {
  const { data: job, isLoading, isError, error } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => apiClient.getJob(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: 5_000,
  })

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="items-start justify-between">
        <div>
          <CardTitle>Job Details</CardTitle>
          <CardDescription>Review inputs, outputs and live logs for the selected run.</CardDescription>
        </div>
        {job && <Badge variant={job.status}>{job.status}</Badge>}
      </CardHeader>
      {!jobId ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-sm text-slate-400">
          <p>Select a job to inspect details.</p>
          <p className="text-xs text-slate-500">Create a job or choose one from the queue.</p>
        </div>
      ) : isLoading ? (
        <div className="flex flex-1 items-center justify-center">
          <Spinner />
        </div>
      ) : isError ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-sm text-rose-300">
          <p>Failed to load job details.</p>
          <p className="text-xs text-rose-400/80">{(error as Error).message}</p>
        </div>
      ) : !job ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-sm text-slate-400">
          <p>Job not found.</p>
        </div>
      ) : (
        <div className="flex flex-1 flex-col gap-4 overflow-hidden">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4">
              <h4 className="text-sm font-semibold text-white">Metadata</h4>
              <dl className="mt-3 space-y-2 text-xs text-slate-300">
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-500">Job ID</dt>
                  <dd className="font-mono">{job.id}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-500">Created</dt>
                  <dd>{new Date(job.createdAt).toLocaleString()}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-500">Updated</dt>
                  <dd>{new Date(job.updatedAt).toLocaleString()}</dd>
                </div>
              </dl>
            </div>
            <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4">
              <h4 className="text-sm font-semibold text-white">Input Payload</h4>
              <pre className="mt-3 max-h-40 overflow-auto rounded-lg bg-slate-900/80 p-3 text-xs text-slate-300">
                {JSON.stringify(job.input ?? {}, null, 2)}
              </pre>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4">
              <h4 className="text-sm font-semibold text-white">Output</h4>
              <TextArea className="mt-3 h-40" readOnly value={job.output ?? 'Waiting for output…'} />
            </div>
            <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4">
              <h4 className="text-sm font-semibold text-white">Logs</h4>
              <div className="mt-3 max-h-40 space-y-1 overflow-auto rounded-lg bg-slate-900/70 p-3 text-xs font-mono text-slate-300">
                {(job.logs ?? ['Logs will stream as the job runs.']).map((line, index) => (
                  <p key={`${line}-${index}`}>{line}</p>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}
