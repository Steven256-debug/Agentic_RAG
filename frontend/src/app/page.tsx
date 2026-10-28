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

    try {
      // Get last 6 messages (excluding the one we just pushed, to use as history)
      const historyMsgCount = 6;
      const history = newSessions[sessionIndex].messages
        .slice(0, -1)
        .slice(-historyMsgCount)
        .map(m => ({ role: m.role, content: m.content }));

      // Dynamically resolve API URL: prioritize environment variable (for Vercel/production), fallback to LAN IP for local dev
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

      // Add a 90-second abort timeout for clear UX feedback on free-tier cold starts
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 90000);
      
      let response: Response;
      try {
        response = await fetch(`${apiUrl}/ask`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: content,
            history,
            corrective,
            routing,
            session_id: sessionId
          }),
          signal: controller.signal
        });
      } catch (fetchErr: unknown) {
        clearTimeout(timeoutId);
        const fErr = fetchErr as Error;
        if (fErr.name === "AbortError") {
          throw new Error("Request timed out. The backend server or AI model took too long to respond. Render free tier servers take ~40s to wake up on the first request; please retry now.");
        }
        throw new Error(`Unable to connect to ComplyGH API (${apiUrl}). Please ensure your backend service is running.`);
      } finally {
        clearTimeout(timeoutId);
      }

      if (!response.ok) {
        if (response.status === 429) {
          let detail = "Gemini API daily quota limit reached (Free Tier daily limit exceeded). Please try a fresh Gemini API key in your Render environment variables.";
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
            if (typeof errorData.detail === 'string') {
               errorMessage = errorData.detail;
            } else if (errorData.detail.message) {
               errorMessage = errorData.detail.message;
            }
          }
        } catch (e) {
          // Ignore JSON parse errors if the response isn't JSON
        }
        
        throw new Error(errorMessage);
      }

      const data = await response.json();
      
      const assistantMsg: Message = {
        role: "assistant",
        content: data.answer,
        sources: data.sources,
      };

      // Append the assistant's message to the current session.
      newSessions[sessionIndex].messages.push(assistantMsg);
      newSessions[sessionIndex].updatedAt = Date.now();
      saveSessions([...newSessions]);
      
    } catch (err: unknown) {
      const e = err as Error;
      setError(e.message || "An unexpected error occurred.");
    } finally {
      setIsLoading(false);
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

