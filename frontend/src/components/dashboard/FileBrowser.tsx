import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api'
import type { FileEntry } from '../../lib/api'
import { Card, CardDescription, CardHeader, CardTitle } from '../ui/Card'
import { Spinner } from '../ui/Spinner'
import { Button } from '../ui/Button'
import { FolderIcon, DocumentIcon, ArrowLeftIcon } from '@heroicons/react/24/outline'

interface FileBrowserProps {
  onOpenFile?(file: FileEntry): void
}

function getParentPath(path: string) {
  if (!path || path === '/') return null
  const segments = path.split('/').filter(Boolean)
  segments.pop()
  return '/' + segments.join('/')
}

export function FileBrowser({ onOpenFile }: FileBrowserProps) {
  const [path, setPath] = useState('/')
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['files', path],
    queryFn: () => apiClient.listFiles(path),
  })

  const parent = getParentPath(path)

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="items-start justify-between">
        <div>
          <CardTitle>File Browser</CardTitle>
          <CardDescription>Inspect artifacts and logs produced by your jobs.</CardDescription>
        </div>
        <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
          Refresh
        </Button>
      </CardHeader>
      <div className="border border-slate-800/80 bg-slate-950/50">
        <div className="flex items-center justify-between border-b border-slate-800/80 px-4 py-2 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="font-mono text-slate-300">{path}</span>
          </div>
          {parent && (
            <button
              onClick={() => setPath(parent)}
              className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-slate-300 transition hover:bg-slate-800/70"
            >
              <ArrowLeftIcon className="h-4 w-4" /> Up
            </button>
          )}
        </div>
        <div className="max-h-80 overflow-auto">
          {isLoading && (
            <div className="flex h-40 items-center justify-center">
              <Spinner />
            </div>
          )}
          {isError && (
            <div className="space-y-2 p-4 text-sm text-rose-300">
              <p>Failed to load files.</p>
              <p className="text-xs text-rose-400/80">{(error as Error).message}</p>
            </div>
          )}
          {!isLoading && !isError && (
            <ul className="divide-y divide-slate-800/80">
              {(data ?? []).map((entry) => {
                const displayName = entry.name || entry.path.split('/').filter(Boolean).pop() || entry.path
                return (
                  <li
                    key={entry.path}
                    className="flex items-center justify-between gap-3 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800/60"
                  >
                    <button
                      onClick={() =>
                        entry.type === 'directory'
                          ? setPath(entry.path)
                          : onOpenFile?.(entry)
                      }
                      className="flex flex-1 items-center gap-3 text-left"
                    >
                      {entry.type === 'directory' ? (
                        <FolderIcon className="h-5 w-5 text-sky-400" />
                      ) : (
                        <DocumentIcon className="h-5 w-5 text-indigo-400" />
                      )}
                      <div>
                        <p className="text-sm text-white">{displayName}</p>
                        <p className="text-xs text-slate-500">
                          {entry.type === 'directory'
                            ? 'Folder'
                            : `${
                                entry.size !== undefined && entry.size !== null
                                  ? (entry.size / 1024).toFixed(1)
                                  : '0.0'
                              } KB`}
                        </p>
                      </div>
                    </button>
                    <span className="text-xs text-slate-500">
                      {new Date(entry.modifiedAt).toLocaleString()}
                    </span>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      </div>
    </Card>
  )
}
