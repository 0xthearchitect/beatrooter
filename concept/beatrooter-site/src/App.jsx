import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, GitFork, SunMedium } from "lucide-react";
import beetrootLogo from "./assets/beatroot_logo.svg";
import nodeDoc from "./assets/Notes.svg";
import nodeOutput from "./assets/node-output.svg";
import nodeTeam from "./assets/User.svg";
import theArchitectImage from "./assets/thearchitect.png";
import devilBoyImage from "./assets/DevilBoy.jpg";
import adamastorImage from "./assets/0xAdamastor.png";
import zerodotoneImage from "./assets/ManWithThatHat.png";

const DEFAULT_STAGE_WIDTH = 1280;
const DOUBLE_CLICK_MS = 280;
const DRAG_THRESHOLD_PX = 6;
const EDGE_STAGE_PADDING = 28;

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function getCurrentPageFromHash() {
  return window.location.hash === "#team" ? "team" : "home";
}

function GitHubIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className="h-4.5 w-4.5">
      <path d="M12 .5a12 12 0 0 0-3.79 23.39c.6.11.82-.26.82-.58v-2.03c-3.34.73-4.04-1.41-4.04-1.41-.55-1.38-1.33-1.75-1.33-1.75-1.09-.75.08-.73.08-.73 1.2.09 1.84 1.22 1.84 1.22 1.08 1.82 2.82 1.29 3.5.99.11-.77.42-1.29.76-1.58-2.66-.3-5.47-1.31-5.47-5.86 0-1.3.47-2.35 1.23-3.18-.12-.3-.53-1.51.12-3.15 0 0 1.01-.32 3.3 1.21a11.6 11.6 0 0 1 6 0c2.29-1.53 3.3-1.2 3.3-1.2.65 1.63.24 2.84.12 3.14.77.83 1.23 1.89 1.23 3.18 0 4.56-2.81 5.56-5.49 5.85.43.37.82 1.1.82 2.22v3.29c0 .32.21.7.83.58A12 12 0 0 0 12 .5Z" />
    </svg>
  );
}

function CommandGlyph({ compact = false }) {
  return (
    <span
      className={`${compact ? "text-[84px]" : "text-[84px]"} font-semibold leading-none text-[#ff94c4]`}
    >
      &gt;_
    </span>
  );
}

function MemberGlyph() {
  return (
    <svg viewBox="0 0 48 48" className="h-8 w-8" fill="none" aria-hidden="true">
      <path d="M23.8 9.4c0-2.8 2.27-5.1 5.08-5.1h.6v.76c0 2.82-2.28 5.1-5.08 5.1h-.6V9.4Z" fill="#79da63" />
      <path d="M20.94 10.36c-1.98-1.99-1.98-5.2.01-7.18l.42-.42.51.52c1.99 1.98 1.99 5.2 0 7.18l-.42.43-.52-.53Z" fill="#79da63" />
      <path d="M27.3 10.87c-1.98-1.98-1.98-5.2 0-7.18l.42-.42.52.51c1.99 1.99 1.99 5.2 0 7.2l-.43.42-.5-.53Z" fill="#79da63" />
      <circle cx="24" cy="18.5" r="8" fill="#b24677" />
      <path d="M12.2 41c.54-7.4 4.96-12.14 11.8-12.14 6.83 0 11.25 4.73 11.8 12.14H12.2Z" fill="#b24677" />
    </svg>
  );
}

function renderNodeIcon(meta, compact) {
  const iconSize = compact
    ? meta.compactIconSize ?? 80
    : meta.expandedIconSize ?? 54;

  if (meta.iconAsset) {
    return (
      <img
        src={meta.iconAsset}
        alt=""
        className="rounded-[12px] object-cover"
        style={{ width: iconSize, height: iconSize }}
        draggable="false"
      />
    );
  }

  const { iconType } = meta;

  switch (iconType) {
    case "command":
      return <img src={nodeTeam} alt="" draggable="false" style={{ width: iconSize, height: iconSize }} />;
    case "member":
      return <img src={nodeTeam} alt="" draggable="false" style={{ width: iconSize, height: iconSize }} />;
    case "about":
      return <img src={nodeDoc} alt="" draggable="false" style={{ width: iconSize, height: iconSize }} />;
    case "product":
      return <img src={nodeOutput} alt="" draggable="false" style={{ width: iconSize, height: iconSize }} />;
    default:
      return <img src={beetrootLogo} alt="" draggable="false" style={{ width: iconSize, height: iconSize }} />;
  }
}

