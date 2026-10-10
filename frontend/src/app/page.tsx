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

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      
      const response = await fetch(`${apiUrl}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: content,
          history,
          corrective,
          routing
        }),
      });

      if (!response.ok) {
        if (response.status === 429) {
          throw new Error("Rate limit exceeded. Please wait a moment and try again.");
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

      // Create typewriter effect simulation in state updates, or simply add message and let ChatArea handle visual
      // For simplicity and stability, we append it. ChatArea has a framer-motion transition.
      
      // Append the assistant's message to the current session.
      // We use the `newSessions` array created at the start of the function 
      // instead of the `sessions` state to avoid a stale closure bug.
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
    <div className="flex h-screen w-full overflow-hidden bg-background">
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
           const lastUserMessage = currentMessages.slice().reverse().find(m => m.role === "user");
           if (lastUserMessage) {
             // In a real app we'd pop the error and resend. Here we'll just try to send again 
             // without duplicating it if we wanted, but easiest is just to fire the send with the same content.
             handleSendMessage(lastUserMessage.content, true, true);
           }
        }}
      />
    </div>
  );
}
