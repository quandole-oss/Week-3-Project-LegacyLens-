import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import fortran from "react-syntax-highlighter/dist/esm/languages/hljs/fortran";
import { atomOneDark } from "react-syntax-highlighter/dist/esm/styles/hljs";
import type { Source, SearchResult } from "../api";
import { getFileContext } from "../api";
import { useState } from "react";

SyntaxHighlighter.registerLanguage("fortran", fortran);

interface Props {
  source: Source | SearchResult;
  index: number;
  expanded?: boolean;
}

export default function SourceCard({ source, index, expanded = false }: Props) {
  const [isExpanded, setIsExpanded] = useState(expanded);
  const [fullContext, setFullContext] = useState<string | null>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [contextStartLine, setContextStartLine] = useState(source.start_line);
  const snippet = "snippet" in source ? source.snippet : ("text" in source ? source.text : "");
  const score = source.score;

  const handleLoadContext = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (fullContext) {
      setFullContext(null);
      return;
    }
    setContextLoading(true);
    try {
      const ctx = await getFileContext(
        source.file_path,
        source.start_line,
        source.end_line,
        50,
      );
      setFullContext(ctx.content);
      setContextStartLine(ctx.start_line);
    } catch {
      setFullContext("// Failed to load file context");
      setContextStartLine(1);
    } finally {
      setContextLoading(false);
    }
  };

  const displayCode = fullContext ?? snippet;
  const displayStartLine = fullContext ? contextStartLine : source.start_line;

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-750"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono bg-gray-700 text-gray-300 px-2 py-0.5 rounded">
            #{index + 1}
          </span>
          <div>
            <span className="text-sm font-medium text-indigo-400">
              {source.routine_name}
            </span>
            <span className="text-xs text-gray-500 ml-2">
              {source.file_path}:{source.start_line}-{source.end_line}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs bg-gray-700 text-gray-400 px-2 py-0.5 rounded">
            {source.routine_type}
          </span>
          <span
            className={`text-xs px-2 py-0.5 rounded font-mono ${
              score > 0.8
                ? "bg-green-900 text-green-300"
                : score > 0.6
                ? "bg-yellow-900 text-yellow-300"
                : "bg-gray-700 text-gray-400"
            }`}
          >
            {(score * 100).toFixed(1)}%
          </span>
          <svg
            className={`w-4 h-4 text-gray-500 transition-transform ${isExpanded ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>
      {isExpanded && displayCode && (
        <div className="border-t border-gray-700">
          <div className="flex items-center justify-between px-4 py-1.5 bg-gray-900/50">
            <span className="text-xs text-gray-500">
              {fullContext ? "Full context" : "Matched snippet"}
            </span>
            <button
              onClick={handleLoadContext}
              disabled={contextLoading}
              className="text-xs text-indigo-400 hover:text-indigo-300 disabled:text-gray-600 transition-colors"
            >
              {contextLoading
                ? "Loading..."
                : fullContext
                ? "Show snippet"
                : "View full context"}
            </button>
          </div>
          <SyntaxHighlighter
            language="fortran"
            style={atomOneDark}
            customStyle={{
              margin: 0,
              padding: "1rem",
              fontSize: "0.8rem",
              background: "#1a1b26",
              maxHeight: "400px",
              overflow: "auto",
            }}
            showLineNumbers
            startingLineNumber={displayStartLine}
          >
            {displayCode}
          </SyntaxHighlighter>
        </div>
      )}
    </div>
  );
}
