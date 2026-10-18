"use client";

import { useEffect, useState } from "react";
import { Plus, MessageSquare, Trash2, Sun, Moon, PanelLeftClose, PanelLeftOpen, Search, Edit } from "lucide-react";
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
      <div className="mb-6">
        <h3 className="text-xs font-semibold text-gray-500 mb-2 pl-2">{title}</h3>
        <div className="space-y-0.5">
          {group.map((s) => (
            <div
              key={s.id}
              className={`group flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors ${
                currentSessionId === s.id ? "bg-gray-200 dark:bg-gray-800 text-foreground" : "hover:bg-gray-100 dark:hover:bg-gray-800/50 text-foreground/80"
              }`}
              onClick={() => onSelectSession(s.id)}
            >
              <div className="flex items-center space-x-2 overflow-hidden">
                <span className="text-sm truncate max-w-[170px]">{s.title}</span>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteSession(s.id);
                }}
                className={`opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:text-red-500 text-gray-400`}
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
        className={`fixed inset-y-0 left-0 z-40 w-[260px] bg-sidebar border-r border-border/50 transform transition-transform duration-300 ease-in-out flex flex-col ${
          isSidebarOpen ? "translate-x-0" : "-translate-x-full"
        } md:relative md:translate-x-0`}
      >
        <div className="p-3 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-foreground hover:bg-gray-100 dark:hover:bg-gray-800 p-2 rounded-lg cursor-pointer transition-colors flex-1 mr-2">
            <span className="font-semibold text-sm">ComplyGH</span>
          </div>
          <div className="flex space-x-1">
            <button className="p-2 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-800 rounded-lg transition-colors">
              <Search className="w-4 h-4" />
            </button>
            <button 
              onClick={() => setIsSidebarOpen(false)}
              className="md:hidden p-2 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="px-3 pb-3 space-y-2 mt-1">
          <button
            onClick={onNewChat}
            className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg bg-gray-100 dark:bg-gray-800 text-foreground hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          >
            <div className="flex items-center space-x-2">
              <Edit className="w-4 h-4 text-foreground/80" />
              <span className="text-sm font-medium">New chat</span>
            </div>
          </button>
          
          <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-transparent text-sm text-foreground/80">
            <span className="text-sm">Temporary Chat</span>
            <button 
              onClick={() => setIsTemporary(!isTemporary)}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${isTemporary ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'}`}
            >
              <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${isTemporary ? 'translate-x-5' : 'translate-x-1'}`} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-3 pb-4 scrollbar-thin mt-2">
          {renderGroup("Today", today)}
          {renderGroup("Yesterday", yesterday)}
          {renderGroup("Previous 7 Days", previous)}
        </div>

        <div className="p-3">
          <button
            onClick={toggleTheme}
            className="flex items-center space-x-3 w-full p-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-foreground"
          >
            {theme === "light" ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
            <span className="text-sm font-medium">{theme === "light" ? "Dark Mode" : "Light Mode"}</span>
          </button>
        </div>
      </div>
      
      {!isSidebarOpen && (
        <button 
          className="fixed top-3 left-3 z-50 md:hidden bg-transparent p-2 rounded-md hover:bg-gray-100 text-foreground"
          onClick={() => setIsSidebarOpen(true)}
        >
          <PanelLeftOpen className="w-5 h-5" />
        </button>
      )}
    </>
  );
}
