import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createCustomQA,
  createWebsite,
  deleteCustomQA,
  deleteWebsite,
  getAnalytics,
  getWebsite,
  listCustomQAs,
  listWebsites,
  triggerCrawl,
  updateWebsite,
  type CustomQACreate,
  type WebsiteCreate,
  type WebsiteUpdate,
} from './api'

// Query Keys
export const ragKeys = {
  all: ['rag'] as const,
  websites: () => [...ragKeys.all, 'websites'] as const,
  website: (id: string) => [...ragKeys.websites(), id] as const,
  qas: (websiteId: string) => [...ragKeys.website(websiteId), 'qas'] as const,
  analytics: (websiteId: string) => [...ragKeys.website(websiteId), 'analytics'] as const,
}

// Websites
export function useWebsites() {
  return useQuery({
    queryKey: ragKeys.websites(),
    queryFn: listWebsites,
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data || data.length === 0) {
        return false
      }

      return data.some((website) => website.status === 'PENDING' || website.status === 'CRAWLING')
        ? 5000
        : false
    },
    refetchIntervalInBackground: true,
  })
}

export function useWebsite(websiteId: string) {
  return useQuery({
    queryKey: ragKeys.website(websiteId),
    queryFn: () => getWebsite(websiteId),
    enabled: !!websiteId,
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) {
        return false
      }

      return data.status === 'READY' || data.status === 'ERROR' ? false : 4000
    },
    refetchIntervalInBackground: true,
  })
}

export function useCreateWebsite() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: WebsiteCreate) => createWebsite(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ragKeys.websites() })
    },
  })
}

export function useUpdateWebsite(websiteId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: WebsiteUpdate) => updateWebsite(websiteId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ragKeys.website(websiteId) })
      queryClient.invalidateQueries({ queryKey: ragKeys.websites() })
    },
  })
}

export function useDeleteWebsite() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (websiteId: string) => deleteWebsite(websiteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ragKeys.websites() })
    },
  })
}

export function useTriggerCrawl(websiteId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => triggerCrawl(websiteId),
    onSuccess: () => {
      // Invalidate to refresh status
      queryClient.invalidateQueries({ queryKey: ragKeys.website(websiteId) })
      queryClient.invalidateQueries({ queryKey: ragKeys.websites() })
    },
  })
}

// Custom Q&As
export function useCustomQAs(websiteId: string) {
  return useQuery({
    queryKey: ragKeys.qas(websiteId),
    queryFn: () => listCustomQAs(websiteId),
    enabled: !!websiteId,
  })
}

export function useCreateCustomQA(websiteId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CustomQACreate) => createCustomQA(websiteId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ragKeys.qas(websiteId) })
    },
  })
}

export function useDeleteCustomQA(websiteId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (qaId: string) => deleteCustomQA(websiteId, qaId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ragKeys.qas(websiteId) })
    },
  })
}

// Analytics
export function useAnalytics(websiteId: string) {
  return useQuery({
    queryKey: ragKeys.analytics(websiteId),
    queryFn: () => getAnalytics(websiteId),
    enabled: !!websiteId,
  })
}
