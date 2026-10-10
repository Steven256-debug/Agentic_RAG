"use client";

import { useState, useRef, useEffect } from "react";
import { Message, Source } from "@/lib/types";
import { Send, Settings2, Copy, CheckCircle2, ChevronDown, ChevronRight, ShieldCheck, RefreshCw } from "lucide-react";
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
  const [corrective, setCorrective] = useState(false);
  const [routing, setRouting] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
    <div className="flex-1 flex flex-col bg-background h-screen overflow-hidden">
      {/* Header Mobile Support */}
      <div className="md:hidden h-14 border-b border-border bg-card flex items-center justify-center">
        <span className="font-bold text-primary dark:text-accent">ComplyGH</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 scrollbar-thin">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 ? (
            <EmptyState setInput={setInput} />
          ) : (
            <AnimatePresence>
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
                    <ShieldCheck className="w-5 h-5 text-accent" />
                  </div>
                  <div className="bg-card border border-border p-4 rounded-2xl rounded-tl-sm flex space-x-2">
                    <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: "0ms" }}></span>
                    <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: "150ms" }}></span>
                    <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: "300ms" }}></span>
                  </div>
                </motion.div>
              )}
              {error && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl border border-red-200 dark:border-red-800 text-center">
                  <p className="mb-2">{error}</p>
                  <button onClick={onRetry} className="flex items-center space-x-2 mx-auto bg-red-100 dark:bg-red-800 px-4 py-2 rounded-lg hover:opacity-80 transition-opacity">
                    <RefreshCw className="w-4 h-4" /> <span>Retry</span>
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="p-4 bg-background">
        <div className="max-w-3xl mx-auto relative">
          {showSettings && (
            <div className="absolute bottom-full mb-2 right-0 bg-card border border-border rounded-xl shadow-lg p-4 w-64 z-10">
              <h4 className="text-sm font-semibold mb-3 border-b border-border pb-2 text-foreground">Advanced Settings</h4>
              <div className="space-y-3">
                <label className="flex items-center justify-between cursor-pointer">
                  <span className="text-sm text-gray-600 dark:text-gray-300">Corrective Retrieval</span>
                  <input type="checkbox" checked={corrective} onChange={(e) => setCorrective(e.target.checked)} className="w-4 h-4 accent-primary" />
                </label>
                <label className="flex items-center justify-between cursor-pointer">
                  <span className="text-sm text-gray-600 dark:text-gray-300">Query Routing</span>
                  <input type="checkbox" checked={routing} onChange={(e) => setRouting(e.target.checked)} className="w-4 h-4 accent-primary" />
                </label>
              </div>
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="relative shadow-sm rounded-2xl bg-card border border-border focus-within:border-primary transition-colors flex items-end">
            <button
              type="button"
              onClick={() => setShowSettings(!showSettings)}
              className="p-3 text-gray-400 hover:text-primary transition-colors"
              title="Settings"
            >
              <Settings2 className="w-5 h-5" />
            </button>
            
            <textarea
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
              }}
              onKeyDown={handleKeyDown}
              placeholder="Ask about Ghana&apos;s financial regulations..."
              className="flex-1 max-h-[150px] bg-transparent resize-none outline-none py-3 px-2 text-foreground placeholder-gray-400"
              rows={1}
            />
            
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="m-2 p-2 rounded-xl bg-primary text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary-light transition-colors"
            >
              <Send className="w-5 h-5" />
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

const EmptyState = ({ setInput }: { setInput: (s: string) => void }) => (
  <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-8 flex flex-col items-center"
    >
      <ShieldCheck className="w-20 h-20 text-primary dark:text-accent mb-4" />
      <h2 className="text-3xl font-bold text-primary dark:text-gray-100 mb-2">ComplyGH</h2>
      <p className="text-gray-500 dark:text-gray-400 text-lg">Your AI guide to Ghana&apos;s financial regulations</p>
    </motion.div>
    
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-2xl">
      {[
        "What is the minimum capital adequacy ratio for banks?",
        "What are the KYC rules for mobile money agents?",
        "What is the penalty for non-compliance?",
        "Summarize the Cyber Information Security Directive."
      ].map((q, i) => (
        <motion.button
          key={i}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: i * 0.1 }}
          onClick={() => setInput(q)}
          className="p-4 bg-card border border-border rounded-xl text-left hover:shadow-md hover:border-accent transition-all text-sm text-foreground"
        >
          {q}
        </motion.button>
      ))}
    </div>
  </div>
);

const MessageBubble = ({ message }: { message: Message }) => {
  const isUser = message.role === "user";
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex space-x-3 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0 mt-1">
          <ShieldCheck className="w-5 h-5 text-accent" />
        </div>
      )}
      
      <div className={`max-w-[85%] ${isUser ? "bg-gray-100 dark:bg-gray-800 text-foreground rounded-2xl rounded-tr-sm px-5 py-3" : "w-full"}`}>
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="bg-card border border-border p-5 rounded-2xl rounded-tl-sm shadow-sm text-foreground prose dark:prose-invert max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
            
            <div className="mt-4 flex justify-end border-t border-border pt-2">
               <CopyButton text={message.content} />
            </div>
            
            {message.sources && message.sources.length > 0 && (
              <div className="mt-4 pt-4 border-t border-border">
                <h4 className="text-xs font-semibold uppercase text-gray-500 mb-3">Sources Retrieved</h4>
                <div className="space-y-2">
                  {message.sources.map((src, i) => (
                    <SourceCard key={i} source={src} index={i+1} />
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
  return (
    <div className="border border-border rounded-lg overflow-hidden text-sm bg-gray-50 dark:bg-gray-900/50">
      <button 
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
      >
        <div className="flex items-center space-x-2 overflow-hidden">
          <span className="bg-primary/10 text-primary dark:text-accent font-mono text-xs px-2 py-0.5 rounded">[{index}]</span>
          <span className="font-medium truncate">{source.source_filename} (Pg {source.page_number})</span>
        </div>
        {open ? <ChevronDown className="w-4 h-4 text-gray-500" /> : <ChevronRight className="w-4 h-4 text-gray-500" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-3 pb-3 pt-1 border-t border-border"
          >
            <p className="text-xs font-semibold text-gray-500 mb-1">{source.section_title}</p>
            <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-4">{source.text}</p>
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
      className="flex items-center space-x-1 text-xs text-gray-500 hover:text-primary transition-colors"
    >
      {copied ? <CheckCircle2 className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
      <span>{copied ? "Copied!" : "Copy"}</span>
    </button>
  );
};
