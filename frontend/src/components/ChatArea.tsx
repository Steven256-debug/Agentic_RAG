"use client";

import { useState, useRef, useEffect } from "react";
import { Message, Source } from "@/lib/types";
import {
  Send,
  Plus,
  ChevronDown,
  ChevronRight,
  Copy,
  CheckCircle2,
  ShieldCheck,
  PanelLeftOpen,
  Settings2,
  Globe,
  FileText,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { motion, AnimatePresence } from "framer-motion";

export default function ChatArea({
  messages,
  onSendMessage,
  isLoading,
  error,
  onRetry,
  onToggleSidebar,
  onNewChat,
}: {
  messages: Message[];
  onSendMessage: (msg: string, corrective: boolean, routing: boolean) => void;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  onToggleSidebar: () => void;
  onNewChat: () => void;
}) {
  const [input, setInput] = useState("");
  const [corrective, setCorrective] = useState(false);
  const [routing, setRouting] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isEmpty = messages.length === 0;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input, corrective, routing);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && window.innerWidth >= 768) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
  };

  return (
    <div className="flex-1 flex flex-col bg-background h-[100dvh] relative overflow-hidden">
      {/* Mobile Top Header */}
      <header className="md:hidden h-14 border-b border-border bg-background/95 backdrop-blur-md flex items-center justify-between px-3 sticky top-0 z-30 flex-shrink-0">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="p-2 -ml-1 text-foreground/80 hover:text-foreground active:bg-gray-100 dark:active:bg-gray-800 rounded-xl transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
          aria-label="Open sidebar"
        >
          <PanelLeftOpen className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-2 text-primary dark:text-accent">
          <ShieldCheck className="w-5 h-5" />
          <span className="font-bold text-base tracking-tight">ComplyGH</span>
        </div>

        <button
          type="button"
          onClick={onNewChat}
          className="p-2 -mr-1 text-foreground/80 hover:text-foreground active:bg-gray-100 dark:active:bg-gray-800 rounded-xl transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
          aria-label="New chat"
        >
          <Plus className="w-5 h-5" />
        </button>
      </header>

      {isEmpty ? (
        // --- EMPTY STATE (ComplyGH Original) ---
        <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 text-center overflow-y-auto smooth-scroll">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 sm:mb-8 flex flex-col items-center max-w-lg"
          >
            <ShieldCheck className="w-16 h-16 sm:w-20 sm:h-20 text-primary dark:text-accent mb-3 sm:mb-4 drop-shadow-sm" />
            <h1 className="text-3xl sm:text-4xl font-bold text-primary dark:text-gray-100 mb-2">ComplyGH</h1>
            <p className="text-gray-500 dark:text-gray-400 text-sm sm:text-lg">
              Your AI guide to Ghana&apos;s financial regulations
            </p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 w-full max-w-2xl px-2">
            {[
              "What is the minimum capital adequacy ratio for banks?",
              "What are the KYC rules for mobile money agents?",
              "What is the penalty for non-compliance?",
              "Summarize the Cyber Information Security Directive.",
            ].map((q, i) => (
              <motion.button
                key={i}
                type="button"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.08 }}
                onClick={() => setInput(q)}
                className="p-3.5 sm:p-4 bg-card border border-border rounded-xl text-left hover:shadow-md hover:border-accent active:bg-gray-100 dark:active:bg-gray-800/80 transition-all text-xs sm:text-sm text-foreground min-h-[56px] flex items-center"
              >
                {q}
              </motion.button>
            ))}
          </div>

          {error && (
            <div className="w-full max-w-2xl mt-4 px-2">
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs sm:text-sm text-red-600 dark:text-red-400 flex items-center justify-between">
                <span>{error}</span>
                <button
                  type="button"
                  onClick={onRetry}
                  className="ml-3 font-semibold underline hover:no-underline flex-shrink-0"
                >
                  Retry
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        // --- ACTIVE CHAT STATE ---
        <div className="flex-1 overflow-y-auto smooth-scroll p-4 sm:p-6 space-y-5 pb-36 sm:pb-40">
          <div className="max-w-3xl mx-auto space-y-6">
            <AnimatePresence initial={false}>
              {messages.map((msg, idx) => (
                <MessageBubble key={idx} message={msg} />
              ))}

              {isLoading && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex space-x-3 items-start"
                >
                  <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0 mt-1">
                    <ShieldCheck className="w-5 h-5 text-accent animate-pulse" />
                  </div>
                  <div className="bg-card border border-border p-4 rounded-2xl rounded-tl-sm shadow-sm flex items-center space-x-2">
                    <span className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: "300ms" }} />
                    <span className="text-xs text-gray-400 pl-2">Consulting BOG regulations...</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {error && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs sm:text-sm text-red-600 dark:text-red-400 flex items-center justify-between">
                <span>{error}</span>
                <button
                  type="button"
                  onClick={onRetry}
                  className="ml-3 font-semibold underline hover:no-underline flex-shrink-0"
                >
                  Retry
                </button>
              </div>
            )}

            <div ref={messagesEndRef} className="h-4" />
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="p-3 sm:p-4 bg-background border-t border-border/40 pb-safe">
        <div className="max-w-3xl mx-auto relative">
          {/* Advanced Settings Popup */}
          {showSettings && (
            <div className="absolute bottom-full mb-2 right-0 bg-card border border-border rounded-xl shadow-xl p-4 w-72 z-30">
              <h4 className="text-sm font-semibold mb-3 border-b border-border pb-2 text-foreground flex items-center justify-between">
                <span>Search Controls</span>
                <span className="text-[10px] font-mono text-gray-400">RAG</span>
              </h4>
              <div className="space-y-3">
                <label className="flex items-center justify-between cursor-pointer py-1">
                  <span className="text-xs text-foreground/80 font-medium">Query Routing</span>
                  <input
                    type="checkbox"
                    checked={routing}
                    onChange={(e) => setRouting(e.target.checked)}
                    className="w-4 h-4 accent-primary"
                  />
                </label>
                <label className="flex items-center justify-between cursor-pointer py-1">
                  <span className="text-xs text-foreground/80 font-medium">Corrective Retrieval</span>
                  <input
                    type="checkbox"
                    checked={corrective}
                    onChange={(e) => setCorrective(e.target.checked)}
                    className="w-4 h-4 accent-primary"
                  />
                </label>
              </div>
            </div>
          )}

          <form
            onSubmit={handleSubmit}
            className="relative shadow-sm rounded-2xl bg-card border border-border focus-within:border-primary transition-colors flex items-end p-1.5"
          >
            <button
              type="button"
              onClick={() => setShowSettings(!showSettings)}
              className={`p-2.5 rounded-xl transition-colors min-w-[40px] min-h-[40px] flex items-center justify-center ${
                routing || corrective || showSettings
                  ? "text-primary dark:text-accent bg-primary/10"
                  : "text-gray-400 hover:text-primary dark:hover:text-accent"
              }`}
              title="Search Settings (Routing & Corrective RAG)"
              aria-label="Settings"
            >
              <Settings2 className="w-5 h-5" />
            </button>

            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleTextareaInput}
              onKeyDown={handleKeyDown}
              placeholder="Ask about Ghana's financial regulations..."
              className="flex-1 max-h-[150px] bg-transparent resize-none outline-none py-2.5 px-2 text-foreground text-[16px] sm:text-[15px] placeholder-gray-400 leading-relaxed"
              rows={1}
            />

            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="m-1 p-2.5 rounded-xl bg-primary text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-primary-light active:scale-95 transition-all min-w-[40px] min-h-[40px] flex items-center justify-center"
              aria-label="Send"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          <div className="text-center mt-2">
            <span className="text-[10px] text-gray-400 dark:text-gray-500">
              ComplyGH can make mistakes. Informational only, not legal advice. Verify against the official documents.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

