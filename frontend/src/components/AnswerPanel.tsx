import ReactMarkdown from "react-markdown";
import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import fortran from "react-syntax-highlighter/dist/esm/languages/hljs/fortran";
import { atomOneDark } from "react-syntax-highlighter/dist/esm/styles/hljs";

SyntaxHighlighter.registerLanguage("fortran", fortran);

interface Props {
  answer: string;
  isStreaming: boolean;
}

export default function AnswerPanel({ answer, isStreaming }: Props) {
  if (!answer) return null;

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
      <div className="flex items-center gap-2 mb-4">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
          Answer
        </h3>
        {isStreaming && (
          <span className="flex items-center gap-1 text-xs text-indigo-400">
            <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse" />
            Generating...
          </span>
        )}
      </div>
      <div className="prose prose-invert prose-sm max-w-none">
        <ReactMarkdown
          components={{
            code({ className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || "");
              const inline = !match;
              return inline ? (
                <code className="bg-gray-700 px-1.5 py-0.5 rounded text-sm" {...props}>
                  {children}
                </code>
              ) : (
                <SyntaxHighlighter
                  style={atomOneDark}
                  language={match[1]}
                  customStyle={{
                    borderRadius: "0.5rem",
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
