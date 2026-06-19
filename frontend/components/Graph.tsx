"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { getGraph } from "@/lib/api";
import type { GraphData, Paper } from "@/types";

export interface GraphProps {
  onNodeSelect: (paper: Paper | null) => void;
  highlightIds?: number[];
}

interface SimNode extends d3.SimulationNodeDatum {
  id: number;
  paper: Paper;
  fx?: number | null;
  fy?: number | null;
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  source: SimNode | number;
  target: SimNode | number;
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}…`;
}

function getNodeVisual(paper: Paper, isHighlighted: boolean) {
  let radius = 8;
  let fill = "#374151";

  if (paper.gap_score != null && paper.gap_score > 0.5) {
    fill = "#FCD34D";
    radius = 11;
  }
  if (paper.is_frontier) {
    fill = "#818CF8";
  }
  if (paper.read) {
    fill = "#6EE7B7";
  }

  let stroke = "transparent";
  let strokeWidth = 0;

  if (paper.seed) {
    radius = 14;
    stroke = "white";
    strokeWidth = 3;
  }

  if (isHighlighted) {
    stroke = "white";
    strokeWidth = 3;
  }

  return { radius, fill, stroke, strokeWidth, pulse: paper.is_frontier };
}

export default function Graph({
  onNodeSelect,
  highlightIds = [],
}: GraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  const onNodeSelectRef = useRef(onNodeSelect);
  const highlightIdsRef = useRef(highlightIds);
  const simulationRef = useRef<d3.Simulation<SimNode, SimLink> | null>(null);
  const nodesRef = useRef<SimNode[]>([]);
  const nodeSelectionRef = useRef<d3.Selection<SVGGElement, SimNode, d3.BaseType, unknown> | null>(null);
  const edgeSelectionRef = useRef<d3.Selection<SVGLineElement, SimLink, d3.BaseType, unknown> | null>(null);
  const edgeLabelRef = useRef<d3.Selection<SVGGElement, unknown, d3.BaseType, unknown> | null>(null);
  const initializedRef = useRef(false);

  useEffect(() => {
    onNodeSelectRef.current = onNodeSelect;
  }, [onNodeSelect]);

  useEffect(() => {
    highlightIdsRef.current = highlightIds;
    const highlightSet = new Set(highlightIds);
    nodeSelectionRef.current?.each(function (d) {
      const group = d3.select(this);
      const visual = getNodeVisual(d.paper, highlightSet.has(d.id));
      group
        .select<SVGCircleElement>("circle.node-circle")
        .attr("r", visual.radius)
        .attr("fill", visual.fill)
        .attr("stroke", visual.stroke)
        .attr("stroke-width", visual.strokeWidth);
      group
        .select<SVGCircleElement>("circle.node-pulse")
        .attr("r", visual.radius)
        .style("display", visual.pulse ? "block" : "none");
    });
  }, [highlightIds]);

  useEffect(() => {
    let cancelled = false;

    const fetchGraph = async () => {
      try {
        const data = await getGraph();
        if (!cancelled) {
          setGraphData(data);
        }
      } catch (error) {
        console.error("Failed to fetch graph:", error);
      }
    };

    fetchGraph();
    const interval = setInterval(fetchGraph, 4000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      setDimensions({ width, height });
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const { width, height } = dimensions;
    if (width === 0 || height === 0) return;

    const container = containerRef.current;
    if (!container) return;

    if (!initializedRef.current) {
      const svg = d3
        .select(container)
        .append("svg")
        .attr("width", "100%")
        .attr("height", "100%")
        .attr("viewBox", `0 0 ${width} ${height}`)
        .style("cursor", "grab");

      const zoomLayer = svg.append("g").attr("class", "zoom-layer");

      zoomLayer
        .append("rect")
        .attr("class", "graph-background")
        .attr("width", width)
        .attr("height", height)
        .attr("fill", "transparent")
        .on("click", () => onNodeSelectRef.current(null));

      const edgeGroup = zoomLayer.append("g").attr("class", "edges");
      const edgeLabelGroup = zoomLayer
        .append("g")
        .attr("class", "edge-label")
        .style("display", "none")
        .style("pointer-events", "none");

      edgeLabelGroup
        .append("rect")
        .attr("class", "edge-label-bg")
        .attr("rx", 3)
        .attr("ry", 3)
        .attr("fill", "#1F2937")
        .attr("fill-opacity", 0.9);

      edgeLabelGroup
        .append("text")
        .attr("class", "edge-label-text")
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "middle")
        .attr("fill", "#F9FAFB")
        .attr("font-size", 11)
        .attr("font-family", "system-ui, sans-serif");

      edgeLabelRef.current = edgeLabelGroup;

      const nodeGroup = zoomLayer.append("g").attr("class", "nodes");
      nodeSelectionRef.current = nodeGroup.selectAll<SVGGElement, SimNode>("g.node");
      edgeSelectionRef.current = edgeGroup.selectAll<SVGLineElement, SimLink>("line");

      const simulation = d3
        .forceSimulation<SimNode, SimLink>([])
        .force(
          "link",
          d3
            .forceLink<SimNode, SimLink>()
            .id((d) => d.id)
            .distance(80)
            .strength(0.5),
        )
        .force("charge", d3.forceManyBody().strength(-200))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collide", d3.forceCollide<SimNode>().radius(20));

      simulation.on("tick", () => {
        edgeSelectionRef.current
          ?.attr("x1", (d) => (d.source as SimNode).x ?? 0)
          .attr("y1", (d) => (d.source as SimNode).y ?? 0)
          .attr("x2", (d) => (d.target as SimNode).x ?? 0)
          .attr("y2", (d) => (d.target as SimNode).y ?? 0);

        nodeSelectionRef.current?.attr(
          "transform",
          (d) => `translate(${d.x ?? 0},${d.y ?? 0})`,
        );
      });

      const zoomBehavior = d3
        .zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
          zoomLayer.attr("transform", event.transform);
        });

      svg.call(zoomBehavior).on("dblclick.zoom", null);

      simulationRef.current = simulation;
      edgeSelectionRef.current = edgeGroup.selectAll<SVGLineElement, SimLink>("line");
      nodeSelectionRef.current = nodeGroup.selectAll<SVGGElement, SimNode>("g.node");

      initializedRef.current = true;
    }

    const svg = d3.select(container).select<SVGSVGElement>("svg");
    svg.attr("viewBox", `0 0 ${width} ${height}`);
    svg.select("rect.graph-background").attr("width", width).attr("height", height);

    simulationRef.current
      ?.force("center", d3.forceCenter(width / 2, height / 2))
      .force("x", null)
      .force("y", null);

    if (graphData) {
      const oldNodeMap = new Map(nodesRef.current.map((node) => [node.id, node]));
      const highlightSet = new Set(highlightIdsRef.current);

      nodesRef.current = graphData.nodes.map((paper) => {
        const existing = oldNodeMap.get(paper.id);
        if (existing) {
          existing.paper = paper;
          return existing;
        }
        return { id: paper.id, paper };
      });

      const nodeIds = new Set(nodesRef.current.map((node) => node.id));
      nodesRef.current = nodesRef.current.filter((node) => nodeIds.has(node.id));

      const links: SimLink[] = graphData.edges
        .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
        .map((edge) => ({ source: edge.source, target: edge.target }));

      const simulation = simulationRef.current;
      if (!simulation) return;

      simulation.nodes(nodesRef.current);
      const linkForce = simulation.force("link") as d3.ForceLink<SimNode, SimLink>;
      linkForce.links(links);

      const containerNode = d3.select(container);
      const nodeGroup = containerNode.select<SVGGElement>("g.nodes");
      const edgeGroup = containerNode.select<SVGGElement>("g.edges");

      const dragBehavior = d3
        .drag<SVGGElement, SimNode>()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
          svg.style("cursor", "grabbing");
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = event.x;
          d.fy = event.y;
          svg.style("cursor", "grab");
        });

      nodeSelectionRef.current = nodeGroup
        .selectAll<SVGGElement, SimNode>("g.node")
        .data(nodesRef.current, (d) => d.id)
        .join(
          (enter) => {
            const group = enter
              .append("g")
              .attr("class", "node")
              .style("cursor", "pointer")
              .call(dragBehavior);

            group
              .append("circle")
              .attr("class", "node-pulse graph-frontier-pulse")
              .attr("fill", "none")
              .attr("stroke", "#818CF8")
              .attr("stroke-width", 2)
              .style("display", "none");

            group.append("circle").attr("class", "node-circle");

            group
              .on("click", (event, d) => {
                event.stopPropagation();
                onNodeSelectRef.current(d.paper);
              })
              .on("dblclick", (event, d) => {
                event.stopPropagation();
                console.log(`crawl deeper: ${d.paper.arxiv_id}`);
              });

            return group;
          },
          (update) => update.call(dragBehavior),
          (exit) => exit.remove(),
        );

      nodeSelectionRef.current.each(function (d) {
        const group = d3.select(this);
        const visual = getNodeVisual(d.paper, highlightSet.has(d.id));
        group
          .select<SVGCircleElement>("circle.node-circle")
          .attr("r", visual.radius)
          .attr("fill", visual.fill)
          .attr("stroke", visual.stroke)
          .attr("stroke-width", visual.strokeWidth);
        group
          .select<SVGCircleElement>("circle.node-pulse")
          .attr("r", visual.radius)
          .style("display", visual.pulse ? "block" : "none");
      });

      edgeSelectionRef.current = edgeGroup
        .selectAll<SVGLineElement, SimLink>("line")
        .data(links, (d) => {
          const source = d.source as SimNode;
          const target = d.target as SimNode;
          const sourceId = typeof source === "object" ? source.id : source;
          const targetId = typeof target === "object" ? target.id : target;
          return `${sourceId}-${targetId}`;
        })
        .join(
          (enter) =>
            enter
              .append("line")
              .attr("stroke", "#4B5563")
              .attr("stroke-opacity", 0.4)
              .attr("stroke-width", 1),
          (update) => update,
          (exit) => exit.remove(),
        );

      edgeSelectionRef.current
        .on("mouseenter", function (_event, d) {
          const source = d.source as SimNode;
          const target = d.target as SimNode;
          const x = ((source.x ?? 0) + (target.x ?? 0)) / 2;
          const y = ((source.y ?? 0) + (target.y ?? 0)) / 2;
          const title = truncate(target.paper.title ?? "Untitled", 40);
          const label = edgeLabelRef.current;
          if (!label) return;

          const text = label.select("text").text(title);
          const bbox = (text.node() as SVGTextElement).getBBox();

          label
            .select("rect")
            .attr("x", bbox.x - 6)
            .attr("y", bbox.y - 4)
            .attr("width", bbox.width + 12)
            .attr("height", bbox.height + 8);

          label.attr("transform", `translate(${x},${y})`).style("display", "block");
        })
        .on("mouseleave", () => {
          edgeLabelRef.current?.style("display", "none");
        });

      simulation.alpha(0.3).restart();
    }
  }, [graphData, dimensions]);

  useEffect(() => {
    return () => {
      simulationRef.current?.stop();
      if (containerRef.current) {
        d3.select(containerRef.current).selectAll("*").remove();
      }
      initializedRef.current = false;
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="relative h-full w-full overflow-hidden bg-gray-950"
    />
  );
}
