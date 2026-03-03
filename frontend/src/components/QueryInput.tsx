import { useState } from "react";
import type { FormEvent } from "react";

interface Props {
  onSubmit: (query: string) => void;
  isLoading: boolean;
  placeholder?: string;
}

const EXAMPLE_QUERIES = [
  "What does DGESV do?",
  "How does LU decomposition work in LAPACK?",
  "Find routines that solve eigenvalue problems",
  "Explain the BLAS matrix multiplication routine",
  "What are the dependencies of DGEEV?",
];

export default function QueryInput({ onSubmit, isLoading, placeholder }: Props) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
    }
  };

  return (
    <div className="w-full font-mono">
      <form onSubmit={handleSubmit} className="flex gap-2 items-center">
        <span className="text-phosphor crt-glow text-xl select-none">&gt;</span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder || "Ask about LAPACK code..."}
          className="cmd-input flex-1 text-phosphor px-1 py-2 font-mono text-lg"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="btn-bracket border border-phosphor text-phosphor px-4 py-2 font-mono uppercase disabled:border-terminal-border-dim disabled:text-terminal-border-dim disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <span className="flex items-center gap-1">
              <span className="blink-cursor inline-block w-2 h-4 bg-phosphor" />
              PROCESSING...
            </span>
          ) : (
            "[ SEARCH ]"
          )}
        </button>
      </form>
      <div className="mt-2 flex flex-wrap gap-1">
        {EXAMPLE_QUERIES.map((example) => (
          <button
            key={example}
            onClick={() => {
              setQuery(example);
              onSubmit(example);
            }}
            disabled={isLoading}
            className="btn-bracket text-xs text-phosphor border border-terminal-border-dim px-2 py-1 font-mono hover:border-phosphor disabled:opacity-50"
          >
            + {example} +
          </button>
        ))}
      </div>
    </div>
  );
}
