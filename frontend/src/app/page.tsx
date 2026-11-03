"use client";

import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import ChatArea from "@/components/ChatArea";
import { ChatSession, Message } from "@/lib/types";

export default function Home() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isTemporary, setIsTemporary] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("complygh_sessions");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // eslint-disable-next-line
        setSessions(parsed);
        if (parsed.length > 0) {
          // eslint-disable-next-line
          setCurrentSessionId(parsed[0].id);
        }
      } catch (e) {
        console.error("Failed to parse sessions", e);
      }
    }
  }, []);

  // Pre-warm the backend as soon as the page loads so cold start
  // happens silently in the background, not on the user's first query.
  useEffect(() => {
    let apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      if (typeof window !== "undefined") {
        const host = window.location.hostname;
        apiUrl = (host && host !== "localhost" && host !== "127.0.0.1")
          ? `http://${host}:8000`
          : "http://127.0.0.1:8000";
      } else {
        apiUrl = "http://127.0.0.1:8000";
      }
    }
    apiUrl = apiUrl.replace(/\/+$/, "");
    // Fire-and-forget: just wake the server up, ignore errors
    fetch(`${apiUrl}/ping`, { method: "GET" }).catch(() => {});
  }, []);

  const saveSessions = (newSessions: ChatSession[]) => {
    setSessions(newSessions);
    const permanentSessions = newSessions.filter(s => !s.isTemporary);
    localStorage.setItem("complygh_sessions", JSON.stringify(permanentSessions));
  };

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setIsSidebarOpen(false); // close sidebar on mobile after action
  };

  const handleDeleteSession = (id: string) => {
    const newSessions = sessions.filter((s) => s.id !== id);
    saveSessions(newSessions);
    if (currentSessionId === id) {
      setCurrentSessionId(newSessions.length > 0 ? newSessions[0].id : null);
    }
  };

  const currentSession = sessions.find((s) => s.id === currentSessionId);
  const currentMessages = currentSession ? currentSession.messages : [];

  const handleSendMessage = async (content: string, corrective: boolean, routing: boolean) => {
    setError(null);
    setIsWarmingUp(false);
    
    // Create new message
    const userMsg: Message = { role: "user", content };
    let sessionId = currentSessionId;
    const newSessions = [...sessions];
    let sessionIndex = newSessions.findIndex((s) => s.id === sessionId);

    if (!sessionId || sessionIndex === -1) {
      // New session
      sessionId = crypto.randomUUID();
      const newSession: ChatSession = {
        id: sessionId,
        title: content.length > 30 ? content.slice(0, 30) + "..." : content,
        messages: [userMsg],
        updatedAt: Date.now(),
        isTemporary,
      };
      newSessions.unshift(newSession);
      sessionIndex = 0;
      setCurrentSessionId(sessionId);
    } else {
      newSessions[sessionIndex].messages.push(userMsg);
      newSessions[sessionIndex].updatedAt = Date.now();
    }
    
    saveSessions(newSessions);
    setIsLoading(true);

    // Resolve API URL
    let apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      apiUrl = "http://127.0.0.1:8000";
      if (typeof window !== "undefined") {
        const host = window.location.hostname;
        if (host && host !== "localhost" && host !== "127.0.0.1") {
          apiUrl = `http://${host}:8000`;
        }
      }
    }
    apiUrl = apiUrl.replace(/\/+$/, "");

    const doFetch = async (timeoutMs: number): Promise<Response> => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const history = newSessions[sessionIndex].messages
          .slice(0, -1)
          .slice(-6)
          .map(m => ({ role: m.role, content: m.content }));

        const response = await fetch(`${apiUrl}/ask`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: content,
            history,
            corrective,
            routing,
            session_id: sessionId,
          }),
          signal: controller.signal,
        });
        return response;
      } finally {
        clearTimeout(timeoutId);
      }
    };

    try {
      let response: Response;

      try {
        // First attempt: 55 second timeout (enough for a warm server)
        response = await doFetch(55000);
      } catch (firstErr: unknown) {
        const e = firstErr as Error;
        if (e.name === "AbortError") {
          // Cold start detected — show warm-up notice and retry with a longer timeout
          setIsWarmingUp(true);
          try {
            response = await doFetch(90000);
          } catch (retryErr: unknown) {
            const re = retryErr as Error;
            if (re.name === "AbortError") {
              throw new Error(
                "The server is taking longer than usual to wake up. Please wait a moment and try again."
              );
            }
            throw re;
          } finally {
            setIsWarmingUp(false);
          }
        } else {
          throw new Error(
            `Unable to connect to ComplyGH API (${apiUrl}). Please ensure your backend service is running.`
          );
        }
      }

      setIsWarmingUp(false);

      if (!response.ok) {
        if (response.status === 429) {
          let detail = "Gemini API daily quota limit reached. Please try again later.";
          try {
            const d = await response.json();
            if (d && d.detail) detail = d.detail;
          } catch (_) {}
          throw new Error(detail);
        }
        let errorMessage = "Failed to connect to the server.";
        try {
          const errorData = await response.json();
          if (errorData && errorData.detail) {
            errorMessage = typeof errorData.detail === "string"
              ? errorData.detail
              : errorData.detail.message ?? errorMessage;
          }
        } catch (_) {}
        throw new Error(errorMessage);
      }

      const data = await response.json();
      const assistantMsg: Message = {
        role: "assistant",
        content: data.answer,
        sources: data.sources,
      };

      newSessions[sessionIndex].messages.push(assistantMsg);
      newSessions[sessionIndex].updatedAt = Date.now();
      saveSessions([...newSessions]);

    } catch (err: unknown) {
      const e = err as Error;
      setError(e.message || "An unexpected error occurred.");
    } finally {
      setIsLoading(false);
      setIsWarmingUp(false);
    }
  };

  return (
    <div className="flex h-[100dvh] w-full overflow-hidden bg-background">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={(id) => {
          setCurrentSessionId(id);
          setIsSidebarOpen(false);
        }}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        isSidebarOpen={isSidebarOpen}
        setIsSidebarOpen={setIsSidebarOpen}
        isTemporary={isTemporary}
        setIsTemporary={setIsTemporary}
      />
      <ChatArea
        messages={currentMessages}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
        isWarmingUp={isWarmingUp}
        error={error}
        onRetry={() => {
          const lastUserMessage = currentMessages.slice().reverse().find((m) => m.role === "user");
          if (lastUserMessage) {
            handleSendMessage(lastUserMessage.content, true, true);
          }
        }}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        onNewChat={handleNewChat}
      />
    </div>
  );
}

