import { useState } from 'react'
import { usePaymentHistory } from '@/features/billing/hooks'
import { Card } from '@/components/ui/card'
import { formatDistanceToNow } from 'date-fns'

export default function PaymentHistoryPage() {
  const [page, setPage] = useState(0)
  const limit = 20
  const offset = page * limit

  const { data, isLoading, error } = usePaymentHistory(limit, offset)

  const formatAmount = (amountCents: number, currency: string) => {
    const amount = amountCents / 100
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency.toUpperCase(),
    }).format(amount)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'succeeded':
        return 'text-green-400'
      case 'pending':
        return 'text-yellow-400'
      case 'failed':
        return 'text-red-400'
      case 'refunded':
        return 'text-gray-400'
      default:
        return 'text-gray-400'
    }
  }

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'succeeded':
        return 'bg-green-500/10 text-green-400 border-green-500/20'
      case 'pending':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
      case 'failed':
        return 'bg-red-500/10 text-red-400 border-red-500/20'
      case 'refunded':
        return 'bg-gray-500/10 text-gray-400 border-gray-500/20'
      default:
        return 'bg-gray-500/10 text-gray-400 border-gray-500/20'
    }
  }

  return (
    <div className="container mx-auto max-w-7xl px-4 py-8">
      <div className="mb-8">
        <h1 className="mb-2 text-3xl font-bold text-white">Payment History</h1>
        <p className="text-gray-400">View all your payment transactions</p>
      </div>

      <Card>
        <div className="p-6">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
            </div>
          )}

          {error && (
            <div className="rounded-lg bg-red-500/10 p-4 text-red-400">
              Failed to load payment history. Please try again later.
            </div>
          )}

          {data && data.transactions.length === 0 && (
            <div className="py-12 text-center">
              <p className="text-gray-400">No payment history yet</p>
            </div>
          )}

          {data && data.transactions.length > 0 && (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-800">
                      <th className="pb-4 text-left text-sm font-semibold text-gray-400">
                        Date
                      </th>
                      <th className="pb-4 text-left text-sm font-semibold text-gray-400">
                        Description
                      </th>
                      <th className="pb-4 text-left text-sm font-semibold text-gray-400">
                        Amount
                      </th>
                      <th className="pb-4 text-left text-sm font-semibold text-gray-400">
                        Status
                      </th>
                      <th className="pb-4 text-left text-sm font-semibold text-gray-400">
                        Payment Method
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.transactions.map((transaction) => (
                      <tr
                        key={transaction.id}
                        className="border-b border-gray-800/50 last:border-0"
                      >
                        <td className="py-4 text-sm text-gray-300">
                          <div>{new Date(transaction.created_at).toLocaleDateString()}</div>
                          <div className="text-xs text-gray-500">
                            {formatDistanceToNow(new Date(transaction.created_at), {
                              addSuffix: true,
                            })}
                          </div>
                        </td>
                        <td className="py-4 text-sm text-white">
                          {transaction.description || 'Payment'}
                          {transaction.failure_reason && (
                            <div className="mt-1 text-xs text-red-400">
                              {transaction.failure_reason}
                            </div>
                          )}
                        </td>
                        <td className="py-4 text-sm font-semibold text-white">
                          {formatAmount(transaction.amount_cents, transaction.currency)}
                        </td>
                        <td className="py-4 text-sm">
                          <span
                            className={`inline-flex rounded-full border px-3 py-1 text-xs font-medium ${getStatusBadgeColor(transaction.status)}`}
                          >
                            {transaction.status.charAt(0).toUpperCase() +
                              transaction.status.slice(1)}
                          </span>
                        </td>
                        <td className="py-4 text-sm text-gray-300">
                          {transaction.payment_method && transaction.payment_method_last4 ? (
                            <div>
                              <div className="capitalize">{transaction.payment_method}</div>
                              <div className="text-xs text-gray-500">
                                •••• {transaction.payment_method_last4}
                              </div>
                            </div>
                          ) : (
                            <span className="text-gray-500">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="mt-6 flex items-center justify-between border-t border-gray-800 pt-6">
                <div className="text-sm text-gray-400">
                  Showing {offset + 1} to {Math.min(offset + limit, data.total)} of{' '}
                  {data.total} transactions
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(Math.max(0, page - 1))}
                    disabled={page === 0}
                    className="rounded-lg bg-gray-800 px-4 py-2 text-sm font-medium text-white transition hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage(page + 1)}
                    disabled={offset + limit >= data.total}
                    className="rounded-lg bg-gray-800 px-4 py-2 text-sm font-medium text-white transition hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </Card>
    </div>
  )
}