const HOME_CONFIG = {
  stageHeight: 620,
  maxWidth: 1280,
  getInitialNodes(stageWidth) {
    const sideOffset = clamp(stageWidth * 0.12, 116, 170);
    const compactSize = 126;
    const minYPosition = 200; // More breathing room from header border
    
    // Generate random Y offsets for organic positioning
    // Side nodes (left & right) move freely up or down
    // Center node stays almost fixed for visual anchor
    const leftYOffset = (Math.random() - 0.5) * 120 - 20;   // -80 to +40px (more range, can go both ways)
    const centerYOffset = (Math.random() - 0.5) * 12;       // -6 to +6px (barely moves)
    const rightYOffset = (Math.random() - 0.5) * 120 + 20;  // -40 to +80px (more range, can go both ways)
    
    return {
      about: { x: sideOffset, y: clamp(250 + leftYOffset, minYPosition, 620), expanded: false },
      team: { x: Math.round((stageWidth - compactSize) / 2), y: clamp(250 + centerYOffset, minYPosition, 620), expanded: false },
      beatrooter: { x: stageWidth - sideOffset - compactSize, y: clamp(244 + rightYOffset, minYPosition, 620), expanded: false },
    };
  },
  edges: [
    { from: "about", to: "team", fromPort: "right", toPort: "left" },
    { from: "team", to: "beatrooter", fromPort: "right", toPort: "left" },
  ],
  nodes: {
    about: {
      collapsed: { width: 126, height: 126 },
      expanded: { width: 292, height: 186 },
      expandedPortY: 38,
      compactFrameSize: 92,
      compactIconSize: 70,
      expandedFrameSize: 60,
      expandedIconSize: 42,
      title: "ABOUT",
      accent: "#ff6d96",
      headerBackground: "linear-gradient(180deg, rgba(126,34,63,0.96) 0%, rgba(88,25,48,0.92) 100%)",
      iconType: "about",
      details: [
        ["Focus", "Node-based music workflows"],
        ["Vision", "Automation for beat builders"],
        ["Story", "Built for modern creative teams"],
      ],
    },
    team: {
      collapsed: { width: 126, height: 126 },
      expanded: { width: 392, height: 188 },
      expandedPortY: 38,
      compactFrameSize: 92,
      compactIconSize: 68,
      expandedFrameSize: 60,
      expandedIconSize: 42,
      title: "TEAM",
      accent: "#7a74ff",
      headerBackground: "linear-gradient(180deg, rgba(66,62,142,0.98) 0%, rgba(56,52,122,0.95) 100%)",
      iconType: "member",
      linkToPage: "team",
      details: [
        ["Crew", "Designers, devs and producers"],
        ["Culture", "Fast iteration, strong taste"],
        ["Mode", "Shipping tools that feel alive"],
      ],
    },
    beatrooter: {
      collapsed: { width: 126, height: 126 },
      expanded: { width: 304, height: 184 },
      expandedPortY: 38,
      compactFrameSize: 94,
      compactIconSize: 74,
      expandedFrameSize: 66,
      expandedIconSize: 50,
      title: "BEATROOTER",
      accent: "#ee7bb0",
      headerBackground: "linear-gradient(180deg, rgba(92,36,59,0.96) 0%, rgba(63,26,42,0.92) 100%)",
      iconType: "product",
      iconAsset: beetrootLogo,
      details: [
        ["Product", "Visual audio operations"],
        ["Platform", "Docs, flows and examples"],
        ["Status", "Growing with every release"],
      ],
    },
  },
};

