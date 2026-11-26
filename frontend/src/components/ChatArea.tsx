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
  PanelLeftOpen,
  Settings2,
  FileText,
  ExternalLink,
  CornerDownLeft,
  Loader2,
  AlertCircle,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { ComplyMark } from "./Sidebar";

const STARTER_QUERIES = [
  "What is the minimum capital adequacy ratio for banks?",
  "What are the KYC rules for mobile money agents?",
  "What is the penalty for non-compliance?",
  "Summarize the Cyber Information Security Directive.",
];

export default function ChatArea({
  messages,
  currentSessionTitle,
  isTemporary,
  isDesktopRailOpen,
  onToggleDesktopRail,
  onSendMessage,
  isLoading,
  isWarmingUp,
  error,
  onRetry,
  onToggleSidebar,
  onNewChat,
}: {
  messages: Message[];
  currentSessionTitle: string | null;
  isTemporary: boolean;
  isDesktopRailOpen: boolean;
  onToggleDesktopRail: () => void;
  onSendMessage: (msg: string, corrective: boolean, routing: boolean) => void;
  isLoading: boolean;
  isWarmingUp: boolean;
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
  const settingsRef = useRef<HTMLDivElement>(null);

  const isEmpty = messages.length === 0;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    if (!showSettings) return;
    const handleOutsideClick = (e: MouseEvent) => {
      if (
        settingsRef.current &&
        !settingsRef.current.contains(e.target as Node)
      ) {
        setShowSettings(false);
      }
    };
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setShowSettings(false);
    };
    document.addEventListener("mousedown", handleOutsideClick);
    window.addEventListener("keydown", handleEsc);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
      window.removeEventListener("keydown", handleEsc);
    };
  }, [showSettings]);

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

  const activeTitle = currentSessionTitle || "New regulatory inquiry";

  return (
    <main className="flex-1 flex flex-col bg-paper h-[100dvh] min-w-0 relative">
      {/* Workspace Top Bar */}
      <header className="min-h-14 border-b border-rule bg-paper-2 flex items-center justify-between gap-2 px-3 sm:px-6 py-2 sticky top-0 z-30 flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <button
            type="button"
            onClick={onToggleSidebar}
            className="min-[60rem]:hidden p-2 -ml-1 text-ink-2 hover:text-ink hover:bg-paper-3 active:translate-y-px rounded-pill transition-[background-color,color,transform] min-w-[44px] min-h-[44px] flex items-center justify-center cursor-pointer flex-shrink-0"
            aria-label="Open sidebar"
          >
            <PanelLeftOpen className="w-5 h-5" />
          </button>

          {!isDesktopRailOpen && (
            <button
              type="button"
              onClick={onToggleDesktopRail}
              className="hidden min-[60rem]:flex p-2 -ml-1 text-ink-2 hover:text-ink hover:bg-paper-3 active:translate-y-px rounded-pill transition-[background-color,color,transform] min-w-[44px] min-h-[44px] items-center justify-center cursor-pointer flex-shrink-0"
              aria-label="Expand sidebar"
              title="Expand sidebar"
            >
              <PanelLeftOpen className="w-4 h-4" />
            </button>
          )}

          <div className="flex items-center gap-2 min-w-0">
            <span className="min-[60rem]:hidden w-6 h-6 rounded-pill bg-brand text-brand-ink flex items-center justify-center flex-shrink-0">
              <ComplyMark className="w-3.5 h-3.5" />
            </span>
            <span className="text-sm font-medium text-ink truncate">
              {activeTitle}
            </span>
            {isTemporary && (
              <span className="text-xs px-2 py-0.5 rounded-pill bg-accent-soft text-accent-text border border-rule font-medium flex-shrink-0">
                Temporary
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1.5 flex-shrink-0">
          {routing && (
            <span className="text-xs px-2 py-1 rounded-pill bg-cool-soft text-cool border border-rule font-medium whitespace-nowrap">
              Routing
            </span>
          )}
          {corrective && (
            <span className="text-xs px-2 py-1 rounded-pill bg-cool-soft text-cool border border-rule font-medium whitespace-nowrap">
              Corrective
            </span>
          )}

          <button
            type="button"
            onClick={onNewChat}
            className="min-[60rem]:hidden p-2 -mr-1 text-ink-2 hover:text-ink hover:bg-paper-3 active:translate-y-px rounded-pill transition-[background-color,color,transform] min-w-[44px] min-h-[44px] flex items-center justify-center cursor-pointer flex-shrink-0"
            aria-label="New chat"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>
      </header>

      {isEmpty ? (
        /* --- EMPTY WORKSPACE: STATUTORY INQUIRY LEDGER --- */
        <div className="flex-1 flex flex-col justify-center px-4 sm:px-6 py-8 overflow-y-auto smooth-scroll">
          <div className="w-full max-w-3xl mx-auto">
            <div className="mb-8 flex items-start gap-4">
              <div className="w-11 h-11 rounded-card bg-brand text-brand-ink flex items-center justify-center flex-shrink-0 mt-0.5">
                <ComplyMark className="w-6 h-6" />
              </div>
              <div className="min-w-0">
                <h1 className="font-display text-2xl sm:text-3xl font-medium tracking-[-0.03em] text-ink mb-1.5">
                  ComplyGH
                </h1>
                <p className="text-ink-2 text-base leading-relaxed">
                  Your AI guide to Ghana&apos;s financial regulations
                </p>
              </div>
            </div>

            <section
              aria-labelledby="suggested-queries-heading"
              className="border border-rule rounded-card bg-paper-2 overflow-hidden divide-y divide-rule"
            >
              <div className="px-4 py-2.5 bg-paper-3 flex items-center justify-between">
                <h2
                  id="suggested-queries-heading"
                  className="text-xs font-medium text-ink-2"
                >
                  Suggested compliance queries
                </h2>
                <span className="measured text-xs text-muted">
                  04 prompts
                </span>
              </div>
              {STARTER_QUERIES.map((q, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setInput(q)}
                  className="group w-full px-4 py-3.5 flex items-center justify-between gap-4 text-left hover:bg-paper-3 active:translate-y-px transition-[background-color,transform] min-h-[52px] cursor-pointer"
                >
                  <div className="flex items-baseline gap-3.5 min-w-0">
                    <span className="measured text-xs font-medium text-cool flex-shrink-0">
                      0{i + 1}
                    </span>
                    <span className="text-sm sm:text-base text-ink leading-snug">
                      {q}
                    </span>
                  </div>
                  <CornerDownLeft className="w-4 h-4 text-muted group-hover:text-accent-text flex-shrink-0 transition-colors" />
                </button>
              ))}
            </section>

            {error && (
              <div className="mt-4 p-3.5 rounded-card bg-bad-soft border border-bad text-sm text-bad flex items-center justify-between gap-3">
                <span className="flex items-center gap-2 min-w-0">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{error}</span>
                </span>
                <button
                  type="button"
                  onClick={onRetry}
                  className="hit-target font-medium underline hover:no-underline active:translate-y-px flex-shrink-0 min-h-[36px] px-2 rounded-pill cursor-pointer transition-transform"
                >
                  Retry
                </button>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* --- ACTIVE WORKSPACE THREAD --- */
        <div className="flex-1 overflow-y-auto smooth-scroll px-4 sm:px-6 py-6">
          <h1 className="visually-hidden">{activeTitle}</h1>
          <div className="max-w-3xl mx-auto space-y-6 pb-8">
            {messages.map((msg, idx) => (
              <MessageBubble key={idx} message={msg} />
            ))}

            {isLoading && (
              <div className="border border-rule rounded-card bg-paper-2 p-4 flex items-start gap-3">
                <Loader2 className="w-4 h-4 text-cool animate-spin motion-reduce:animate-none flex-shrink-0 mt-0.5" />
                <div className="space-y-1 min-w-0">
                  <p className="text-sm font-medium text-ink">
                    {isWarmingUp
                      ? "Waking up server…"
                      : "Consulting BOG regulations…"}
                  </p>
                  {isWarmingUp && (
                    <p className="text-xs text-cool leading-relaxed">
                      Server was asleep, retrying automatically. This takes about
                      30s on first load.
                    </p>
                  )}
                </div>
              </div>
            )}

            {error && (
              <div className="p-3.5 rounded-card bg-bad-soft border border-bad text-sm text-bad flex items-center justify-between gap-3">
                <span className="flex items-center gap-2 min-w-0">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{error}</span>
                </span>
                <button
                  type="button"
                  onClick={onRetry}
                  className="hit-target font-medium underline hover:no-underline active:translate-y-px flex-shrink-0 min-h-[36px] px-2 rounded-pill cursor-pointer transition-transform"
                >
                  Retry
                </button>
              </div>
            )}

            <div ref={messagesEndRef} className="h-2" />
          </div>
        </div>
      )}

      {/* Composer Area */}
      <div className="px-3 sm:px-6 py-3 bg-paper border-t border-rule pb-safe flex-shrink-0">
        <div className="max-w-3xl mx-auto relative" ref={settingsRef}>
          {/* Search Controls Popover */}
          {showSettings && (
            <div
              role="dialog"
              aria-label="Search controls"
              className="absolute bottom-full mb-2 left-0 bg-paper-2 border border-rule-2 rounded-card p-4 w-80 max-w-[calc(100vw-2rem)] z-30"
            >
              <div className="flex items-center justify-between border-b border-rule pb-2.5 mb-3">
                <h2 className="text-sm font-medium text-ink">
                  Search controls
                </h2>
                <span className="text-xs text-muted">Retrieval pipeline</span>
              </div>

              <div className="space-y-3">
                <label className="flex items-start justify-between gap-3 cursor-pointer py-1">
                  <div>
                    <span className="text-sm font-medium text-ink block">
                      Query Routing
                    </span>
                    <span className="text-xs text-muted block">
                      Scope search to matching statutory Acts
                    </span>
                  </div>
                  <input
                    type="checkbox"
                    checked={routing}
                    onChange={(e) => setRouting(e.target.checked)}
                    className="w-4 h-4 mt-0.5 accent-cool cursor-pointer flex-shrink-0"
                  />
                </label>

                <label className="flex items-start justify-between gap-3 cursor-pointer py-1">
                  <div>
                    <span className="text-sm font-medium text-ink block">
                      Corrective Retrieval
                    </span>
                    <span className="text-xs text-muted block">
                      Reformulate and re-query weak context
                    </span>
                  </div>
                  <input
                    type="checkbox"
                    checked={corrective}
                    onChange={(e) => setCorrective(e.target.checked)}
                    className="w-4 h-4 mt-0.5 accent-cool cursor-pointer flex-shrink-0"
                  />
                </label>
              </div>
            </div>
          )}

          <form
            onSubmit={handleSubmit}
            className="relative rounded-card bg-paper-3 border border-muted outline-2 outline-transparent -outline-offset-2 has-[textarea:focus-visible]:outline-focus flex items-end p-1.5 gap-1"
          >
            <button
              type="button"
              onClick={() => setShowSettings(!showSettings)}
              aria-expanded={showSettings}
              aria-label="Search controls"
              title="Search Settings (Routing and Corrective RAG)"
              className={`p-2 rounded-pill transition-[background-color,color,transform] active:translate-y-px min-w-[40px] min-h-[40px] flex items-center justify-center cursor-pointer flex-shrink-0 ${
                routing || corrective || showSettings
                  ? "text-cool bg-cool-soft"
                  : "text-muted hover:text-ink hover:bg-paper-2"
              }`}
            >
              <Settings2 className="w-4 h-4" />
            </button>

            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleTextareaInput}
              onKeyDown={handleKeyDown}
              placeholder="Ask about Ghana's financial regulations…"
              aria-label="Ask about Ghana's financial regulations"
              className="flex-1 max-h-[150px] bg-transparent resize-none outline-none py-2 px-2 text-ink text-base placeholder:text-muted leading-relaxed min-w-0"
              rows={1}
            />

            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              aria-label="Send"
              className="p-2 rounded-pill bg-accent text-accent-ink disabled:opacity-55 disabled:cursor-not-allowed hover:bg-accent-hover active:translate-y-px transition-[background-color,transform] duration-150 min-w-[40px] min-h-[40px] flex items-center justify-center cursor-pointer flex-shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          <p className="text-center mt-2 text-xs text-muted">
            ComplyGH can make mistakes. Informational only, not legal advice.
            Verify against the official documents.
          </p>
        </div>
      </div>
    </main>
  );
}

const MessageBubble = ({ message }: { message: Message }) => {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] bg-paper-3 border border-rule text-ink rounded-card px-4 py-3 text-base break-words">
          <p className="whitespace-pre-wrap leading-relaxed">
            {message.content}
          </p>
        </div>
      </div>
    );
  }

  return (
    <article className="border border-rule rounded-card bg-paper-2 overflow-hidden">
      {/* Dossier Header */}
      <div className="px-4 py-2.5 border-b border-rule flex items-center justify-between gap-3 bg-paper-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="w-6 h-6 rounded-pill bg-brand text-brand-ink flex items-center justify-center flex-shrink-0">
            <ComplyMark className="w-3.5 h-3.5" />
          </span>
          <span className="text-xs font-medium text-ink-2 truncate">
            Regulatory response
          </span>
        </div>
        <CopyButton text={message.content} />
      </div>

      {/* Answer Body */}
      <div className="p-4 sm:p-5 text-ink prose prose-comply max-w-none text-base break-words overflow-x-auto">
        <ReactMarkdown>{message.content}</ReactMarkdown>
      </div>

      {/* Statutory Citations */}
      {message.sources && message.sources.length > 0 && (
        <div className="border-t border-rule bg-paper-3/40">
          <div className="px-4 sm:px-5 py-2.5 flex items-center justify-between border-b border-rule">
            <h2 className="text-xs font-medium text-ink-2">
              Sources retrieved
            </h2>
            <span className="measured text-xs text-muted">
              {String(message.sources.length).padStart(2, "0")} citations
            </span>
          </div>
          <div className="divide-y divide-rule">
            {message.sources.map((src, i) => (
              <SourceCard key={i} source={src} index={i + 1} />
            ))}
          </div>
        </div>
      )}
    </article>
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
  const pdfUrl = `${apiUrl}/pdfs/${encodeURIComponent(
    source.source_filename
  )}#page=${source.page_number}`;

  return (
    <div className="text-sm">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-paper-3 active:translate-y-px transition-[background-color,transform] min-h-[44px] gap-3 cursor-pointer"
      >
        <div className="flex items-center gap-2.5 overflow-hidden flex-1 min-w-0">
          <span className="measured bg-cool-soft text-cool text-xs px-2 py-0.5 rounded font-medium flex-shrink-0">
            [{index}]
          </span>
          <span className="font-medium truncate text-ink">
            {source.source_filename}
          </span>
          <span className="measured text-xs text-muted flex-shrink-0">
            Pg {source.page_number}
          </span>
        </div>
        {open ? (
          <ChevronDown className="w-4 h-4 text-muted flex-shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-muted flex-shrink-0" />
        )}
      </button>

      {open && (
        <div className="px-4 pb-4 pt-3 border-t border-rule bg-paper-3 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium text-ink-2 truncate flex items-center gap-1.5 min-w-0">
              <FileText className="w-3.5 h-3.5 text-muted flex-shrink-0" />
              <span className="truncate">
                {source.section_title !== "Unknown"
                  ? source.section_title
                  : `Page ${source.page_number}`}
              </span>
            </p>
            <a
              href={pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="hit-target text-xs text-cool font-medium hover:underline active:translate-y-px inline-flex items-center gap-1 flex-shrink-0 min-h-[32px] px-1.5 rounded-pill transition-transform"
            >
              <span>Open PDF</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
          <p className="text-xs text-ink-2 leading-relaxed">
            &ldquo;{source.text}&rdquo;
          </p>
        </div>
      )}
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
      className="hit-target inline-flex items-center gap-1.5 text-xs font-medium text-muted hover:text-ink active:translate-y-px transition-[background-color,color,transform] px-2 py-1 rounded-pill hover:bg-paper-3 min-h-[32px] cursor-pointer flex-shrink-0"
    >
      {copied ? (
        <CheckCircle2 className="w-3.5 h-3.5 text-ok" />
      ) : (
        <Copy className="w-3.5 h-3.5" />
      )}
      <span>{copied ? "Copied" : "Copy"}</span>
    </button>
  );
};
