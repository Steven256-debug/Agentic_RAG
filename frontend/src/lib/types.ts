export interface Source {
  source_filename: string;
  page_number: string;
  section_title: string;
  text: string;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  latencySec?: number;
  routedTo?: string[];
  rewrittenQuery?: string;
  reformulatedQuery?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  updatedAt: number;
  isTemporary?: boolean;
}
