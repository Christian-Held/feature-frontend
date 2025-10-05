export function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const dimension = size === 'sm' ? 16 : size === 'lg' ? 32 : 24
  return (
    <svg
      className="animate-spin text-sky-400"
      width={dimension}
      height={dimension}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle
        className="opacity-20"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        d="M4 12a8 8 0 018-8"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
      />
    </svg>
  )
}
