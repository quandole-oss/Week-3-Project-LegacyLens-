const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface Source {
  file_path: string;
  routine_name: string;
  routine_type: string;
  start_line: number;
  end_line: number;
  score: number;
  snippet?: string;
}

export interface SearchResult {
  text: string;
  file_path: string;
  routine_name: string;
  routine_type: string;
  start_line: number;
  end_line: number;
  language: string;
  score: number;
}

export interface StreamEvent {
  type: "sources" | "token" | "done" | "patterns" | "dependencies" | "graph" | "result" | "error";
  data: unknown;
}

export interface IndexStats {
  index_name: string;
  total_vectors: number;
  dimensions: number;
}

export async function searchCode(query: string, topK: number = 10): Promise<{ query: string; results: SearchResult[]; count: number }> {
  const res = await fetch(`${API_URL}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK }),
  });
  if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
  return res.json();
}

export async function getStats(): Promise<IndexStats> {
  const res = await fetch(`${API_URL}/api/stats`);
  if (!res.ok) throw new Error(`Stats failed: ${res.statusText}`);
  return res.json();
}

export interface FileContext {
  file_path: string;
  start_line: number;
  end_line: number;
  total_lines: number;
  content: string;
}

export async function getFileContext(
  filePath: string,
  startLine: number,
  endLine: number,
  contextLines: number = 50,
): Promise<FileContext> {
  const res = await fetch(`${API_URL}/api/file-context`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      file_path: filePath,
      start_line: startLine,
      end_line: endLine,
      context_lines: contextLines,
    }),
  });
  if (!res.ok) throw new Error(`File context failed: ${res.statusText}`);
  return res.json();
}

export async function* streamQuery(
  endpoint: string,
  query: string,
  topK: number = 10,
  verbosity: string = "regular",
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${API_URL}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: query, query, top_k: topK, stream: true, verbosity }),
  });

  if (!res.ok) throw new Error(`Request failed: ${res.statusText}`);
  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith("data: ")) {
        try {
          const event: StreamEvent = JSON.parse(trimmed.slice(6));
          yield event;
        } catch {
          // Skip malformed events
        }
      }
    }
  }

  // Process any remaining data left in the buffer after stream ends
  const remaining = buffer.trim();
  if (remaining.startsWith("data: ")) {
    try {
      const event: StreamEvent = JSON.parse(remaining.slice(6));
      yield event;
    } catch {
      // Skip malformed events
    }
  }
}
