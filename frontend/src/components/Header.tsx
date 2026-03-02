import { useEffect, useState } from "react";
import { getStats } from "../api";
import type { IndexStats } from "../api";

export default function Header() {
  const [stats, setStats] = useState<IndexStats | null>(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => {});
  }, []);

  return (
    <header className="bg-gray-900 border-b border-gray-700 px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="text-2xl font-bold text-white tracking-tight">
            <span className="text-indigo-400">Legacy</span>Lens
          </div>
          <span className="text-xs text-gray-400 bg-gray-800 px-2 py-1 rounded">
            LAPACK Explorer
          </span>
        </div>
        {stats && (
          <div className="text-sm text-gray-400">
            {stats.total_vectors.toLocaleString()} vectors indexed
          </div>
        )}
      </div>
    </header>
  );
}