const TEAM_CONFIG = {
  stageHeight: 620,
  maxWidth: 1360,
  getInitialNodes(stageWidth) {
    return {
      memberA: { x: 92, y: 54, expanded: false },
      memberB: { x: 86, y: 430, expanded: false },
      product: { x: Math.round((stageWidth - 136) / 2), y: 236, expanded: false },
      memberC: { x: stageWidth - 190, y: 48, expanded: false },
      memberD: { x: stageWidth - 182, y: 420, expanded: false },
    };
  },
  edges: [
    { from: "memberA", to: "product", fromPort: "right", toPort: "left" },
    { from: "memberB", to: "product", fromPort: "right", toPort: "left" },
    { from: "memberC", to: "product", fromPort: "left", toPort: "right" },
    { from: "memberD", to: "product", fromPort: "left", toPort: "right" },
  ],
  nodes: {
    memberA: {
      collapsed: { width: 132, height: 132 },
      expanded: { width: 332, height: 208 },
      expandedPortY: 42,
      compactFrameSize: 112,
      compactIconSize: 104,
      expandedFrameSize: 72,
      expandedIconSize: 54,
      title: "0XTHEARCHITECT",
      accent: "#ee7bb0",
      headerBackground: "linear-gradient(180deg, rgba(92,36,59,0.96) 0%, rgba(63,26,42,0.92) 100%)",
      iconType: "member",
      iconAsset: theArchitectImage,
      details: [
        ["Role", "ARCHITECT / CORE DEV"],
        ["Focus", "Architecture, technical direction, tool integration."],
        ["Strength", "Build the roots of BeatRooter."],
      ],
    },
    memberB: {
      collapsed: { width: 132, height: 132 },
      expanded: { width: 332, height: 208 },
      expandedPortY: 42,
      compactFrameSize: 112,
      compactIconSize: 104,
      expandedFrameSize: 72,
      expandedIconSize: 54,
      title: "DEVILBOY",
      accent: "#ee7bb0",
      headerBackground: "linear-gradient(180deg, rgba(92,36,59,0.96) 0%, rgba(63,26,42,0.92) 100%)",
      iconType: "member",
      iconAsset: devilBoyImage,
      details: [
        ["Role", "DEV / TEAM LEADER"],
        ["Focus", "Development, idealist, collaboration."],
        ["Strength", "Keeping the momentum alive."],
      ],
    },
    product: {
      collapsed: { width: 136, height: 136 },
      expanded: { width: 388, height: 220 },
      expandedPortY: 44,
      compactFrameSize: 112,
      compactIconSize: 82,
      expandedFrameSize: 78,
      expandedIconSize: 58,
      title: "BEATROOTER",
      accent: "#79da63",
      headerBackground: "linear-gradient(180deg, rgba(45,74,33,0.96) 0%, rgba(31,52,24,0.92) 100%)",
      iconType: "product",
      iconAsset: beetrootLogo,
      details: [
        ["Core", "Node-based cybersecurity automation tools"],
        ["Value", "Automation for beat builders"],
        ["Goal", "To be an icon in the world of cybersecurity as a tool for orchestrating attacks"],
      ],
    },
    memberC: {
      collapsed: { width: 132, height: 132 },
      expanded: { width: 332, height: 208 },
      expandedPortY: 42,
      compactFrameSize: 112,
      compactIconSize: 104,
      expandedFrameSize: 72,
      expandedIconSize: 54,
      title: "ZER0DOTONE",
      accent: "#ee7bb0",
      headerBackground: "linear-gradient(180deg, rgba(92,36,59,0.96) 0%, rgba(63,26,42,0.92) 100%)",
      iconType: "member",
      iconAsset: zerodotoneImage,
      details: [
        ["Role", "DEV / DESIGNER"],
        ["Focus", "Designer, Identity, Metal."],
        ["Strength", "Do you see our icons? Well... guess what!"],
      ],
    },
    memberD: {
      collapsed: { width: 132, height: 132 },
      expanded: { width: 332, height: 208 },
      expandedPortY: 42,
      compactFrameSize: 112,
      compactIconSize: 104,
      expandedFrameSize: 72,
      expandedIconSize: 54,
      title: "0XADAMASTOR",
      accent: "#ee7bb0",
      headerBackground: "linear-gradient(180deg, rgba(92,36,59,0.96) 0%, rgba(63,26,42,0.92) 100%)",
      iconType: "member",
      iconAsset: adamastorImage,
      details: [
        ["Core", "DEV / CIBERSECURITY SPECIALIST"],
        ["Value", "Systems, tooling, stability."],
        ["Strength", "Strengthening the underground network."],
      ],
    },
  },
};

const PAGE_CONFIGS = {
  home: HOME_CONFIG,
  team: TEAM_CONFIG,
};

function getNodeSize(config, nodeId, expanded) {
  const node = config.nodes[nodeId];
  return expanded ? node.expanded : node.collapsed;
}

function toggleNodeExpansion(config, currentNodes, nodeId, stageWidth) {
  const currentNode = currentNodes[nodeId];
  const currentSize = getNodeSize(config, nodeId, currentNode.expanded);
  const nextExpanded = !currentNode.expanded;
  const nextSize = getNodeSize(config, nodeId, nextExpanded);
  const centerX = currentNode.x + currentSize.width / 2;
  const centerY = currentNode.y + currentSize.height / 2;

  return {
    ...currentNodes,
    [nodeId]: {
      ...currentNode,
      expanded: nextExpanded,
      x: clamp(centerX - nextSize.width / 2, 0, Math.max(stageWidth - nextSize.width, 0)),
      y: clamp(centerY - nextSize.height / 2, 0, config.stageHeight - nextSize.height),
    },
  };
}

function getNodeRect(config, nodeId, nodeState) {
  const size = getNodeSize(config, nodeId, nodeState.expanded);
  return {
    x: nodeState.x,
    y: nodeState.y,
    width: size.width,
    height: size.height,
    right: nodeState.x + size.width,
    bottom: nodeState.y + size.height,
  };
}

