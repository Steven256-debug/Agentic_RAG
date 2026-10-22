"use client";

import { useEffect, useState } from "react";
import { Plus, MessageSquare, Trash2, ShieldCheck, Sun, Moon, PanelLeftClose, Search, X } from "lucide-react";
import { ChatSession } from "@/lib/types";

export default function Sidebar({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  isSidebarOpen,
  setIsSidebarOpen,
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
  isTemporary: boolean;
  setIsTemporary: (v: boolean) => void;
}) {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [now, setNow] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    const isDark = document.documentElement.classList.contains("dark");
    // eslint-disable-next-line
    setTheme(isDark ? "dark" : "light");
    setNow(Date.now());

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isSidebarOpen) {
        setIsSidebarOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isSidebarOpen, setIsSidebarOpen]);

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light";
    setTheme(newTheme);
    if (newTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };

  const filteredSessions = searchQuery.trim()
    ? sessions.filter((s) => s.title.toLowerCase().includes(searchQuery.toLowerCase()))
    : sessions;

  const groupSessions = (sessList: ChatSession[]) => {
    const msInDay = 86400000;
    const today: ChatSession[] = [];
    const yesterday: ChatSession[] = [];
    const previous: ChatSession[] = [];

    [...sessList].sort((a, b) => b.updatedAt - a.updatedAt).forEach((s) => {
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

  const { today, yesterday, previous } = now > 0 ? groupSessions(filteredSessions) : { today: [], yesterday: [], previous: [] };

  const renderGroup = (title: string, group: ChatSession[]) => {
    if (group.length === 0) return null;
    return (
      <div className="mb-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2 pl-1">{title}</h3>
        <div className="space-y-1">
          {group.map((s) => (
            <div
              key={s.id}
              className={`group flex items-center justify-between p-2.5 rounded-xl cursor-pointer transition-colors min-h-[42px] ${
                currentSessionId === s.id
                  ? "bg-primary text-white font-medium shadow-xs"
                  : "hover:bg-primary/10 text-foreground active:bg-primary/20"
              }`}
              onClick={() => onSelectSession(s.id)}
            >
              <div className="flex items-center space-x-2.5 overflow-hidden flex-1 mr-1">
                <MessageSquare className={`w-4 h-4 flex-shrink-0 ${currentSessionId === s.id ? "text-white" : "text-gray-400 group-hover:text-primary"}`} />
                <span className="text-sm truncate">{s.title}</span>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteSession(s.id);
                }}
                className={`opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-red-500 hover:text-white min-w-[32px] min-h-[32px] flex items-center justify-center ${
                  currentSessionId === s.id ? "text-white/80 hover:text-white" : "text-gray-400"
                }`}
                aria-label="Delete chat"
                title="Delete chat"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <>
      {/* Mobile Drawer Backdrop */}
      {isSidebarOpen && (
        <div
          onClick={() => setIsSidebarOpen(false)}
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40 md:hidden transition-opacity duration-300"
          aria-label="Close sidebar"
        />
      )}

      {/* Sidebar Drawer */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-sidebar border-r border-border transform transition-transform duration-300 ease-in-out flex flex-col shadow-2xl md:shadow-none md:relative md:translate-x-0 pb-safe pt-safe md:pt-0 md:pb-0 ${
          isSidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Brand Header */}
        <div className="p-4 flex items-center justify-between border-b border-border/40 md:border-none">
          <div className="flex items-center space-x-2 text-primary dark:text-accent">
            <ShieldCheck className="w-6 h-6" />
            <span className="font-bold text-xl tracking-tight">ComplyGH</span>
          </div>

          <div className="flex items-center space-x-1">
            <button
              type="button"
              onClick={() => setIsSearching(!isSearching)}
              className="p-2 text-gray-500 hover:text-foreground hover:bg-gray-200 dark:hover:bg-gray-800 rounded-lg transition-colors min-w-[38px] min-h-[38px] flex items-center justify-center"
              title="Search history"
              aria-label="Search history"
            >
              <Search className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => setIsSidebarOpen(false)}
              className="md:hidden text-foreground p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 min-w-[38px] min-h-[38px] flex items-center justify-center"
              aria-label="Close menu"
            >
              <PanelLeftClose className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Search bar when toggled */}
        {isSearching && (
          <div className="px-4 pb-2">
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search history..."
                className="w-full text-xs py-1.5 pl-7 pr-7 rounded-lg bg-card border border-border text-foreground placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-primary"
                autoFocus
              />
              <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2 top-2" />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2 top-2 text-gray-400 hover:text-foreground"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Primary New Chat Button in Gold Accent */}
        <div className="px-4 pb-4 space-y-3">
          <button
            type="button"
            onClick={onNewChat}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl bg-accent text-primary font-semibold hover:bg-accent-hover active:scale-[0.98] transition-all shadow-xs min-h-[42px]"
          >
            <Plus className="w-5 h-5" />
            <span>New Chat</span>
          </button>

          <div className="flex items-center justify-between px-2 text-sm text-foreground">
            <span className="font-medium text-gray-500 dark:text-gray-400">Temporary Chat</span>
            <button
              type="button"
              onClick={() => setIsTemporary(!isTemporary)}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                isTemporary ? "bg-accent" : "bg-gray-300 dark:bg-gray-600"
              }`}
              aria-label="Toggle temporary chat"
            >
              <span
                className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                  isTemporary ? "translate-x-5" : "translate-x-1"
                }`}
              />
            </button>
          </div>
        </div>

        {/* Chat History List */}
        <div className="flex-1 overflow-y-auto px-4 pb-4 scrollbar-thin smooth-scroll">
          {filteredSessions.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-xs text-gray-400">
                {searchQuery ? "No matching chats found." : "No saved chats yet."}
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
        <div className="p-4 border-t border-border">
          <button
            type="button"
            onClick={toggleTheme}
            className="flex items-center space-x-3 w-full p-2.5 rounded-lg hover:bg-primary/10 transition-colors text-foreground min-h-[42px]"
          >
            {theme === "light" ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            <span className="text-sm font-medium">{theme === "light" ? "Dark Mode" : "Light Mode"}</span>
          </button>
        </div>
      </aside>
    </>
  );
}


