"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  chatAssistantStream,
  getAssistantConversationDetail,
  getAssistantConversations,
} from "@/lib/api";

const DEFAULT_VEHICLE_ID = "00000000-0000-4000-8000-000000000003";

type ChatRole = "user" | "assistant" | "system";

type ChatBubble = {
  id: string;
  role: ChatRole;
  content: string;
  intent?: string;
  route?: string;
  citations?: string[];
  warnings?: string[];
  maintenanceContext?: string;
  memoryMessageCount?: number;
  streaming?: boolean;
};

const WELCOME: ChatBubble = {
  id: "welcome",
  role: "system",
  content:
    "Ask about TPMS warnings, OBD codes, service intervals, or charging. Answers are grounded in the Phase 5 knowledge base and remember prior turns in this conversation.",
};

const SUGGESTIONS = [
  "Why is my tire pressure warning light on?",
  "What does P0420 mean?",
  "When should I replace brake fluid?",
  "How does regenerative braking work?",
];

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Assistant request failed";
}

function bubblesFromStoredMessages(
  messages: Array<{ role?: string; content?: string }>
): ChatBubble[] {
  const bubbles: ChatBubble[] = [];
  messages.forEach((item, index) => {
    const role = String(item.role || "").toLowerCase();
    const content = String(item.content || "").trim();
    if ((role !== "user" && role !== "assistant") || !content) return;
    bubbles.push({
      id: `hist-${index}-${role}`,
      role,
      content,
    });
  });
  return bubbles.length ? bubbles : [WELCOME];
}

