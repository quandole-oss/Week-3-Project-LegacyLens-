export type Verbosity = "succinct" | "concise" | "regular" | "detailed";

const LEVELS: { id: Verbosity; label: string }[] = [
  { id: "succinct", label: "Succinct" },
  { id: "concise", label: "Concise" },
  { id: "regular", label: "Regular" },
  { id: "detailed", label: "Detailed" },
];

interface Props {
  value: Verbosity;
  onChange: (v: Verbosity) => void;
}

export default function VerbositySelector({ value, onChange }: Props) {
  return (
    <div className="flex items-center gap-0 font-mono">
      <span className="text-xs text-amber uppercase tracking-wide mr-2 crt-glow-amber">
        VERBOSITY:
      </span>
      <div className="flex gap-0 border border-terminal-border">
        {LEVELS.map((level) => (
          <button
            key={level.id}
            onClick={() => onChange(level.id)}
            className={`border-r border-terminal-border last:border-r-0 px-2 py-1 text-xs uppercase font-mono transition-colors ${
              value === level.id
                ? "bg-amber text-terminal-black"
                : "text-phosphor-dim bg-transparent hover:bg-phosphor hover:text-terminal-black"
            }`}
          >
            {value === level.id ? `[ ${level.label} ]` : level.label}
          </button>
        ))}
      </div>
    </div>
  );
}
