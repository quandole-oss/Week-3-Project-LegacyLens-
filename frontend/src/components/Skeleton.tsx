export function AnswerSkeleton() {
  return (
    <div className="bg-terminal-black border border-terminal-border p-3 font-mono">
      <div className="tui-row flex items-center gap-2 mb-2 border-b border-terminal-border">
        <h3 className="text-sm text-amber uppercase tracking-wide crt-glow-amber">
          === OUTPUT ===
        </h3>
      </div>
      <div className="space-y-2 text-phosphor pt-2">
        <div className="flex items-center gap-1 animate-pulse">
          <span className="uppercase">Loading response</span>
          <span className="blink-cursor inline-block w-2 h-4 bg-phosphor" />
        </div>
        <div className="text-phosphor-dim font-mono animate-pulse skeleton-bar">
          ████████████████████████████████████████
        </div>
        <div className="text-phosphor-dim font-mono animate-pulse skeleton-bar">
          ██████████████████████████████
        </div>
        <div className="text-phosphor-dim font-mono animate-pulse skeleton-bar">
          ████████████████████
        </div>
      </div>
    </div>
  );
}

export function SourceSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-0 font-mono">
      <h3 className="text-sm text-amber uppercase tracking-wide crt-glow-amber mb-2">
        === SOURCES ===
      </h3>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="bg-terminal-black border border-terminal-border overflow-hidden animate-pulse"
        >
          <div className="tui-row flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs border border-terminal-border text-amber px-1 py-0">
                #{i + 1}
              </span>
              <div>
                <div className="text-sm text-phosphor-dim uppercase">Loading...</div>
                <div className="text-xs text-phosphor-dim">---</div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-xs border border-terminal-border text-phosphor-dim px-1 py-0 uppercase">
                ---
              </span>
              <span className="text-xs text-phosphor-dim font-mono">
                [--.--%]
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
