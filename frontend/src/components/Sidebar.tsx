"use client";

import { useEffect, useRef, useState } from "react";
import {
  Plus,
  MessageSquare,
  Trash2,
  Sun,
  Moon,
  PanelLeftClose,
  Search,
  X,
} from "lucide-react";
import { ChatSession } from "@/lib/types";

export function ComplyMark({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <path
        d="M12 2.5L4.5 5.6V11.8C4.5 16.5 7.7 20.4 12 21.8C16.3 20.4 19.5 16.5 19.5 11.8V5.6L12 2.5Z"
        stroke="currentColor"
        strokeWidth="1.65"
        strokeLinejoin="round"
      />
      <path
        d="M8.5 10.5H15.5M8.5 13.75H13.25"
        stroke="currentColor"
        strokeWidth="1.65"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function Sidebar({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  isSidebarOpen,
  setIsSidebarOpen,
  isDesktopRailOpen,
  setIsDesktopRailOpen,
  isTemporary,
  setIsTemporary,
}: {
  sessions: ChatSession[];
  currentSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void;
  isSidebarOpen: boolean;
  setIsSidebarOpen: (v: boolean) => void;
  isDesktopRailOpen: boolean;
  setIsDesktopRailOpen: (v: boolean) => void;
  isTemporary: boolean;
  setIsTemporary: (v: boolean) => void;
}) {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [now, setNow] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [isNarrowViewport, setIsNarrowViewport] = useState(false);
  const asideRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const isDark = document.documentElement.classList.contains("dark");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTheme(isDark ? "dark" : "light");
    setNow(Date.now());

    const mq = window.matchMedia("(max-width: 59.99rem)");
    const syncViewport = () => setIsNarrowViewport(mq.matches);
    syncViewport();
    mq.addEventListener("change", syncViewport);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isSidebarOpen) {
        setIsSidebarOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      mq.removeEventListener("change", syncViewport);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isSidebarOpen, setIsSidebarOpen]);

  const isDrawerHidden = isNarrowViewport
    ? !isSidebarOpen
    : !isDesktopRailOpen;

  useEffect(() => {
    const el = asideRef.current;
    if (!el) return;
    if (isDrawerHidden) {
      el.setAttribute("inert", "");
    } else {
      el.removeAttribute("inert");
    }
  }, [isDrawerHidden]);

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light";
    setTheme(newTheme);
    if (newTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    try {
      localStorage.setItem("complygh_theme", newTheme);
    } catch {
      // Ignore storage failures in restricted contexts
    }
  };

  const filteredSessions = searchQuery.trim()
    ? sessions.filter((s) =>
        s.title.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : sessions;

  const groupSessions = (sessList: ChatSession[]) => {
    const msInDay = 86400000;
    const today: ChatSession[] = [];
    const yesterday: ChatSession[] = [];
    const previous: ChatSession[] = [];

    [...sessList]
      .sort((a, b) => b.updatedAt - a.updatedAt)
      .forEach((s) => {
        const diff = now - s.updatedAt;
        if (diff < msInDay) {
          today.push(s);
        } else if (diff < msInDay * 2) {
          yesterday.push(s);
        } else {
          previous.push(s);
        }
      });

    return { today, yesterday, previous };
  };

  const { today, yesterday, previous } =
    now > 0
      ? groupSessions(filteredSessions)
      : { today: [], yesterday: [], previous: [] };

  const renderGroup = (title: string, group: ChatSession[]) => {
    if (group.length === 0) return null;
    return (
      <section className="mb-5" aria-label={title}>
        <h2 className="text-xs font-medium text-muted mb-1.5 px-2">
          {title}
        </h2>
        <div className="space-y-0.5">
          {group.map((s) => {
            const isActive = currentSessionId === s.id;
            return (
              <div
                key={s.id}
                className={`group flex items-center justify-between rounded-pill transition-colors min-h-[40px] border-l-2 ${
                  isActive
                    ? "bg-paper-3 border-accent text-ink font-medium"
                    : "border-transparent hover:bg-paper-3/60 text-ink-2 hover:text-ink"
                }`}
              >
                <button
                  type="button"
                  onClick={() => onSelectSession(s.id)}
                  className="flex items-center gap-2.5 px-2.5 py-2 flex-1 min-w-0 text-left rounded-pill min-h-[40px] cursor-pointer active:translate-y-px transition-transform duration-150"
                >
                  <MessageSquare
                    className={`w-4 h-4 flex-shrink-0 ${
                      isActive ? "text-accent-text" : "text-muted"
                    }`}
                  />
                  <span className="text-sm truncate">{s.title}</span>
                </button>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteSession(s.id);
                  }}
                  className="hit-target opacity-100 min-[60rem]:opacity-0 min-[60rem]:group-hover:opacity-100 min-[60rem]:group-focus-within:opacity-100 focus-visible:opacity-100 transition-[opacity,color,background-color] mr-1 p-1.5 rounded-pill text-muted hover:text-bad hover:bg-bad-soft active:translate-y-px min-w-[34px] min-h-[34px] flex items-center justify-center cursor-pointer flex-shrink-0"
                  aria-label={`Delete chat: ${s.title}`}
                  title="Delete chat"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      </section>
    );
  };

  return (
    <>
      {/* Mobile Drawer Backdrop */}
      {isSidebarOpen && (
        <div
          onClick={() => setIsSidebarOpen(false)}
          className="fixed inset-0 bg-scrim z-40 min-[60rem]:hidden transition-opacity duration-200"
          aria-hidden="true"
        />
      )}

      {/* Sidebar Drawer / Collapsible Desktop Rail */}
      <aside
        ref={asideRef}
        aria-label="Workspace navigation"
        aria-hidden={isDrawerHidden || undefined}
        className={`fixed inset-y-0 left-0 z-50 w-72 bg-paper-2 border-r border-rule transform transition-[transform,margin] duration-200 ease-out flex flex-col pb-safe pt-safe min-[60rem]:pt-0 min-[60rem]:pb-0 min-[60rem]:relative flex-shrink-0 ${
          isSidebarOpen ? "translate-x-0" : "-translate-x-full"
        } ${
          isDesktopRailOpen
            ? "min-[60rem]:translate-x-0"
            : "min-[60rem]:-ml-72 min-[60rem]:-translate-x-full"
        }`}
      >
        {/* Brand Masthead */}
        <div className="h-14 px-4 flex items-center justify-between border-b border-rule flex-shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="w-7 h-7 rounded-pill bg-brand text-brand-ink flex items-center justify-center flex-shrink-0">
              <ComplyMark className="w-4 h-4" />
            </span>
            <span className="font-display font-medium text-base tracking-[-0.02em] text-ink truncate">
              ComplyGH
            </span>
          </div>

          <div className="flex items-center gap-1 flex-shrink-0">
            <button
              type="button"
              onClick={() => setIsSearching(!isSearching)}
              aria-pressed={isSearching}
              className={`hit-target p-2 rounded-pill transition-[background-color,color,transform] active:translate-y-px min-w-[40px] min-h-[40px] flex items-center justify-center cursor-pointer ${
                isSearching
                  ? "bg-paper-3 text-ink"
                  : "text-muted hover:text-ink hover:bg-paper-3"
              }`}
              title="Search history"
              aria-label="Search history"
            >
              <Search className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => {
                if (isNarrowViewport) {
                  setIsSidebarOpen(false);
                } else {
                  setIsDesktopRailOpen(false);
                }
              }}
              className="hit-target text-muted hover:text-ink p-2 rounded-pill hover:bg-paper-3 active:translate-y-px min-w-[40px] min-h-[40px] flex items-center justify-center cursor-pointer transition-[background-color,color,transform]"
              aria-label="Collapse sidebar"
              title="Collapse sidebar"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Search bar when toggled */}
        {isSearching && (
          <div className="px-3 pt-3">
            <div className="relative flex items-center">
              <Search className="w-3.5 h-3.5 text-muted absolute left-3 pointer-events-none" />
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter inquiries…"
                aria-label="Filter inquiries"
                className="w-full text-sm min-h-[40px] pl-8 pr-9 rounded-pill bg-paper-3 border border-muted text-ink placeholder:text-muted outline-2 outline-transparent -outline-offset-2 focus-visible:outline-focus"
                autoFocus
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  aria-label="Clear filter"
                  className="hit-target absolute right-1.5 p-1.5 text-muted hover:text-ink active:translate-y-px rounded-pill cursor-pointer min-w-[32px] min-h-[32px] flex items-center justify-center"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Primary Action & Temporary Mode */}
        <div className="p-3 space-y-2.5 border-b border-rule">
          <button
            type="button"
            onClick={onNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 min-h-[40px] rounded-pill bg-accent text-accent-ink font-medium text-sm hover:bg-accent-hover active:translate-y-px transition-[background-color,transform] duration-150 cursor-pointer whitespace-nowrap"
          >
            <Plus className="w-4 h-4 flex-shrink-0" />
            <span>New Chat</span>
          </button>

          <div className="flex items-center justify-between px-2 py-1.5 rounded-pill">
            <div className="min-w-0 pr-2">
              <span
                id="temp-chat-label"
                className="text-sm font-medium text-ink-2 block"
              >
                Temporary Chat
              </span>
              {isTemporary && (
                <span className="text-xs text-accent-text block">
                  Not saved to history
                </span>
              )}
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={isTemporary}
              aria-labelledby="temp-chat-label"
              onClick={() => setIsTemporary(!isTemporary)}
              className={`hit-target relative inline-flex h-6 w-10 items-center rounded-full border transition-colors cursor-pointer flex-shrink-0 ${
                isTemporary
                  ? "bg-accent border-accent"
                  : "bg-paper-3 border-muted"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full transition-transform ${
                  isTemporary
                    ? "translate-x-5 bg-accent-ink"
                    : "translate-x-1 bg-muted"
                }`}
              />
            </button>
          </div>
        </div>

        {/* Chat History List */}
        <div className="flex-1 overflow-y-auto px-2.5 py-3 smooth-scroll">
          {filteredSessions.length === 0 ? (
            <div className="px-2.5 py-6">
              <p className="text-sm font-medium text-ink-2 mb-1">
                {searchQuery ? "No matching inquiries" : "No saved inquiries"}
              </p>
              <p className="text-xs text-muted leading-relaxed">
                {searchQuery
                  ? "Clear the search filter to view all sessions."
                  : "Start a compliance query to build your session log."}
              </p>
            </div>
          ) : (
            <>
              {renderGroup("Today", today)}
              {renderGroup("Yesterday", yesterday)}
              {renderGroup("Previous 7 Days", previous)}
            </>
          )}
        </div>

        {/* Footer Theme Toggle */}
        <div className="p-3 border-t border-rule flex-shrink-0">
          <button
            type="button"
            onClick={toggleTheme}
            className="flex items-center justify-between w-full px-3 min-h-[44px] rounded-pill hover:bg-paper-3 active:translate-y-px transition-[background-color,color,transform] text-ink-2 hover:text-ink cursor-pointer"
          >
            <span className="flex items-center gap-2.5 text-sm font-medium">
              {theme === "light" ? (
                <Moon className="w-4 h-4 text-muted" />
              ) : (
                <Sun className="w-4 h-4 text-accent-text" />
              )}
              <span>{theme === "light" ? "Dark Mode" : "Light Mode"}</span>
            </span>
            <span className="text-xs text-muted">
              {theme === "light" ? "Paper" : "Graphite"}
            </span>
          </button>
        </div>
      </aside>
    </>
  );
}
