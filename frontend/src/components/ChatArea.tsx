"use client";

import { useState, useRef, useEffect } from "react";
import { Message, Source } from "@/lib/types";
import { Send, Plus, ChevronDown, ChevronRight, Copy, CheckCircle2, MoreHorizontal, FileText, PenLine, Globe, BookOpen, ShieldCheck } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { motion, AnimatePresence } from "framer-motion";

export default function ChatArea({
  messages,
  onSendMessage,
  isLoading,
  error,
  onRetry,
}: {
  messages: Message[];
  onSendMessage: (msg: string, corrective: boolean, routing: boolean) => void;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  const [input, setInput] = useState("");
  // In a real ChatGPT clone, these settings might be buried in a top menu, but we'll keep them simple.
  const [corrective, setCorrective] = useState(false);
  const [routing, setRouting] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const isEmpty = messages.length === 0;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input, corrective, routing);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-background h-screen relative">
      {/* Header Mobile Support */}
      <div className="md:hidden h-14 border-b border-border/50 bg-background/80 backdrop-blur-md flex items-center justify-center sticky top-0 z-10">
        <span className="font-semibold text-foreground tracking-tight">ComplyGH</span>
      </div>

      {isEmpty ? (
        // --- EMPTY STATE ---
        <div className="flex-1 flex flex-col items-center justify-center px-4 -mt-20">
          <h1 className="text-3xl md:text-4xl font-semibold text-foreground mb-8 tracking-tight">
            Research Ghanaian financial regulations.
          </h1>
          
          <div className="w-full max-w-3xl relative">
            <form 
              onSubmit={handleSubmit} 
              className="w-full bg-card shadow-sm border border-border rounded-2xl flex items-center overflow-hidden focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all p-2"
            >
              <div className="pl-3 text-gray-400">
                <Globe className="w-5 h-5" />
              </div>
              
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a question or search for a directive..."
                className="flex-1 bg-transparent outline-none py-3 px-4 text-foreground text-base placeholder-gray-400"
              />
              
              <div className="flex items-center space-x-3 pr-2">
                <label className="hidden sm:flex items-center space-x-1.5 text-xs text-gray-500 cursor-pointer hover:text-foreground transition-colors" title="Filter search to specific regulatory documents">
                  <input type="checkbox" checked={routing} onChange={(e) => setRouting(e.target.checked)} className="accent-primary" />
                  <span>Routing</span>
                </label>
                <label className="hidden sm:flex items-center space-x-1.5 text-xs text-gray-500 cursor-pointer hover:text-foreground transition-colors" title="Self-reflection and query reformulation">
                  <input type="checkbox" checked={corrective} onChange={(e) => setCorrective(e.target.checked)} className="accent-primary" />
                  <span>Corrective RAG</span>
                </label>
                <button
                  type="submit"
                  disabled={!input.trim() || isLoading}
                  className={`p-2 rounded-xl transition-colors ${
                    input.trim() && !isLoading 
                      ? "bg-primary text-white hover:bg-primary-light" 
                      : "bg-gray-100 dark:bg-gray-800 text-gray-400"
                  }`}
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </form>

            <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-3">
              <button onClick={() => setInput("Summarize the Anti-Money Laundering Act")} className="p-4 bg-gray-50 dark:bg-gray-800/30 rounded-xl text-left hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors border border-transparent hover:border-border text-sm text-foreground/80 group">
                <FileText className="w-4 h-4 text-primary/60 mb-2 group-hover:text-primary transition-colors" />
                Summarize the AML Act
              </button>
              <button onClick={() => setInput("What are the KYC rules for mobile money?")} className="p-4 bg-gray-50 dark:bg-gray-800/30 rounded-xl text-left hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors border border-transparent hover:border-border text-sm text-foreground/80 group">
                <ShieldCheck className="w-4 h-4 text-primary/60 mb-2 group-hover:text-primary transition-colors" />
                Mobile Money KYC Rules
              </button>
              <button onClick={() => setInput("What are the penalties for non-compliance?")} className="p-4 bg-gray-50 dark:bg-gray-800/30 rounded-xl text-left hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors border border-transparent hover:border-border text-sm text-foreground/80 group">
                <BookOpen className="w-4 h-4 text-primary/60 mb-2 group-hover:text-primary transition-colors" />
                Penalties for non-compliance
              </button>
            </div>
          </div>
        </div>
      ) : (
        // --- ACTIVE CHAT STATE ---
        <>
          <div className="flex-1 overflow-y-auto scrollbar-none pb-40">
            <div className="max-w-4xl mx-auto px-4 md:px-8 py-6 space-y-6">
              <AnimatePresence initial={false}>
                {messages.map((msg, idx) => (
                  <MessageRow key={idx} message={msg} />
                ))}
                
                {isLoading && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex space-x-5 py-6"
                  >
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <BookOpen className="w-4 h-4 text-primary dark:text-accent" />
                    </div>
                    <div className="flex-1 pt-2 flex space-x-1.5 items-center">
                      <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-pulse" style={{ animationDelay: "0ms" }}></span>
                      <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-pulse" style={{ animationDelay: "200ms" }}></span>
                      <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-pulse" style={{ animationDelay: "400ms" }}></span>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
              <div ref={messagesEndRef} className="h-4" />
            </div>
          </div>

          <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-background via-background to-transparent pt-10 pb-6 px-4">
            <div className="max-w-3xl mx-auto relative">
              <form 
                onSubmit={handleSubmit} 
                className="w-full bg-card shadow-lg shadow-black/5 border border-border rounded-2xl flex items-end overflow-hidden focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all p-2"
              >
                <textarea
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value);
                    e.target.style.height = 'auto';
                    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a follow-up question..."
                  className="flex-1 max-h-[200px] bg-transparent resize-none outline-none py-3 px-4 text-foreground text-base placeholder-gray-400"
                  rows={1}
                />
                
                <div className="flex items-center space-x-3 mb-1 pr-2">
                  <label className="hidden sm:flex items-center space-x-1.5 text-xs text-gray-500 cursor-pointer hover:text-foreground transition-colors" title="Filter search to specific regulatory documents">
                    <input type="checkbox" checked={routing} onChange={(e) => setRouting(e.target.checked)} className="accent-primary" />
                    <span>Routing</span>
                  </label>
                  <label className="hidden sm:flex items-center space-x-1.5 text-xs text-gray-500 cursor-pointer hover:text-foreground transition-colors" title="Self-reflection and query reformulation">
                    <input type="checkbox" checked={corrective} onChange={(e) => setCorrective(e.target.checked)} className="accent-primary" />
                    <span>Corrective RAG</span>
                  </label>
                  <button
                    type="submit"
                    disabled={!input.trim() || isLoading}
                    className={`p-2.5 rounded-xl transition-colors ${
                      input.trim() && !isLoading 
                        ? "bg-primary text-white hover:bg-primary-light" 
                        : "bg-gray-100 dark:bg-gray-800 text-gray-400"
                    }`}
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </form>
              <div className="text-center mt-2">
                <span className="text-[11px] text-gray-400">
                  ComplyGH may provide inaccurate information. Verify against official frameworks.
                </span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

const MessageRow = ({ message }: { message: Message }) => {
  const isUser = message.role === "user";
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full flex justify-center py-2"
    >
      <div className={`w-full max-w-3xl flex ${isUser ? "justify-end" : "justify-start"} group`}>
        {isUser ? (
          <div className="bg-gray-100 dark:bg-gray-800 px-5 py-3 rounded-3xl max-w-[80%] text-[15px] text-foreground">
            {message.content}
          </div>
        ) : (
          <div className="flex space-x-4 w-full">
            <div className="w-8 h-8 rounded-full border border-gray-200 dark:border-gray-700 flex items-center justify-center flex-shrink-0 mt-1 bg-white dark:bg-[#10A37F]">
              <span className="text-gray-500 dark:text-white font-bold text-xs">GH</span>
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="text-foreground prose dark:prose-invert prose-p:leading-relaxed max-w-none text-[15px]">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
              
              <div className="mt-3 flex items-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <CopyButton text={message.content} />
                <button className="p-1.5 text-gray-400 hover:text-foreground hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                  <MoreHorizontal className="w-4 h-4" />
                </button>
              </div>
              
              {message.sources && message.sources.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {message.sources.map((src, i) => (
                    <SourceCard key={i} source={src} index={i+1} />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
};

const SourceCard = ({ source, index }: { source: Source; index: number }) => {
  const [open, setOpen] = useState(false);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const pdfUrl = `${apiUrl}/pdfs/${encodeURIComponent(source.source_filename)}#page=${source.page_number}`;

  return (
    <div className="flex flex-col border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-gray-50 dark:bg-gray-800/50 transition-colors w-full sm:w-[350px]">
      <button 
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between p-2.5 hover:bg-gray-100 dark:hover:bg-gray-800 w-full text-left"
      >
        <div className="flex items-center overflow-hidden pr-2">
          <span className="font-mono text-[10px] text-gray-500 mr-2 flex-shrink-0">[{index}]</span>
          <span className="font-medium text-xs text-foreground/80 truncate">{source.source_filename}</span>
        </div>
        {open ? <ChevronDown className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />}
      </button>
      
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-gray-200 dark:border-gray-700 bg-card"
          >
            <div className="p-3">
              <div className="flex justify-between items-center mb-2">
                <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider truncate mr-2">
                  {source.section_title !== "Unknown" ? source.section_title : `Page ${source.page_number}`}
                </span>
                <a 
                  href={pdfUrl} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-[10px] text-primary hover:underline whitespace-nowrap flex items-center space-x-1"
                >
                  <Globe className="w-3 h-3" />
                  <span>Open PDF</span>
                </a>
              </div>
              <p className="text-[11px] text-foreground/70 leading-relaxed font-serif line-clamp-6">
                "{source.text}"
              </p>
            </div>
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
      onClick={handleCopy}
      className="p-1.5 text-gray-400 hover:text-foreground hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
      title="Copy"
    >
      {copied ? <CheckCircle2 className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
    </button>
  );
};
