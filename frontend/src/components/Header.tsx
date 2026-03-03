import { useEffect, useState } from "react";
import { getStats } from "../api";
import type { IndexStats } from "../api";

export default function Header() {
  const [stats, setStats] = useState<IndexStats | null>(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => {});
  }, []);

  return (
    <header className="bg-terminal-black border-b border-terminal-border px-4 py-3 font-mono">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="text-2xl crt-glow tracking-tight uppercase">
            <span className="text-amber crt-glow-amber">Legacy</span><span className="text-phosphor">Lens</span>
          </div>
          <span className="text-xs text-phosphor border border-terminal-border px-2 py-0.5 uppercase">
            LAPACK EXPLORER
          </span>
        </div>
        {stats && (
          <div className="text-sm text-phosphor crt-glow uppercase">
            [ {stats.total_vectors.toLocaleString()} VECTORS INDEXED ]
          </div>
        )}
      </div>
    </header>
  );
}
