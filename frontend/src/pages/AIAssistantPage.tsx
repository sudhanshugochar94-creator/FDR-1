import React, { FormEvent, useEffect, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Bot, Send, Sparkles } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

interface AssistantResponse {
  answer: string;
  source_records: Array<Record<string, unknown>>;
  query_type: string;
  ai_generated: boolean;
}

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  response?: AssistantResponse;
}

interface AIHealth {
  ollama_reachable: boolean;
  model_available: boolean;
  model_name: string;
  message: string;
}

const AIAssistantPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const nextId = useRef(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const health = useQuery({
    queryKey: ['ai-health'],
    queryFn: async () => (await apiClient.get<AIHealth>('/api/ai/health')).data,
    staleTime: 60_000,
  });
  const askMutation = useMutation({
    mutationFn: async (prompt: string) => (await apiClient.post<AssistantResponse>('/api/ai/assistant', { query: prompt })).data,
    onSuccess: (response) => setMessages((current) => [...current, { id: nextId.current++, role: 'assistant', content: response.answer, response }]),
    onError: () => setMessages((current) => [...current, { id: nextId.current++, role: 'assistant', content: 'I could not reach the assistant service. Please try again in a moment.' }]),
  });
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, askMutation.isPending]);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const prompt = query.trim();
    if (prompt.length < 3 || askMutation.isPending) return;
    setMessages((current) => [...current, { id: nextId.current++, role: 'user', content: prompt }]);
    setQuery('');
    askMutation.mutate(prompt);
  };

  return (
    <div className="mx-auto flex min-h-[calc(100vh-10rem)] max-w-5xl flex-col gap-6 pb-8">
      <div><h1 className="text-2xl font-bold tracking-tight">AI compliance assistant</h1><p className="mt-1 text-sm text-muted-foreground">Ask questions about FDR records and compliance workflow activity.</p></div>
      <Card className="flex min-h-[32rem] flex-1 flex-col">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2"><Bot className="h-5 w-5 text-primary" />FDR assistant</CardTitle>
          <CardDescription className="flex flex-wrap items-center gap-2">
            {health.isLoading ? 'Checking assistant availability…' : health.isError ? 'Assistant health is unavailable.' : health.data?.ollama_reachable && health.data?.model_available ? `Connected · ${health.data.model_name}` : `Fallback mode · ${health.data?.message}`}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-4 p-4 sm:p-6">
          <div className="flex-1 space-y-4 overflow-y-auto pr-1" aria-live="polite">
            {messages.length === 0 && <div className="mx-auto mt-10 max-w-md text-center"><Sparkles className="mx-auto mb-3 h-9 w-9 text-indigo-500" /><p className="font-medium">How can I help with your FDR review?</p><p className="mt-2 text-sm text-muted-foreground">For example: “Show me FDRs maturing this month” or “What cases need review?”</p></div>}
            {messages.map((message) => <div key={message.id} className={`max-w-[90%] rounded-lg p-3 sm:max-w-[80%] ${message.role === 'user' ? 'ml-auto bg-primary text-primary-foreground' : 'bg-muted'}`}>
              <p className="whitespace-pre-wrap text-sm">{message.content}</p>
              {message.response && <div className="mt-3 border-t border-border/70 pt-2 text-xs opacity-80"><p>{message.response.ai_generated ? 'AI-generated response' : 'Deterministic assistant response'} · {message.response.query_type.replace(/_/g, ' ')}</p>{message.response.source_records.length > 0 && <details className="mt-1"><summary className="cursor-pointer">Related records ({message.response.source_records.length})</summary><pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words">{JSON.stringify(message.response.source_records, null, 2)}</pre></details>}</div>}
            </div>)}
            {askMutation.isPending && <div className="w-fit rounded-lg bg-muted p-3 text-sm text-muted-foreground">Thinking…</div>}
            <div ref={bottomRef} />
          </div>
          <form onSubmit={submit} className="flex gap-2 border-t pt-4">
            <Input aria-label="Ask the FDR assistant" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ask a question about FDR compliance…" maxLength={500} minLength={3} />
            <Button type="submit" disabled={query.trim().length < 3 || askMutation.isPending} aria-label="Send question"><Send className="h-4 w-4" /></Button>
          </form>
          <p className="text-xs text-muted-foreground">Responses are informational and should not replace the formal verification workflow.</p>
        </CardContent>
      </Card>
    </div>
  );
};

export default AIAssistantPage;
