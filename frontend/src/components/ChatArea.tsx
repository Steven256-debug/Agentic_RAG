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
  AlertCircle,
  ArrowDown,
  GitBranch,
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
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const settingsRef = useRef<HTMLDivElement>(null);

  const isEmpty = messages.length === 0;
  const hasHistory = messages.length > 1;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 150)}px`;
    if (
      input &&
      STARTER_QUERIES.includes(input) &&
      document.activeElement !== el
    ) {
      el.focus();
      const len = el.value.length;
      el.setSelectionRange(len, len);
    }
  }, [input]);

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

  const handleThreadScroll = () => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowScrollBottom(distanceFromBottom > 180);
  };

  const scrollToLatest = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

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
        /* --- EMPTY STATE: CLASSIC STARTER QUERY CARDS --- */
        <div className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 py-8 overflow-y-auto smooth-scroll">
          <div className="w-full max-w-2xl mx-auto text-center">
            <div className="mb-8 flex flex-col items-center">
              <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-card bg-brand text-brand-ink flex items-center justify-center mb-4">
                <ComplyMark className="w-8 h-8 sm:w-9 sm:h-9" />
              </div>
              <h1 className="font-display text-3xl sm:text-4xl font-medium tracking-[-0.03em] text-ink mb-2">
                ComplyGH
              </h1>
              <p className="text-ink-2 text-base sm:text-lg max-w-md leading-relaxed">
                Your AI guide to Ghana&apos;s financial regulations
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
              {STARTER_QUERIES.map((q, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setInput(q)}
                  className="p-4 bg-paper-2 border border-rule rounded-card text-left hover:bg-paper-3 hover:border-accent active:translate-y-px transition-[background-color,border-color,transform] duration-150 text-sm text-ink leading-snug min-h-[60px] flex items-center cursor-pointer"
                >
                  {q}
                </button>
              ))}
            </div>

            {error && (
              <div className="mt-4 p-3.5 rounded-card bg-bad-soft border border-bad text-sm text-bad flex items-center justify-between gap-3 text-left">
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
        <div
          ref={scrollContainerRef}
          onScroll={handleThreadScroll}
          className="flex-1 overflow-y-auto smooth-scroll px-4 sm:px-6 py-6 relative"
        >
          <h1 className="visually-hidden">{activeTitle}</h1>
          <div className="max-w-3xl mx-auto space-y-6 pb-8">
            {messages.map((msg, idx) => (
              <MessageBubble key={idx} message={msg} />
            ))}

            {isLoading && (
              <ThinkingIndicator
                isWarmingUp={isWarmingUp}
                routing={routing}
                corrective={corrective}
                hasHistory={hasHistory}
              />
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

          {showScrollBottom && (
            <div className="sticky bottom-3 flex justify-center pointer-events-none">
              <button
                type="button"
                onClick={scrollToLatest}
                aria-label="Scroll to latest message"
                className="pointer-events-auto inline-flex items-center gap-1.5 px-3 py-1.5 rounded-pill bg-paper-2 border border-rule-2 text-xs font-medium text-ink-2 hover:text-ink hover:bg-paper-3 active:translate-y-px transition-[background-color,color,transform] cursor-pointer min-h-[36px]"
              >
                <ArrowDown className="w-3.5 h-3.5" />
                <span>Latest</span>
              </button>
            </div>
          )}
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

/* ------------------------------------------------------------------ */
/*  Thinking Indicator — ChatGPT cadence + Claude staged reasoning    */
/* ------------------------------------------------------------------ */

const ThinkingIndicator = ({
  isWarmingUp,
  routing,
  corrective,
  hasHistory,
}: {
  isWarmingUp: boolean;
  routing: boolean;
  corrective: boolean;
  hasHistory: boolean;
}) => {
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const timer = window.setInterval(() => {
      setElapsedMs(Date.now() - start);
    }, 100);
    return () => window.clearInterval(timer);
  }, []);

  const stages = [
    {
      label: hasHistory
        ? "Rewriting follow-up with thread context"
        : "Parsing inquiry & statutory scope",
      detail: "Normalizing regulatory terms and section references",
    },
    {
      label: routing
        ? "Routing across Bank of Ghana Acts"
        : "Searching indexed Ghana statutes & directives",
      detail: "Hybrid semantic and lexical section retrieval",
    },
    {
      label: corrective
        ? "Verifying & refining retrieved context"
        : "Cross-referencing clauses & drafting answer",
      detail: "Grounding claims against retrieved page excerpts",
    },
  ];

  const activeStage = elapsedMs >= 4200 ? 2 : elapsedMs >= 1600 ? 1 : 0;
  const elapsedFormatted = `${(elapsedMs / 1000).toFixed(1)}s`;

  return (
    <div
      role="status"
      aria-live="polite"
      className="border border-rule rounded-card bg-paper-2 overflow-hidden"
    >
      {/* Top scanning beam */}
      <div className="h-[2px] w-full overflow-hidden bg-rule">
        <div
          className={`thinking-beam motion-reduce:animate-none h-full w-1/3 ${
            isWarmingUp ? "bg-accent" : "bg-cool"
          }`}
        />
      </div>

      {/* Reasoning Header */}
      <div className="px-4 py-3 border-b border-rule flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          {/* Concentric breathing ComplyMark */}
          <div className="relative flex-shrink-0">
            <span
              aria-hidden="true"
              className={`thinking-ring motion-reduce:animate-none absolute inset-0 rounded-pill border ${
                isWarmingUp ? "border-accent" : "border-cool"
              }`}
            />
            <div className="thinking-breath motion-reduce:animate-none relative w-7 h-7 rounded-pill bg-brand text-brand-ink flex items-center justify-center">
              <ComplyMark className="w-4 h-4" />
            </div>
          </div>

          <div className="flex items-center gap-2.5 min-w-0">
            <span className="text-sm font-medium text-ink truncate">
              {isWarmingUp
                ? "Waking up ComplyGH server"
                : "Consulting BoG regulations"}
            </span>

            {/* 4-bar harmonic cadence indicator */}
            <span
              aria-hidden="true"
              className="inline-flex items-center gap-[3px] h-3.5 flex-shrink-0"
            >
              <span className="thinking-wave-bar motion-reduce:animate-none w-[2px] h-full rounded-full bg-cool" />
              <span className="thinking-wave-bar motion-reduce:animate-none w-[2px] h-full rounded-full bg-cool" />
              <span className="thinking-wave-bar motion-reduce:animate-none w-[2px] h-full rounded-full bg-cool" />
              <span className="thinking-wave-bar motion-reduce:animate-none w-[2px] h-full rounded-full bg-cool" />
            </span>
          </div>
        </div>

        <span className="measured text-xs text-cool flex-shrink-0">
          {elapsedFormatted}
        </span>
      </div>

      {/* Stage Trace Body */}
      <div className="p-4">
        {isWarmingUp ? (
          <div className="border-l-2 border-accent pl-3.5 py-0.5 space-y-1">
            <p className="text-sm font-medium text-accent-text">
              Cold start detected, retrying automatically
            </p>
            <p className="text-xs text-muted leading-relaxed">
              The server instance slept during inactivity. Initial wake-up takes
              around 30s before statutory retrieval begins.
            </p>
          </div>
        ) : (
          <ol className="border-l border-rule-2 ml-2 pl-4 space-y-2.5">
            {stages.map((stage, idx) => {
              const isDone = idx < activeStage;
              const isCurrent = idx === activeStage;
              return (
                <li
                  key={stage.label}
                  className={`relative rounded-pill transition-colors duration-200 ${
                    isCurrent ? "bg-paper-3 px-3 py-2 overflow-hidden" : "px-1 py-0.5"
                  }`}
                >
                  {isCurrent && (
                    <span
                      aria-hidden="true"
                      className="thinking-row-sheen motion-reduce:animate-none pointer-events-none absolute inset-y-0 left-0 w-1/2 bg-cool/10"
                    />
                  )}
                  <div className="relative flex items-start gap-2.5">
                    {isDone ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-ok flex-shrink-0 mt-0.5" />
                    ) : isCurrent ? (
                      <span
                        aria-hidden="true"
                        className="thinking-step-pulse motion-reduce:animate-none w-3.5 h-3.5 rounded-full border-2 border-cool flex-shrink-0 mt-0.5"
                      />
                    ) : (
                      <span
                        aria-hidden="true"
                        className="w-3.5 h-3.5 rounded-full border border-rule-2 flex-shrink-0 mt-0.5"
                      />
                    )}
                    <div className="min-w-0">
                      <p
                        className={`text-xs font-medium leading-snug ${
                          isDone
                            ? "text-ink-2"
                            : isCurrent
                            ? "text-ink"
                            : "text-muted"
                        }`}
                      >
                        {stage.label}
                      </p>
                      {isCurrent && (
                        <p className="text-xs text-muted mt-0.5 leading-snug">
                          {stage.detail}
                        </p>
                      )}
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Message Bubble & Dossier Citations                                */
/* ------------------------------------------------------------------ */

const MessageBubble = ({ message }: { message: Message }) => {
  const isUser = message.role === "user";
  const [traceOpen, setTraceOpen] = useState(false);

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

  const hasTrace = Boolean(
    message.routedTo?.length ||
      message.rewrittenQuery ||
      message.reformulatedQuery
  );

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

        <div className="flex items-center gap-2 flex-shrink-0">
          {typeof message.latencySec === "number" && (
            <span
              className="measured text-xs text-muted"
              title="Response time"
            >
              {message.latencySec.toFixed(1)}s
            </span>
          )}
          <CopyButton text={message.content} />
        </div>
      </div>

      {/* Answer Body */}
      <div className="p-4 sm:p-5 text-ink prose prose-comply max-w-none text-base break-words overflow-x-auto">
        <ReactMarkdown>{message.content}</ReactMarkdown>
      </div>

      {/* Optional Retrieval Trace (only when backend returned trace metadata) */}
      {hasTrace && (
        <div className="border-t border-rule bg-paper-3/30">
          <button
            type="button"
            onClick={() => setTraceOpen(!traceOpen)}
            aria-expanded={traceOpen}
            className="w-full px-4 sm:px-5 py-2 flex items-center justify-between gap-2 text-xs text-muted hover:text-ink hover:bg-paper-3 transition-colors min-h-[38px] cursor-pointer"
          >
            <span className="inline-flex items-center gap-1.5 font-medium">
              <GitBranch className="w-3.5 h-3.5 text-cool" />
              <span>Retrieval trace</span>
            </span>
            {traceOpen ? (
              <ChevronDown className="w-3.5 h-3.5 flex-shrink-0" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 flex-shrink-0" />
            )}
          </button>

          {traceOpen && (
            <div className="px-4 sm:px-5 pb-3 pt-1 space-y-1.5 text-xs border-t border-rule bg-paper-3/50">
              {message.rewrittenQuery && (
                <p className="text-ink-2">
                  <span className="text-muted font-medium">Rewritten query: </span>
                  {message.rewrittenQuery}
                </p>
              )}
              {message.reformulatedQuery && (
                <p className="text-ink-2">
                  <span className="text-muted font-medium">Corrective query: </span>
                  {message.reformulatedQuery}
                </p>
              )}
              {message.routedTo && message.routedTo.length > 0 && (
                <p className="text-ink-2">
                  <span className="text-muted font-medium">Routed statutes: </span>
                  {message.routedTo.join(", ")}
                </p>
              )}
            </div>
          )}
        </div>
      )}

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
