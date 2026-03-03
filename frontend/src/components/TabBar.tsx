interface Tab {
  id: string;
  label: string;
  icon: string;
}

const TABS: Tab[] = [
  { id: "query", label: "Ask", icon: "?" },
  { id: "search", label: "Search", icon: "S" },
  { id: "explain", label: "Explain", icon: "E" },
  { id: "docgen", label: "Docs", icon: "D" },
  { id: "dependencies", label: "Deps", icon: "G" },
  { id: "patterns", label: "Patterns", icon: "P" },
  { id: "business", label: "Logic", icon: "L" },
];

interface Props {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export default function TabBar({ activeTab, onTabChange }: Props) {
  return (
    <div className="flex flex-wrap gap-0 border border-terminal-border font-mono">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`border-r border-terminal-border last:border-r-0 px-3 py-2 text-sm uppercase font-mono transition-colors ${
            activeTab === tab.id
              ? "bg-phosphor text-terminal-black"
              : "text-phosphor bg-transparent hover:bg-phosphor hover:text-terminal-black"
          }`}
        >
          {activeTab === tab.id ? `[ ${tab.label.toUpperCase()} ]` : `+ ${tab.label.toUpperCase()} +`}
        </button>
      ))}
    </div>
  );
}