function getPortPosition(config, nodeId, nodeState, portName, offsetY = 0) {
  const meta = config.nodes[nodeId];
  const size = getNodeSize(config, nodeId, nodeState.expanded);
  const portY = nodeState.expanded ? (meta.expandedPortY ?? 38) : size.height / 2;
  const isLeftPort = portName === "in" || portName === "left";

  return {
    x: nodeState.x + (isLeftPort ? 0 : size.width),
    y: nodeState.y + portY + offsetY,
    normalX: isLeftPort ? -1 : 1,
    normalY: 0,
  };
}

function buildRoundedPolylinePath(points, radius) {
  if (points.length < 2) {
    return "";
  }

  const path = [`M ${points[0].x} ${points[0].y}`];

  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1];
    const current = points[index];
    const next = points[index + 1];

    if (!next) {
      path.push(`L ${current.x} ${current.y}`);
      continue;
    }

    const inDx = current.x - previous.x;
    const inDy = current.y - previous.y;
    const outDx = next.x - current.x;
    const outDy = next.y - current.y;
    const inLength = Math.hypot(inDx, inDy);
    const outLength = Math.hypot(outDx, outDy);

    if (inLength === 0 || outLength === 0) {
      path.push(`L ${current.x} ${current.y}`);
      continue;
    }

    const cornerRadius = Math.min(radius, inLength / 2, outLength / 2);
    const entry = {
      x: current.x - (inDx / inLength) * cornerRadius,
      y: current.y - (inDy / inLength) * cornerRadius,
    };
    const exit = {
      x: current.x + (outDx / outLength) * cornerRadius,
      y: current.y + (outDy / outLength) * cornerRadius,
    };

    path.push(`L ${entry.x} ${entry.y}`);
    path.push(`Q ${current.x} ${current.y} ${exit.x} ${exit.y}`);
  }

  return path.join(" ");
}

function buildForwardEdgePath(start, end, stageWidth, stageHeight) {
  const distance = Math.hypot(end.x - start.x, end.y - start.y);
  const handleLength = clamp(distance * 0.34, 56, 190);
  const control1X = clamp(start.x + handleLength, EDGE_STAGE_PADDING, stageWidth - EDGE_STAGE_PADDING);
  const control2X = clamp(end.x - handleLength, EDGE_STAGE_PADDING, stageWidth - EDGE_STAGE_PADDING);
  const startY = clamp(start.y, EDGE_STAGE_PADDING, stageHeight - EDGE_STAGE_PADDING);
  const endY = clamp(end.y, EDGE_STAGE_PADDING, stageHeight - EDGE_STAGE_PADDING);

  return `M ${start.x} ${startY} C ${control1X} ${startY}, ${control2X} ${endY}, ${end.x} ${endY}`;
}

function buildMirroredEdgePath(start, end, stageWidth, stageHeight) {
  const distance = Math.hypot(end.x - start.x, end.y - start.y);
  const handleLength = clamp(distance * 0.3, 44, 120);
  const control1X = clamp(start.x - handleLength, EDGE_STAGE_PADDING, stageWidth - EDGE_STAGE_PADDING);
  const control2X = clamp(end.x + handleLength, EDGE_STAGE_PADDING, stageWidth - EDGE_STAGE_PADDING);
  const startY = clamp(start.y, EDGE_STAGE_PADDING, stageHeight - EDGE_STAGE_PADDING);
  const endY = clamp(end.y, EDGE_STAGE_PADDING, stageHeight - EDGE_STAGE_PADDING);

  return `M ${start.x} ${startY} C ${control1X} ${startY}, ${control2X} ${endY}, ${end.x} ${endY}`;
}

function buildEnterRightAdaptivePath(sourceRect, targetRect, start, end, stageWidth, stageHeight) {
  const sourceAboveTarget = sourceRect.bottom <= targetRect.y;
  const sourceBelowTarget = sourceRect.y >= targetRect.bottom;
  const minTop = Math.min(sourceRect.y, targetRect.y);
  const maxBottom = Math.max(sourceRect.bottom, targetRect.bottom);
  const exitX = clamp(
    start.x - clamp(Math.abs(end.x - start.x) * 0.12, 38, 74),
    EDGE_STAGE_PADDING,
    stageWidth - EDGE_STAGE_PADDING,
  );
  const entryX = clamp(
    targetRect.right + clamp(Math.abs(targetRect.right - sourceRect.x) * 0.1, 42, 84),
    EDGE_STAGE_PADDING,
    stageWidth - EDGE_STAGE_PADDING,
  );
  const laneMargin = clamp(Math.abs(start.y - end.y) * 0.16, 36, 64);
  let laneY;

  if (sourceAboveTarget) {
    laneY = minTop - laneMargin;
  } else if (sourceBelowTarget) {
    laneY = maxBottom + laneMargin;
  } else if (start.y <= end.y) {
    laneY = maxBottom + laneMargin;
  } else {
    laneY = minTop - laneMargin;
  }

  laneY = clamp(laneY, EDGE_STAGE_PADDING, stageHeight - EDGE_STAGE_PADDING);

  return buildRoundedPolylinePath(
    [
      { x: clamp(start.x, EDGE_STAGE_PADDING, stageWidth - EDGE_STAGE_PADDING), y: clamp(start.y, EDGE_STAGE_PADDING, stageHeight - EDGE_STAGE_PADDING) },
      { x: exitX, y: clamp(start.y, EDGE_STAGE_PADDING, stageHeight - EDGE_STAGE_PADDING) },
      { x: exitX, y: laneY },
      { x: entryX, y: laneY },
      { x: entryX, y: clamp(end.y, EDGE_STAGE_PADDING, stageHeight - EDGE_STAGE_PADDING) },
      { x: clamp(end.x, EDGE_STAGE_PADDING, stageWidth - EDGE_STAGE_PADDING), y: clamp(end.y, EDGE_STAGE_PADDING, stageHeight - EDGE_STAGE_PADDING) },
    ],
    18,
  );
}

