"use client";

import { useState } from "react";
import Graph from "@/components/Graph";
import type { Paper } from "@/types";

export default function Home() {
  const [selected, setSelected] = useState<Paper | null>(null);

  return (
    <main className="flex h-screen flex-col bg-gray-950">
      <header className="border-b border-gray-800 px-4 py-2 text-sm text-gray-300">
        {selected?.title ?? "Click a node to select"}
      </header>
      <div className="min-h-0 flex-1">
        <Graph
          onNodeSelect={setSelected}
          highlightIds={selected ? [selected.id] : []}
        />
      </div>
    </main>
  );
}
