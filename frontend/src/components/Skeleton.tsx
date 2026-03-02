export function AnswerSkeleton() {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 animate-pulse">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-4 w-16 bg-gray-700 rounded" />
        <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse" />
      </div>
      <div className="space-y-3">
        <div className="h-3 bg-gray-700 rounded w-full" />
        <div className="h-3 bg-gray-700 rounded w-5/6" />
        <div className="h-3 bg-gray-700 rounded w-4/6" />
        <div className="h-3 bg-gray-700 rounded w-full" />
        <div className="h-3 bg-gray-700 rounded w-3/6" />
      </div>
    </div>
  );
}

export function SourceSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3">
      <div className="h-4 w-24 bg-gray-700 rounded animate-pulse" />
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden animate-pulse"
        >
          <div className="flex items-center justify-between px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="h-5 w-6 bg-gray-700 rounded" />
              <div className="space-y-1">
                <div className="h-4 w-24 bg-gray-700 rounded" />
                <div className="h-3 w-40 bg-gray-700 rounded" />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-5 w-16 bg-gray-700 rounded" />
              <div className="h-5 w-12 bg-gray-700 rounded" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