function buildBackwardEdgePath(sourceRect, targetRect, start, end, stageWidth, stageHeight) {
  const sourceAboveTarget = sourceRect.bottom <= targetRect.y;
  const sourceBelowTarget = sourceRect.y >= targetRect.bottom;
  const minTop = Math.min(sourceRect.y, targetRect.y);
  const maxBottom = Math.max(sourceRect.bottom, targetRect.bottom);
  const sideX = clamp(
    Math.max(sourceRect.right, targetRect.right) + clamp(Math.abs(start.x - end.x) * 0.12, 44, 86),
    EDGE_STAGE_PADDING,
    stageWidth - EDGE_STAGE_PADDING,
  );
  const laneMargin = clamp(Math.abs(start.y - end.y) * 0.16, 34, 62);
  let laneY;

  if (sourceAboveTarget) {
    laneY = minTop - laneMargin;
  } else if (sourceBelowTarget) {
    laneY = maxBottom + laneMargin;
  } else if (start.y <= end.y) {
    laneY = maxBottom + laneMargin;
  } else {
    laneY = minTop - laneMargin;
  }

  laneY = clamp(laneY, EDGE_STAGE_PADDING, stageHeight - EDGE_STAGE_PADDING);

  const entryX = clamp(
    end.x - clamp(Math.abs(sideX - end.x) * 0.18, 64, 104),
    EDGE_STAGE_PADDING,
    stageWidth - EDGE_STAGE_PADDING,
  );
  const radius = clamp(Math.min(18, Math.abs(laneY - end.y) * 0.38), 10, 18);

  return buildRoundedPolylinePath(
    [
      {
        x: clamp(start.x, EDGE_STAGE_PADDING, stageWidth - EDGE_STAGE_PADDING),
        y: clamp(start.y, EDGE_STAGE_PADDING, stageHeight - EDGE_STAGE_PADDING),
      },
      { x: sideX, y: clamp(start.y, EDGE_STAGE_PADDING, stageHeight - EDGE_STAGE_PADDING) },
      { x: sideX, y: laneY },
      { x: entryX, y: laneY },
      { x: entryX, y: clamp(end.y, EDGE_STAGE_PADDING, stageHeight - EDGE_STAGE_PADDING) },
      {
        x: clamp(end.x, EDGE_STAGE_PADDING, stageWidth - EDGE_STAGE_PADDING),
        y: clamp(end.y, EDGE_STAGE_PADDING, stageHeight - EDGE_STAGE_PADDING),
      },
    ],
    radius,
  );
}

function buildEdgePath(sourceRect, targetRect, start, end, stageWidth, stageHeight) {
  if (start.normalX === -1 && end.normalX === 1) {
    if (start.x < end.x - 28) {
      return buildEnterRightAdaptivePath(sourceRect, targetRect, start, end, stageWidth, stageHeight);
    }

    return buildMirroredEdgePath(start, end, stageWidth, stageHeight);
  }

  if (start.normalX === 1 && end.normalX === -1 && end.x >= start.x + 28) {
    return buildForwardEdgePath(start, end, stageWidth, stageHeight);
  }

  if (start.normalX === 1 && end.normalX === -1) {
    return buildBackwardEdgePath(sourceRect, targetRect, start, end, stageWidth, stageHeight);
  }

  if (end.x >= start.x + 28) {
    return buildMirroredEdgePath(start, end, stageWidth, stageHeight);
  }

  return buildRoundedPolylinePath(
    [
      { x: start.x, y: start.y },
      { x: (start.x + end.x) / 2, y: start.y },
      { x: (start.x + end.x) / 2, y: end.y },
      { x: end.x, y: end.y },
    ],
    16,
  );
}

