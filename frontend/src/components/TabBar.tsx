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
    <div className="flex flex-wrap gap-1 bg-gray-800 p-1 rounded-lg border border-gray-700">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === tab.id
              ? "bg-indigo-600 text-white"
              : "text-gray-400 hover:text-gray-200 hover:bg-gray-700"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
