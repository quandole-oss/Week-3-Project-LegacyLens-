import ReactMarkdown from "react-markdown";
import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import fortran from "react-syntax-highlighter/dist/esm/languages/hljs/fortran";
import terminalTheme from "../terminalTheme";

SyntaxHighlighter.registerLanguage("fortran", fortran);

interface Props {
  answer: string;
  isStreaming: boolean;
}

export default function AnswerPanel({ answer, isStreaming }: Props) {
  if (!answer) return null;

  return (
    <div className="bg-terminal-black border border-terminal-border p-3 font-mono">
      <div className="tui-row flex items-center gap-2 mb-2 border-b border-terminal-border">
        <h3 className="text-sm text-amber uppercase tracking-wide crt-glow-amber">
          === OUTPUT ===
        </h3>
        {isStreaming && (
          <span className="flex items-center gap-1 text-xs text-phosphor">
            <span className="blink-cursor inline-block w-2 h-4 bg-phosphor" />
            GENERATING...
          </span>
        )}
      </div>
      <div className="terminal-prose max-w-none pt-2">
        <ReactMarkdown
          components={{
            code({ className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || "");
              const inline = !match;
              return inline ? (
                <code className="bg-terminal-green-muted text-amber px-1.5 py-0.5 text-sm" {...props}>
                  {children}
                </code>
              ) : (
                <SyntaxHighlighter
                  style={terminalTheme}
                  language={match[1]}
                  customStyle={{
                    background: "#000000",
                    borderRadius: "0",
                    fontSize: "0.8rem",
                  }}
                >
                  {String(children).replace(/\n$/, "")}
                </SyntaxHighlighter>
              );
            },
          }}
        >
          {answer}
        </ReactMarkdown>
      </div>
    </div>
  );
}