function Header({ page, onNavigate }) {
  const nav = [
    { label: "Home", page: "home" },
    { label: "Team", page: "team" },
    { label: "Docs", page: null },
    { label: "Examples", page: null },
    { label: "Pricing", page: null },
    { label: "About", page: null },
  ];

  return (
    <header className="relative z-30 border-b border-[#9b365f] bg-[#131212]/95 backdrop-blur">
      <div className="flex h-[60px] w-full items-center justify-between px-8 lg:px-14 xl:px-16">
        <button type="button" className="flex items-center gap-3" onClick={() => onNavigate("home")}>
          <img src={beetrootLogo} alt="Beatrooter" className="h-7 w-7" />
          <span className="text-[21px] font-bold uppercase tracking-tight text-[#f7f4f6]">
            Beatrooter
          </span>
        </button>

        <div className="hidden items-center gap-12 md:flex">
          <nav className="flex items-center gap-10 xl:gap-11">
            {nav.map((item) => {
              const active = item.page && page === item.page;
              return (
                <button
                  key={item.label}
                  type="button"
                  onClick={() => item.page && onNavigate(item.page)}
                  className={`relative py-5 text-[13px] font-semibold tracking-tight transition ${
                    active ? "text-[#cf5b88]" : "text-[#c8c2c5] hover:text-white"
                  } ${item.page ? "" : "cursor-default"}`}
                >
                  {item.label}
                  {active && (
                    <span className="absolute inset-x-0 bottom-0 h-[2px] rounded-full bg-[#cf5b88]" />
                  )}
                </button>
              );
            })}
          </nav>

          <div className="flex items-center gap-5 xl:gap-6">
            <button type="button" aria-label="GitHub" className="text-[#e8e1e5] transition hover:text-white">
              <GitHubIcon />
            </button>
            <button type="button" aria-label="Theme" className="text-[#e8e1e5] transition hover:text-white">
              <SunMedium className="h-4.5 w-4.5" />
            </button>
            <button
              type="button"
              className="rounded-md bg-[#b34c79] px-5 py-2 text-[13px] font-semibold text-white transition hover:bg-[#c35b88]"
            >
              Get Started
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}

function GridBackground() {
  return (
    <>
      <div
        className="absolute inset-0"
        style={{
          backgroundColor: "#141212",
          backgroundImage:
            "radial-gradient(circle at center, rgba(255,255,255,0.14) 1.15px, transparent 1.15px)",
          backgroundSize: "40px 40px",
        }}
      />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_44%,rgba(108,85,181,0.14),transparent_28%)]" />
      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(20,18,18,0.14)_0%,rgba(20,18,18,0)_18%,rgba(20,18,18,0)_78%,rgba(20,18,18,0.2)_100%)]" />
    </>
  );
}

function FlowEdge({ path }) {
  return (
    <path
      d={path}
      stroke="#dd6ea3"
      strokeWidth="3.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="none"
      markerEnd="url(#flow-arrow)"
    />
  );
}

function FlowNode({ position, width, height, dragging, onPointerDown, children }) {
  return (
    <div
      className={`absolute select-none ${dragging ? "z-30 cursor-grabbing" : "z-20 cursor-grab"}`}
      style={{
        width,
        height,
        transform: `translate3d(${position.x}px, ${position.y}px, 0)`,
        touchAction: "none",
      }}
      onPointerDown={onPointerDown}
    >
      {children}
    </div>
  );
}

function CompactNode({ meta }) {
  const frameSize = meta.compactFrameSize ?? 112;

  return (
    <div className="flex h-full w-full items-center justify-center rounded-[22px] border border-white/22 bg-[#232323] shadow-[0_18px_34px_rgba(0,0,0,0.28)]">
      <div
        className="flex items-center justify-center rounded-[18px]"
        style={{ width: frameSize, height: frameSize }}
      >
        {renderNodeIcon(meta, true)}
      </div>
    </div>
  );
}

