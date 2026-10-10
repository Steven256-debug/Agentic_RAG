"use client";

import { useEffect, useState } from "react";
import { Plus, MessageSquare, Trash2, ShieldCheck, Sun, Moon, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { ChatSession } from "@/lib/types";

export default function Sidebar({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  isSidebarOpen,
  setIsSidebarOpen,
}: {
  sessions: ChatSession[];
  currentSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void;
  isSidebarOpen: boolean;
  setIsSidebarOpen: (v: boolean) => void;
}) {
  const [theme, setTheme] = useState<"light" | "dark">("light");

  const [now, setNow] = useState(0);

  useEffect(() => {
    const isDark = document.documentElement.classList.contains("dark");
    // eslint-disable-next-line
    setTheme(isDark ? "dark" : "light");
    setNow(Date.now());
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light";
    setTheme(newTheme);
    if (newTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };

  const groupSessions = (sessions: ChatSession[], currentTime: number) => {
    const msInDay = 86400000;
    
    const today: ChatSession[] = [];
    const yesterday: ChatSession[] = [];
    const previous: ChatSession[] = [];

    sessions.sort((a, b) => b.updatedAt - a.updatedAt).forEach((s) => {
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

  const { today, yesterday, previous } = now > 0 ? groupSessions(sessions, now) : { today: [], yesterday: [], previous: [] };

  const renderGroup = (title: string, group: ChatSession[]) => {
    if (group.length === 0) return null;
    return (
      <div className="mb-4">
        <h3 className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">{title}</h3>
        <div className="space-y-1">
          {group.map((s) => (
            <div
              key={s.id}
              className={`group flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors ${
                currentSessionId === s.id ? "bg-primary text-white" : "hover:bg-primary/10 text-foreground"
              }`}
              onClick={() => onSelectSession(s.id)}
            >
              <div className="flex items-center space-x-2 overflow-hidden">
                <MessageSquare className="w-4 h-4 flex-shrink-0" />
                <span className="text-sm truncate max-w-[140px]">{s.title}</span>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteSession(s.id);
                }}
                className={`opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-md hover:bg-red-500 hover:text-white ${currentSessionId === s.id ? "text-white" : "text-gray-400"}`}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <>
      <div
        className={`fixed inset-y-0 left-0 z-40 w-64 bg-sidebar border-r border-border transform transition-transform duration-300 ease-in-out flex flex-col ${
          isSidebarOpen ? "translate-x-0" : "-translate-x-full"
        } md:relative md:translate-x-0`}
      >
        <div className="p-4 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-primary dark:text-accent">
            <ShieldCheck className="w-6 h-6" />
            <span className="font-bold text-xl tracking-tight">ComplyGH</span>
          </div>
          <button className="md:hidden text-foreground" onClick={() => setIsSidebarOpen(false)}>
            <PanelLeftClose className="w-5 h-5" />
          </button>
        </div>

        <div className="px-4 pb-4">
          <button
            onClick={onNewChat}
            className="w-full flex items-center space-x-2 px-4 py-2 rounded-xl bg-accent text-primary font-medium hover:bg-accent-hover transition-colors"
          >
            <Plus className="w-5 h-5" />
            <span>New Chat</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 pb-4 scrollbar-thin">
          {renderGroup("Today", today)}
          {renderGroup("Yesterday", yesterday)}
          {renderGroup("Previous 7 Days", previous)}
        </div>

        <div className="p-4 border-t border-border">
          <button
            onClick={toggleTheme}
            className="flex items-center space-x-3 w-full p-2 rounded-lg hover:bg-primary/10 transition-colors text-foreground"
          >
            {theme === "light" ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            <span className="text-sm font-medium">{theme === "light" ? "Dark Mode" : "Light Mode"}</span>
          </button>
        </div>
      </div>
      
      {!isSidebarOpen && (
        <button 
          className="fixed top-4 left-4 z-50 md:hidden bg-card p-2 rounded-md shadow-md border border-border"
          onClick={() => setIsSidebarOpen(true)}
        >
          <PanelLeftOpen className="w-5 h-5" />
        </button>
      )}
    </>
  );
}