const MessageBubble = ({ message }: { message: Message }) => {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex space-x-3 ${isUser ? "justify-end" : "justify-start"} group`}
    >
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0 mt-1 shadow-xs">
          <ShieldCheck className="w-5 h-5 text-accent" />
        </div>
      )}

      <div
        className={`max-w-[85%] ${
          isUser
            ? "bg-gray-100 dark:bg-gray-800 text-foreground rounded-2xl rounded-tr-sm px-5 py-3 text-[14px] sm:text-[15px] break-words"
            : "w-full min-w-0"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        ) : (
          <div className="bg-card border border-border p-4 sm:p-5 rounded-2xl rounded-tl-sm shadow-sm text-foreground prose dark:prose-invert max-w-none text-[14px] sm:text-[15px] break-words overflow-x-auto">
            <ReactMarkdown>{message.content}</ReactMarkdown>

            <div className="mt-4 flex justify-end border-t border-border pt-2 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
              <CopyButton text={message.content} />
            </div>

            {message.sources && message.sources.length > 0 && (
              <div className="mt-4 pt-4 border-t border-border">
                <h4 className="text-xs font-semibold uppercase text-gray-500 mb-3 tracking-wider">Sources Retrieved</h4>
                <div className="space-y-2">
                  {message.sources.map((src, i) => (
                    <SourceCard key={i} source={src} index={i + 1} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
};

const SourceCard = ({ source, index }: { source: Source; index: number }) => {
  const [open, setOpen] = useState(false);
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
  const pdfUrl = `${apiUrl}/pdfs/${encodeURIComponent(source.source_filename)}#page=${source.page_number}`;

  return (
    <div className="border border-border rounded-xl overflow-hidden text-sm bg-gray-50/70 dark:bg-gray-900/40">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors min-h-[44px]"
      >
        <div className="flex items-center space-x-2 overflow-hidden flex-1 mr-2">
          <span className="bg-primary/10 text-primary dark:text-accent font-mono text-xs px-2 py-0.5 rounded font-semibold flex-shrink-0">
            [{index}]
          </span>
          <span className="font-medium truncate text-foreground">{source.source_filename} (Pg {source.page_number})</span>
        </div>
        {open ? <ChevronDown className="w-4 h-4 text-gray-500 flex-shrink-0" /> : <ChevronRight className="w-4 h-4 text-gray-500 flex-shrink-0" />}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-3.5 pb-3.5 pt-1.5 border-t border-border bg-card"
          >
            <div className="flex items-center justify-between mb-1.5">
              <p className="text-xs font-semibold text-gray-500 truncate mr-2">
                {source.section_title !== "Unknown" ? source.section_title : `Page ${source.page_number}`}
              </p>
              <a
                href={pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] text-primary dark:text-accent font-medium hover:underline flex items-center space-x-1 flex-shrink-0 min-h-[30px]"
              >
                <Globe className="w-3 h-3" />
                <span>Open PDF</span>
              </a>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-4 leading-relaxed font-serif italic bg-gray-50 dark:bg-gray-800/40 p-2.5 rounded-lg border border-border/50">
              "{source.text}"
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const CopyButton = ({ text }: { text: string }) => {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      type="button"
      onClick={handleCopy}
      className="flex items-center space-x-1 text-xs text-gray-500 hover:text-primary dark:hover:text-accent transition-colors p-1.5 rounded min-h-[32px]"
    >
      {copied ? <CheckCircle2 className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
      <span>{copied ? "Copied!" : "Copy"}</span>
    </button>
  );
};