function ExpandedNode({ meta, onNavigate }) {
  const expandedFrameSize = meta.expandedFrameSize ?? 72;

  return (
    <div className="relative h-full overflow-hidden rounded-[28px] border border-white/12 bg-[#232323] shadow-[0_28px_70px_rgba(0,0,0,0.42)]">
      {meta.linkToPage && (
        <button
          type="button"
          aria-label={`Open ${meta.title}`}
          className="absolute right-4 top-4 z-20 flex h-8 w-8 items-center justify-center rounded-full border border-white/12 bg-black/20 text-white/75 transition hover:border-white/25 hover:bg-black/30 hover:text-white"
          onPointerDown={(event) => event.stopPropagation()}
          onClick={(event) => {
            event.stopPropagation();
            onNavigate(meta.linkToPage);
          }}
        >
          <ArrowUpRight className="h-4 w-4" />
        </button>
      )}

      <div
        className="flex h-[72px] items-center gap-5 border-b px-5"
        style={{
          borderColor: `${meta.accent}aa`,
          background: meta.headerBackground,
        }}
      >
        <div
          className="flex items-center justify-center rounded-[16px] bg-transparent"
          style={{ width: expandedFrameSize, height: expandedFrameSize, color: meta.accent }}
        >
          {renderNodeIcon(meta, false)}
        </div>
        <div className="font-['Chakra_Petch'] text-[24px] font-semibold uppercase tracking-[0.03em] text-[#f3f1fb]">
          {meta.title}
        </div>
      </div>

      <div className="px-5 py-4">
        <div className="text-[12px] font-bold uppercase tracking-[0.08em]" style={{ color: meta.accent }}>
          Output
        </div>
        <div className="mt-1.5 border-t border-dotted border-[#384a6e] pt-2.5">
          {meta.details.map(([label, value]) => (
            <div key={label} className="text-[13px] leading-[1.2] text-[#8c95aa]">
              <span className="mr-2 text-[#95a1b6]">{label}:</span>
              <span>{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function NodeRenderer({ config, nodeId, node, dragging, onPointerDown, onNavigate }) {
  const meta = config.nodes[nodeId];
  const size = getNodeSize(config, nodeId, node.expanded);

  return (
    <FlowNode
      position={node}
      width={size.width}
      height={size.height}
      dragging={dragging}
      onPointerDown={onPointerDown}
    >
      {node.expanded ? (
        <ExpandedNode meta={meta} onNavigate={onNavigate} />
      ) : (
        <CompactNode meta={meta} />
      )}
    </FlowNode>
  );
}

function FlowCanvas({ config, className = "", onNavigate }) {
  const stageRef = useRef(null);
  const dragRef = useRef(null);
  const clickRef = useRef({ nodeId: null, time: 0 });
  const [stageWidth, setStageWidth] = useState(config.maxWidth || DEFAULT_STAGE_WIDTH);
  const [draggingId, setDraggingId] = useState(null);
  const [nodes, setNodes] = useState(() =>
    config.getInitialNodes(config.maxWidth || DEFAULT_STAGE_WIDTH),
  );

  useEffect(() => {
    function measure() {
      if (!stageRef.current) {
        return;
      }

      setStageWidth(stageRef.current.clientWidth || config.maxWidth || DEFAULT_STAGE_WIDTH);
    }

    measure();
    window.addEventListener("resize", measure);

    return () => {
      window.removeEventListener("resize", measure);
    };
  }, [config.maxWidth]);

  useEffect(() => {
    function handlePointerMove(event) {
      const drag = dragRef.current;
      const stage = stageRef.current;

      if (!drag || !stage) {
        return;
      }

      const stageRect = stage.getBoundingClientRect();
      const deltaX = event.clientX - drag.startClientX;
      const deltaY = event.clientY - drag.startClientY;

      if (!drag.hasMoved && Math.hypot(deltaX, deltaY) >= DRAG_THRESHOLD_PX) {
        drag.hasMoved = true;
        setDraggingId(drag.nodeId);
      }

      if (!drag.hasMoved) {
        return;
      }

      setNodes((currentNodes) => {
        const currentNode = currentNodes[drag.nodeId];
        const size = getNodeSize(config, drag.nodeId, currentNode.expanded);
        const nextX = clamp(
          event.clientX - stageRect.left - drag.pointerOffsetX,
          0,
          Math.max(stageRect.width - size.width, 0),
        );
        const nextY = clamp(
          event.clientY - stageRect.top - drag.pointerOffsetY,
          0,
          config.stageHeight - size.height,
        );

        if (currentNode.x === nextX && currentNode.y === nextY) {
          return currentNodes;
        }

        return {
          ...currentNodes,
          [drag.nodeId]: {
            ...currentNode,
            x: nextX,
            y: nextY,
          },
        };
      });
    }

    function stopDragging() {
      const drag = dragRef.current;
      if (!drag) {
        return;
      }

      if (!drag.hasMoved) {
        const now = Date.now();
        if (clickRef.current.nodeId === drag.nodeId && now - clickRef.current.time <= DOUBLE_CLICK_MS) {
          setNodes((currentNodes) => toggleNodeExpansion(config, currentNodes, drag.nodeId, stageWidth));
          clickRef.current = { nodeId: null, time: 0 };
        } else {
          clickRef.current = { nodeId: drag.nodeId, time: now };
        }
      }

      dragRef.current = null;
      setDraggingId(null);
    }

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopDragging);
    window.addEventListener("pointercancel", stopDragging);

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", stopDragging);
      window.removeEventListener("pointercancel", stopDragging);
    };
  }, [config, stageWidth]);

  function handlePointerDown(event, nodeId) {
    if (!stageRef.current) {
      return;
    }

    const stageRect = stageRef.current.getBoundingClientRect();
    const node = nodes[nodeId];

    dragRef.current = {
      nodeId,
      pointerOffsetX: event.clientX - stageRect.left - node.x,
      pointerOffsetY: event.clientY - stageRect.top - node.y,
      startClientX: event.clientX,
      startClientY: event.clientY,
      hasMoved: false,
    };

    event.preventDefault();
  }

  const edges = config.edges.map((edge) => {
    const fromRect = getNodeRect(config, edge.from, nodes[edge.from]);
    const toRect = getNodeRect(config, edge.to, nodes[edge.to]);
    return buildEdgePath(
      fromRect,
      toRect,
      getPortPosition(config, edge.from, nodes[edge.from], edge.fromPort ?? "right", edge.fromOffsetY ?? 0),
      getPortPosition(config, edge.to, nodes[edge.to], edge.toPort ?? "left", edge.toOffsetY ?? 0),
      stageWidth,
      config.stageHeight,
    );
  });

  return (
    <section ref={stageRef} className={`relative w-full ${className}`}>
      <svg
        className="absolute inset-0 z-10 h-full w-full overflow-visible"
        viewBox={`0 0 ${stageWidth} ${config.stageHeight}`}
        fill="none"
        preserveAspectRatio="none"
      >
        <defs>
          <marker
            id="flow-arrow"
            markerWidth="18"
            markerHeight="18"
            refX="14"
            refY="9"
            orient="auto"
            markerUnits="userSpaceOnUse"
          >
            <path d="M 1 1 L 15 9 L 1 17 Z" fill="#dd6ea3" />
          </marker>
        </defs>

        {edges.map((edgePath) => (
          <FlowEdge key={edgePath} path={edgePath} />
        ))}
      </svg>

      {Object.keys(config.nodes).map((nodeId) => (
        <NodeRenderer
          key={nodeId}
          config={config}
          nodeId={nodeId}
          node={nodes[nodeId]}
          dragging={draggingId === nodeId}
          onPointerDown={(event) => handlePointerDown(event, nodeId)}
          onNavigate={onNavigate}
        />
      ))}
    </section>
  );
}

function HomePage({ onNavigate }) {
  return (
    <FlowCanvas
      config={HOME_CONFIG}
      className="mx-auto hidden h-[620px] max-w-[1280px] lg:block"
      onNavigate={onNavigate}
    />
  );
}

function TeamPage({ onNavigate }) {
  return (
    <div className="mx-auto flex w-full max-w-[1560px] justify-center px-4 py-6 lg:px-6">
      <section className="w-full rounded-[36px] border border-[#66605d] bg-[#292929] p-6 shadow-[0_40px_90px_rgba(0,0,0,0.42)]">
        <div className="relative rounded-[28px] border border-[#595451] bg-[#292929] shadow-[inset_0_0_0_1px_rgba(255,255,255,0.04),0_10px_24px_rgba(0,0,0,0.14)]">
          <div className="pointer-events-none absolute inset-x-0 top-0 z-30 flex items-center justify-between border-b border-[#625c59] px-5 py-3 text-[#ddd9df]">
            <div className="text-[18px] font-medium tracking-[0.02em] text-[#f0edf2]">Team</div>
            <div className="flex items-center gap-4 text-[15px] text-white/58">
              <span>5N</span>
              <span>0S</span>
            </div>
          </div>
          <div className="p-5 pt-[58px]">
            <FlowCanvas
              config={TEAM_CONFIG}
              className="mx-auto h-[620px] max-w-[1360px] overflow-hidden rounded-[24px] bg-transparent"
              onNavigate={onNavigate}
            />
          </div>
        </div>
      </section>
    </div>
  );
}

export default function BeatrooterLandingPage() {
  const [page, setPage] = useState(() =>
    typeof window === "undefined" ? "home" : getCurrentPageFromHash(),
  );

  useEffect(() => {
    function handleHashChange() {
      setPage(getCurrentPageFromHash());
    }

    window.addEventListener("hashchange", handleHashChange);
    return () => {
      window.removeEventListener("hashchange", handleHashChange);
    };
  }, []);

  function navigateToPage(nextPage) {
    if (nextPage === "team") {
      window.location.hash = "team";
      return;
    }

    window.history.replaceState(null, "", window.location.pathname + window.location.search);
    setPage("home");
  }

  return (
    <div className="min-h-screen overflow-hidden bg-[#141212] text-white">
      <Header page={page} onNavigate={navigateToPage} />

      <main className="relative min-h-[calc(100vh-60px)]">
        <GridBackground />
        {page === "team" ? <TeamPage onNavigate={navigateToPage} /> : <HomePage onNavigate={navigateToPage} />}
      </main>
    </div>
  );
}