export function AssistantChat() {
  const queryClient = useQueryClient();
  const [vehicleId, setVehicleId] = useState(DEFAULT_VEHICLE_ID);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatBubble[]>([WELCOME]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [memoryHint, setMemoryHint] = useState(0);
  const [pending, setPending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const historyQuery = useQuery({
    queryKey: ["assistant-conversations", vehicleId],
    queryFn: () => getAssistantConversations(vehicleId.trim(), 12),
    enabled: Boolean(vehicleId.trim()),
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending]);

  const startNewChat = () => {
    setConversationId(null);
    setMemoryHint(0);
    setError(null);
    setMessages([WELCOME]);
  };

  const loadConversation = async (id: string) => {
    setError(null);
    setLoadingHistory(true);
    try {
      const detail = await getAssistantConversationDetail(id);
      setConversationId(detail.id);
      const bubbles = bubblesFromStoredMessages(detail.messages);
      setMessages(bubbles);
      const priorCount = bubbles.filter(
        (item) => item.role === "user" || item.role === "assistant"
      ).length;
      setMemoryHint(priorCount);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoadingHistory(false);
    }
  };

  const sendMessage = async (raw: string) => {
    const message = raw.trim();
    if (!message || pending) return;

    setError(null);
    setPending(true);
    const userId = `u-${Date.now()}`;
    const assistantId = `a-${Date.now()}`;

    setMessages((prev) => [
      ...prev.filter((item) => item.id !== "welcome"),
      { id: userId, role: "user", content: message },
      {
        id: assistantId,
        role: "assistant",
        content: "",
        streaming: true,
      },
    ]);
    setInput("");

    try {
      await chatAssistantStream(
        {
          message,
          vehicle_id: vehicleId.trim() || undefined,
          conversation_id: conversationId || undefined,
          persist: true,
        },
        {
          onMeta: (meta) => {
            if (meta.conversation_id) setConversationId(meta.conversation_id);
            if (typeof meta.memory_message_count === "number") {
              setMemoryHint(meta.memory_message_count);
            }
            setMessages((prev) =>
              prev.map((item) =>
                item.id === assistantId
                  ? {
                      ...item,
                      intent: meta.intent,
                      route: meta.route,
                      citations: meta.citations,
                      warnings: meta.warnings,
                      maintenanceContext: meta.maintenance_context || undefined,
                      memoryMessageCount: meta.memory_message_count,
                    }
                  : item
              )
            );
          },
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((item) =>
                item.id === assistantId
                  ? { ...item, content: `${item.content}${token.text}` }
                  : item
              )
            );
          },
          onDone: (done) => {
            if (done.conversation_id) setConversationId(done.conversation_id);
            setMessages((prev) =>
              prev.map((item) =>
                item.id === assistantId
                  ? {
                      ...item,
                      content: done.reply || item.content,
                      streaming: false,
                    }
                  : item
              )
            );
          },
        }
      );
      queryClient.invalidateQueries({
        queryKey: ["assistant-conversations", vehicleId],
      });
    } catch (err) {
      setError(errorMessage(err));
      setMessages((prev) =>
        prev.map((item) =>
          item.id === assistantId
            ? {
                ...item,
                content: "Sorry — the assistant could not answer right now.",
                streaming: false,
              }
            : item
        )
      );
    } finally {
      setPending(false);
    }
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    void sendMessage(input);
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[280px_1fr]">
      <aside className="space-y-4">
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Vehicle ID</span>
            <input
              value={vehicleId}
              onChange={(e) => setVehicleId(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs"
            />
          </label>
          <div className="mt-3 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={startNewChat}
              className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800"
            >
              New chat
            </button>
            {memoryHint > 0 ? (
              <p className="text-[11px] text-emerald-300">
                Memory: {memoryHint} msgs
              </p>
            ) : (
              <p className="text-[11px] text-slate-500">No prior turns</p>
            )}
          </div>
          {conversationId ? (
            <p className="mt-3 break-all text-xs text-slate-500">
              Conversation {conversationId}
            </p>
          ) : null}
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-200">History</h2>
            <button
              type="button"
              onClick={() =>
                queryClient.invalidateQueries({
                  queryKey: ["assistant-conversations", vehicleId],
                })
              }
              className="text-xs text-slate-400 hover:text-white"
            >
              Refresh
            </button>
          </div>
          {historyQuery.data?.warning ? (
            <p className="mb-2 text-xs text-amber-300">{historyQuery.data.warning}</p>
          ) : null}
          {loadingHistory ? (
            <p className="mb-2 text-xs text-slate-400">Loading conversation…</p>
          ) : null}
          <div className="max-h-72 space-y-2 overflow-y-auto">
            {(historyQuery.data?.conversations ?? []).length === 0 ? (
              <p className="text-xs text-slate-500">No saved conversations yet.</p>
            ) : (
              historyQuery.data?.conversations.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  disabled={pending || loadingHistory}
                  onClick={() => void loadConversation(item.id)}
                  className={`block w-full rounded-lg border px-3 py-2 text-left text-xs disabled:opacity-50 ${
                    conversationId === item.id
                      ? "border-sky-500/50 bg-sky-500/10 text-sky-100"
                      : "border-slate-800 text-slate-300 hover:bg-slate-800/70"
                  }`}
                >
                  <p className="line-clamp-2">
                    {item.last_user_message || "Empty conversation"}
                  </p>
                  <p className="mt-1 text-[10px] text-slate-500">
                    {item.message_count} msgs
                  </p>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-200">Try asking</h2>
          <div className="flex flex-col gap-2">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                disabled={pending}
                onClick={() => void sendMessage(suggestion)}
                className="rounded-lg border border-slate-700 px-3 py-2 text-left text-xs text-slate-300 hover:bg-slate-800 disabled:opacity-50"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </section>
      </aside>

      <section className="flex min-h-[70vh] flex-col rounded-2xl border border-slate-800 bg-slate-900/60">
        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  message.role === "user"
                    ? "bg-sky-600 text-white"
                    : message.role === "system"
                      ? "border border-slate-700 bg-slate-950 text-slate-400"
                      : "border border-slate-700 bg-slate-950 text-slate-100"
                }`}
              >
                <p className="whitespace-pre-wrap">
                  {message.content || (message.streaming ? "…" : "")}
                </p>
                {message.role === "assistant" && !message.streaming ? (
                  <div className="mt-3 space-y-2 text-xs text-slate-400">
                    {message.intent ? (
                      <p>
                        Intent: {message.intent}
                        {message.route ? ` · ${message.route}` : ""}
                      </p>
                    ) : null}
                    {message.citations?.length ? (
                      <div className="flex flex-wrap gap-1.5">
                        {message.citations.map((citation) => (
                          <span
                            key={citation}
                            className="rounded-full border border-slate-700 px-2 py-0.5 text-[11px] text-sky-200"
                          >
                            {citation}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    {message.memoryMessageCount ? (
                      <p className="text-emerald-300">
                        Used {message.memoryMessageCount} prior message
                        {message.memoryMessageCount === 1 ? "" : "s"}
                      </p>
                    ) : null}
                    {message.maintenanceContext ? (
                      <details className="rounded-lg border border-slate-800 bg-slate-900/80 px-2 py-1">
                        <summary className="cursor-pointer text-violet-300">
                          Maintenance context
                        </summary>
                        <pre className="mt-2 whitespace-pre-wrap text-[11px] text-slate-400">
                          {message.maintenanceContext}
                        </pre>
                      </details>
                    ) : null}
                    {message.warnings?.length ? (
                      <p className="text-amber-300">{message.warnings.join(" · ")}</p>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <form
          onSubmit={onSubmit}
          className="border-t border-slate-800 p-4"
        >
          {error ? (
            <p className="mb-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              {error}
            </p>
          ) : null}
          <div className="flex gap-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your BMW…"
              disabled={pending}
              className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm outline-none ring-sky-500/40 focus:ring"
            />
            <button
              type="submit"
              disabled={pending || !input.trim()}
              className="rounded-xl bg-sky-600 px-5 py-3 text-sm font-semibold text-white hover:bg-sky-500 disabled:opacity-50"
            >
              {pending ? "Thinking…" : "Send"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
