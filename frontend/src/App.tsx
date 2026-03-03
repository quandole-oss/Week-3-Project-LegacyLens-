import { useState, useCallback } from "react";
import Header from "./components/Header";
import TabBar from "./components/TabBar";
import QueryInput from "./components/QueryInput";
import AnswerPanel from "./components/AnswerPanel";
import SourceCard from "./components/SourceCard";
import { AnswerSkeleton, SourceSkeleton } from "./components/Skeleton";
import { streamQuery, searchCode } from "./api";
import type { Source, SearchResult } from "./api";
import "./index.css";

type TabId = "query" | "search" | "explain" | "docgen" | "dependencies" | "patterns" | "business";

const TAB_ENDPOINTS: Record<TabId, string> = {
  query: "/api/query",
  search: "/api/search",
  explain: "/api/explain",
  docgen: "/api/docgen",
  dependencies: "/api/dependencies",
  patterns: "/api/patterns",
  business: "/api/business-logic",
};

const TAB_PLACEHOLDERS: Record<TabId, string> = {
  query: "Ask a question about LAPACK code...",
  search: "Search for code (e.g., 'LU decomposition')...",
  explain: "Enter a routine name to explain (e.g., 'DGESV')...",
  docgen: "Enter a routine name to generate docs for...",
  dependencies: "Enter a routine name to map dependencies...",
  patterns: "Describe a code pattern to find...",
  business: "Enter a routine to extract business logic from...",
};

function App() {
  const [activeTab, setActiveTab] = useState<TabId>("query");
  const [isLoading, setIsLoading] = useState(false);
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleQuery = useCallback(
    async (query: string) => {
      setIsLoading(true);
      setAnswer("");
      setSources([]);
      setSearchResults([]);
      setError(null);

      try {
        if (activeTab === "search") {
          const result = await searchCode(query);
          setSearchResults(result.results);
          setIsLoading(false);
          return;
        }

        const endpoint = TAB_ENDPOINTS[activeTab];
        let fullAnswer = "";

        for await (const event of streamQuery(endpoint, query)) {
          switch (event.type) {
            case "sources":
              setSources(event.data as Source[]);
              break;
            case "token":
              fullAnswer += event.data as string;
              setAnswer(fullAnswer);
              break;
            case "patterns":
            case "dependencies":
            case "graph":
              // For structured data, display as formatted JSON
              fullAnswer += "```json\n" + JSON.stringify(event.data, null, 2) + "\n```\n\n";
              setAnswer(fullAnswer);
              break;
            case "result":
              // Pattern search individual results
              const r = event.data as SearchResult;
              setSearchResults((prev) => [...prev, r]);
              break;
            case "error":
              setError(event.data as string);
              break;
            case "done":
              break;
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setIsLoading(false);
      }
    },
    [activeTab]
  );

  return (
    <div className="min-h-screen bg-terminal-black text-phosphor font-mono">
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-4 sm:py-8">
        <div className="space-y-6">
          <TabBar activeTab={activeTab} onTabChange={(tab) => setActiveTab(tab as TabId)} />
          <QueryInput
            onSubmit={handleQuery}
            isLoading={isLoading}
            placeholder={TAB_PLACEHOLDERS[activeTab]}
          />

          {error && (
            <div className="border border-amber text-amber px-3 py-2 font-mono uppercase crt-glow-amber">
              *** ERROR *** {error}
            </div>
          )}

          {isLoading && !answer && activeTab !== "search" && (
            <AnswerSkeleton />
          )}

          {answer && activeTab !== "search" && (
            <AnswerPanel answer={answer} isStreaming={isLoading} />
          )}

          {isLoading && sources.length === 0 && activeTab !== "search" && (
            <SourceSkeleton />
          )}

          {sources.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm text-amber uppercase tracking-wide crt-glow-amber">
                === SOURCES ({sources.length}) ===
              </h3>
              {sources.map((source, i) => (
                <SourceCard key={`${source.file_path}-${source.routine_name}`} source={source} index={i} />
              ))}
            </div>
          )}

          {searchResults.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm text-amber uppercase tracking-wide crt-glow-amber">
                === RESULTS ({searchResults.length}) ===
              </h3>
              {searchResults.map((result, i) => (
                <SourceCard key={`${result.file_path}-${result.routine_name}-${i}`} source={result} index={i} expanded />
              ))}
            </div>
          )}

          {!isLoading && !answer && !error && sources.length === 0 && searchResults.length === 0 && (
            <div className="text-center py-16 font-mono">
              <pre className="text-phosphor crt-glow text-xs sm:text-sm mb-4 inline-block text-left">
{` _                                _
| |    ___  __ _  __ _  ___ _   _| |    ___ _ __  ___
| |   / _ \\/ _\` |/ _\` |/ __| | | | |   / _ \\ '_ \\/ __|
| |__|  __/ (_| | (_| | (__| |_| | |__|  __/ | | \\__ \\
|_____\\___|\\__, |\\__,_|\\___|\\__, |_____\\___|_| |_|___/
           |___/            |___/`}
              </pre>
              <h2 className="text-lg text-amber crt-glow-amber mb-2 uppercase">
                [ EXPLORE LAPACK LEGACY CODE ]
              </h2>
              <p className="text-phosphor-dim max-w-lg mx-auto uppercase text-sm">
                Ask questions about LAPACK routines, search for code patterns, generate documentation,
                or explore dependencies. Try one of the example queries above to get started.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
