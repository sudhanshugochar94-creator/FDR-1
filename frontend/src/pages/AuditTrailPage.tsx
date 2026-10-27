import React, { FormEvent, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { History, RefreshCw, Search } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface AuditEvent {
  id: string;
  user_id?: string | null;
  role?: string | null;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  timestamp: string;
  before_values?: Record<string, unknown> | null;
  after_values?: Record<string, unknown> | null;
  reason?: string | null;
}

const AuditTrailPage: React.FC = () => {
  const [draftAction, setDraftAction] = useState('');
  const [draftEntity, setDraftEntity] = useState('');
  const [filters, setFilters] = useState({ action: '', entity_type: '' });
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['audit-events', filters],
    queryFn: async () => (await apiClient.get<AuditEvent[]>('/api/audit', {
      params: {
        limit: 100,
        ...(filters.action ? { action: filters.action } : {}),
        ...(filters.entity_type ? { entity_type: filters.entity_type } : {}),
      },
    })).data,
  });
  const submitFilters = (event: FormEvent) => {
    event.preventDefault();
    setFilters({ action: draftAction.trim(), entity_type: draftEntity.trim() });
  };

  return (
    <div className="space-y-6 pb-10">
      <div><h1 className="text-2xl font-bold tracking-tight">System audit trail</h1><p className="mt-1 text-sm text-muted-foreground">Recent recorded actions with optional action and entity filters.</p></div>
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><History className="h-5 w-5 text-primary" />Audit events</CardTitle><CardDescription>Showing up to 100 events, newest first.</CardDescription></CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={submitFilters} className="flex flex-col gap-2 sm:flex-row">
            <Input placeholder="Filter action (e.g. FDR_UPDATED)" value={draftAction} onChange={(event) => setDraftAction(event.target.value)} />
            <Input placeholder="Filter entity type (e.g. FDRInstrument)" value={draftEntity} onChange={(event) => setDraftEntity(event.target.value)} />
            <Button type="submit"><Search className="mr-2 h-4 w-4" />Filter</Button>
            <Button type="button" variant="outline" onClick={() => { setDraftAction(''); setDraftEntity(''); setFilters({ action: '', entity_type: '' }); refetch(); }} aria-label="Refresh audit events"><RefreshCw className="h-4 w-4" /></Button>
          </form>
          {isLoading ? <p className="py-8 text-center text-sm text-muted-foreground">Loading audit events…</p> : isError ? <div className="flex flex-col items-center gap-3 py-8"><p className="text-sm text-destructive">Unable to load the audit trail.</p><Button variant="outline" onClick={() => refetch()}>Retry</Button></div> : data?.length ? <Table><TableHeader><TableRow><TableHead>Timestamp</TableHead><TableHead>Action</TableHead><TableHead>Entity</TableHead><TableHead>Actor</TableHead><TableHead>Details</TableHead></TableRow></TableHeader><TableBody>{data.map((event) => <TableRow key={event.id} className="align-top"><TableCell className="whitespace-nowrap">{formatDate(event.timestamp)}<p className="text-xs text-muted-foreground">{new Date(event.timestamp).toLocaleTimeString()}</p></TableCell><TableCell className="font-medium">{event.action.replace(/_/g, ' ')}</TableCell><TableCell>{event.entity_type}<p className="max-w-36 truncate text-xs text-muted-foreground" title={event.entity_id ?? ''}>{event.entity_id ?? '—'}</p></TableCell><TableCell>{event.role ?? 'Unknown'}<p className="max-w-32 truncate text-xs text-muted-foreground" title={event.user_id ?? ''}>{event.user_id ?? '—'}</p></TableCell><TableCell className="max-w-64"><p>{event.reason ?? '—'}</p><details className="mt-1 text-xs"><summary className="cursor-pointer text-primary">Before / after values</summary><pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words rounded bg-muted p-2">{JSON.stringify({ before: event.before_values, after: event.after_values }, null, 2)}</pre></details></TableCell></TableRow>)}</TableBody></Table> : <p className="py-10 text-center text-sm text-muted-foreground">No audit events match these filters.</p>}
        </CardContent>
      </Card>
    </div>
  );
};

export default AuditTrailPage;
