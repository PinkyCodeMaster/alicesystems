"use client";

import { FormEvent, useEffect, useEffectEvent, useMemo, useState } from "react";
import { Bot, RefreshCcw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  AssistantChatResponse,
  AssistantDependencyStatus,
  AssistantHealthResponse,
  AssistantSessionMessage,
  assistantFetch,
  assistantStreamChat,
  formatDate,
} from "@/lib/alice-client";

export function AssistantConsole({
  assistantBaseUrl,
  onMutation,
}: {
  assistantBaseUrl: string;
  onMutation?: () => Promise<void> | void;
}) {
  const [assistantHealth, setAssistantHealth] = useState<
    "checking" | "reachable" | "unreachable"
  >("checking");
  const [assistantHealthMessage, setAssistantHealthMessage] = useState(
    "Checking assistant health...",
  );
  const [assistantDependencies, setAssistantDependencies] = useState<
    Record<string, AssistantDependencyStatus>
  >({});
  const [assistantInput, setAssistantInput] = useState("");
  const [assistantError, setAssistantError] = useState<string | null>(null);
  const [assistantSessionId, setAssistantSessionId] = useState<string | null>(null);
  const [assistantMessages, setAssistantMessages] = useState<
    AssistantSessionMessage[]
  >([]);
  const [assistantResponse, setAssistantResponse] =
    useState<AssistantChatResponse | null>(null);
  const [assistantSubmitting, setAssistantSubmitting] = useState(false);
  const [assistantRefreshing, setAssistantRefreshing] = useState(false);
  const [streamingReply, setStreamingReply] = useState("");
  const [streamingUserMessage, setStreamingUserMessage] = useState<string | null>(null);
  const [streamingToolTraces, setStreamingToolTraces] = useState<
    AssistantChatResponse["tool_traces"]
  >([]);

  const loadAssistantMessages = async () => {
    if (!assistantSessionId) {
      setAssistantMessages([]);
      return;
    }

    setAssistantRefreshing(true);
    try {
      const response = await assistantFetch<{ items: AssistantSessionMessage[] }>(
        assistantBaseUrl,
        `/sessions/${assistantSessionId}/messages`,
      );
      setAssistantMessages(response.items);
      setAssistantError(null);
    } catch (error) {
      setAssistantError(
        error instanceof Error ? error.message : "Failed to load assistant session",
      );
    } finally {
      setAssistantRefreshing(false);
    }
  };
  const refreshAssistantMessages = useEffectEvent(() => void loadAssistantMessages());

  useEffect(() => {
    let cancelled = false;

    const loadHealth = async () => {
      try {
        const body = await assistantFetch<AssistantHealthResponse>(
          assistantBaseUrl,
          "/health",
        );
        if (cancelled) return;
        setAssistantHealth("reachable");
        setAssistantHealthMessage(
          `${body.service} is ${body.status} (${body.environment})`,
        );
        setAssistantDependencies(body.dependencies);
      } catch (error) {
        if (cancelled) return;
        setAssistantHealth("unreachable");
        setAssistantHealthMessage(
          error instanceof Error ? error.message : "Assistant health check failed",
        );
        setAssistantDependencies({});
      }
    };

    void loadHealth();
    const interval = window.setInterval(() => void loadHealth(), 10000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [assistantBaseUrl]);

  useEffect(() => {
    if (!assistantSessionId) {
      return;
    }

    const timeout = window.setTimeout(() => void refreshAssistantMessages(), 0);
    const interval = window.setInterval(() => void refreshAssistantMessages(), 3000);
    return () => {
      window.clearTimeout(timeout);
      window.clearInterval(interval);
    };
  }, [assistantSessionId, assistantBaseUrl]);

  const submitAssistantPrompt = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = assistantInput.trim();
    if (!message) {
      return;
    }

    setAssistantSubmitting(true);
    try {
      setStreamingReply("");
      setStreamingUserMessage(message);
      setStreamingToolTraces([]);
      setAssistantInput("");
      setAssistantError(null);

      await assistantStreamChat(
        assistantBaseUrl,
        {
          message,
          session_id: assistantSessionId,
        },
        {
          onStart: ({ session_id }) => {
            setAssistantSessionId(session_id);
          },
          onTool: (trace) => {
            setStreamingToolTraces((current) => [...current, trace]);
          },
          onDelta: ({ content }) => {
            setStreamingReply((current) => current + content);
          },
          onDone: (response) => {
            setAssistantResponse(response);
          },
          onError: ({ detail }) => {
            throw new Error(detail);
          },
        },
      );

      await loadAssistantMessages();
      setStreamingReply("");
      setStreamingUserMessage(null);
      setStreamingToolTraces([]);
      if (onMutation) {
        await onMutation();
      }
    } catch (error) {
      setAssistantError(
        error instanceof Error ? error.message : "Assistant request failed",
      );
      setStreamingReply("");
      setStreamingUserMessage(null);
      setStreamingToolTraces([]);
    } finally {
      setAssistantSubmitting(false);
    }
  };

  const lastAssistantMessage = useMemo(
    () =>
      [...assistantMessages]
        .reverse()
        .find((message) => message.role === "assistant") ?? null,
    [assistantMessages],
  );

  const examples = [
    "show me the bench light details",
    "what happened recently",
    "is auto-light enabled",
    "set auto-light on raw to 3200",
    "set auto-light sensor to hall sensor illuminance",
  ];

  return (
    <div className="space-y-6">
      {assistantError ? (
        <Card className="rounded-3xl border-destructive/40">
          <CardContent className="p-4 text-sm text-destructive">
            {assistantError}
          </CardContent>
        </Card>
      ) : null}

      <Card className="rounded-3xl">
        <CardHeader>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-4 w-4" />
                Assistant console
              </CardTitle>
              <CardDescription>
                Live session memory, tool traces, and assistant health.
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant={
                  assistantHealth === "reachable"
                    ? "default"
                    : assistantHealth === "checking"
                      ? "secondary"
                      : "destructive"
                }
              >
                assistant {assistantHealth}
              </Badge>
              <Badge variant="outline">
                {assistantSessionId ? `session ${assistantSessionId}` : "new session"}
              </Badge>
              <Button
                variant="outline"
                size="sm"
                type="button"
                onClick={() => void loadAssistantMessages()}
                disabled={!assistantSessionId || assistantRefreshing || assistantSubmitting}
              >
                <RefreshCcw className="mr-2 h-4 w-4" />
                {assistantRefreshing ? "Refreshing..." : "Refresh"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                type="button"
                onClick={() => {
                  setAssistantSessionId(null);
                  setAssistantMessages([]);
                  setAssistantResponse(null);
                  setAssistantError(null);
                  setStreamingReply("");
                  setStreamingUserMessage(null);
                  setStreamingToolTraces([]);
                }}
                disabled={assistantSubmitting}
              >
                New session
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.9fr)]">
          <div className="space-y-4">
            <form className="space-y-3" onSubmit={submitAssistantPrompt}>
              <Label htmlFor="assistant-prompt">Prompt</Label>
              <Textarea
                id="assistant-prompt"
                value={assistantInput}
                onChange={(event) => setAssistantInput(event.target.value)}
                placeholder="Ask Alice about device state, audit history, or automation settings."
                className="min-h-27.5"
              />
              <div className="flex flex-wrap gap-2">
                {examples.map((example) => (
                  <Button
                    key={example}
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setAssistantInput(example)}
                  >
                    {example}
                  </Button>
                ))}
              </div>
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="text-xs text-muted-foreground">
                  Assistant target: {assistantBaseUrl}
                </div>
                <Button disabled={assistantSubmitting} type="submit">
                  {assistantSubmitting ? "Streaming..." : "Send to assistant"}
                </Button>
              </div>
            </form>

            <div className="space-y-3 rounded-2xl border p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">Session thread</div>
                  <div className="text-xs text-muted-foreground">
                    Real-time assistant memory from the current session.
                  </div>
                </div>
                <div className="text-xs text-muted-foreground">
                  {assistantMessages.length} messages
                </div>
              </div>

              <div className="max-h-105 space-y-3 overflow-y-auto pr-1">
                {assistantMessages.length === 0 && !streamingUserMessage ? (
                  <div className="rounded-2xl border border-dashed p-4 text-sm text-muted-foreground">
                    Start a session from the browser to watch the assistant
                    memory change in real time.
                  </div>
                ) : (
                  <>
                    {assistantMessages.map((message) => (
                      <div
                        key={`${message.session_id}-${message.id}`}
                        className={
                          message.role === "assistant"
                            ? "rounded-2xl border bg-muted/30 p-4"
                            : "rounded-2xl border p-4"
                        }
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2">
                            <Badge
                              variant={
                                message.role === "assistant" ? "default" : "outline"
                              }
                            >
                              {message.role}
                            </Badge>
                            {message.mode ? (
                              <Badge variant="secondary">{message.mode}</Badge>
                            ) : null}
                            {typeof message.success === "boolean" ? (
                              <Badge
                                variant={message.success ? "default" : "destructive"}
                              >
                                {message.success ? "ok" : "failed"}
                              </Badge>
                            ) : null}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {formatDate(message.created_at)}
                          </div>
                        </div>
                        <p className="mt-3 whitespace-pre-wrap text-sm">
                          {message.content}
                        </p>
                      </div>
                    ))}

                    {streamingUserMessage ? (
                      <div className="rounded-2xl border p-4">
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline">user</Badge>
                            <Badge variant="secondary">draft</Badge>
                          </div>
                          <div className="text-xs text-muted-foreground">now</div>
                        </div>
                        <p className="mt-3 whitespace-pre-wrap text-sm">
                          {streamingUserMessage}
                        </p>
                      </div>
                    ) : null}

                    {assistantSubmitting ? (
                      <div className="rounded-2xl border bg-muted/30 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2">
                            <Badge>assistant</Badge>
                            <Badge variant="secondary">streaming</Badge>
                          </div>
                          <div className="text-xs text-muted-foreground">now</div>
                        </div>
                        <p className="mt-3 whitespace-pre-wrap text-sm">
                          {streamingReply || "Thinking..."}
                        </p>
                      </div>
                    ) : null}
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-2xl border p-4">
              <div className="text-sm font-medium">Assistant health</div>
              <div className="mt-2 text-sm text-muted-foreground">
                {assistantHealthMessage}
              </div>
              <div className="mt-3 space-y-2">
                {Object.entries(assistantDependencies).map(([name, dependency]) => (
                  <div
                    key={name}
                    className="rounded-xl border px-3 py-2 text-xs text-muted-foreground"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium text-foreground">{name}</span>
                      <Badge variant={dependency.reachable ? "default" : "outline"}>
                        {dependency.reachable ? "reachable" : "unreachable"}
                      </Badge>
                    </div>
                    <div className="mt-2">{dependency.detail}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border p-4">
              <div className="text-sm font-medium">Latest assistant debug</div>
              {assistantSubmitting || assistantResponse || lastAssistantMessage ? (
                <div className="mt-3 space-y-3 text-xs text-muted-foreground">
                  {assistantSubmitting ? (
                    <>
                      <div>stream: active</div>
                      <div>preview chars: {streamingReply.length}</div>
                      <div className="space-y-2">
                        {streamingToolTraces.map((trace, index) => (
                          <div
                            key={`${trace.tool}-${index}`}
                            className="rounded-xl border px-3 py-2"
                          >
                            <div className="font-medium text-foreground">
                              {trace.tool} [{trace.status}]
                            </div>
                            <div className="mt-1">{trace.detail}</div>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : null}
                  {assistantResponse ? (
                    <>
                      <div>response mode: {assistantResponse.mode}</div>
                      <div>planner: {assistantResponse.debug.planner_source}</div>
                      <div>
                        fallback: {assistantResponse.debug.fallback_used ? "true" : "false"}
                      </div>
                      {assistantResponse.debug.planner_error ? (
                        <div>planner error: {assistantResponse.debug.planner_error}</div>
                      ) : null}
                      <div className="space-y-2">
                        {assistantResponse.tool_traces.map((trace, index) => (
                          <div
                            key={`${trace.tool}-${index}`}
                            className="rounded-xl border px-3 py-2"
                          >
                            <div className="font-medium text-foreground">
                              {trace.tool} [{trace.status}]
                            </div>
                            <div className="mt-1">{trace.detail}</div>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div>
                      Session has persisted messages, but no response debug is
                      loaded yet in this browser tab.
                    </div>
                  )}
                </div>
              ) : (
                <div className="mt-3 text-xs text-muted-foreground">
                  No assistant response yet.
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
