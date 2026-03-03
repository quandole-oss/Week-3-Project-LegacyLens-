import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import fortran from "react-syntax-highlighter/dist/esm/languages/hljs/fortran";
import terminalTheme from "../terminalTheme";
import type { Source, SearchResult } from "../api";
import { useState } from "react";

SyntaxHighlighter.registerLanguage("fortran", fortran);

interface Props {
  source: Source | SearchResult;
  index: number;
  expanded?: boolean;
}

export default function SourceCard({ source, index, expanded = false }: Props) {
  const [isExpanded, setIsExpanded] = useState(expanded);
  const snippet = "snippet" in source ? source.snippet : ("text" in source ? source.text : "");
  const score = source.score;

  return (
    <div className="bg-terminal-black border border-terminal-border overflow-hidden font-mono">
      <div
        className="tui-row flex items-center justify-between cursor-pointer border-b border-terminal-border hover:bg-terminal-green-muted/10"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs border border-terminal-border text-amber px-1 py-0 shrink-0">
            #{index + 1}
          </span>
          <span className="text-sm text-phosphor crt-glow truncate">
            {source.routine_name}
          </span>
          <span className="text-xs text-phosphor-dim shrink-0">
            {source.file_path}:{source.start_line}-{source.end_line}
          </span>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <span className="text-xs border border-terminal-border text-phosphor px-1 py-0 uppercase">
            {source.routine_type}
          </span>
          <span
            className={`text-xs px-1 py-0 font-mono ${
              score > 0.8
                ? "text-phosphor crt-glow"
                : score > 0.6
                ? "text-amber crt-glow-amber"
                : "text-phosphor-dim"
            }`}
          >
            [{(score * 100).toFixed(1)}%]
          </span>
          <span className="text-xs text-phosphor">
            {isExpanded ? "[-]" : "[+]"}
          </span>
        </div>
      </div>
      {isExpanded && snippet && (
        <div className="border-t border-terminal-border">
          <SyntaxHighlighter
            language="fortran"
            style={terminalTheme}
            customStyle={{
              margin: 0,
              padding: "0.5rem 0.75rem",
              fontSize: "0.8rem",
              background: "#000000",
              maxHeight: "400px",
              overflow: "auto",
            }}
            showLineNumbers
            startingLineNumber={source.start_line}
          >
            {snippet}
          </SyntaxHighlighter>
        </div>
      )}
    </div>
  );
}
