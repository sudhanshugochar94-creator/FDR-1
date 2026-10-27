import React, { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRightLeft, RefreshCw, Unlock } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { FDRInstrument } from '@/types';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from '@/components/ui/toast';

interface FDRListResponse {
  items: FDRInstrument[];
  total: number;
}

const RenewalsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState('');
  const [notes, setNotes] = useState('');
  const [releaseReason, setReleaseReason] = useState('');
  const fdrsQuery = useQuery({
    queryKey: ['fdrs', 'lifecycle'],
    queryFn: async () => (await apiClient.get<FDRListResponse>('/api/fdrs', { params: { page_size: 100, sort_by: 'maturity_date', sort_order: 'asc' } })).data,
  });
  const records = fdrsQuery.data?.items ?? [];
  const selectedFdr = records.find((fdr) => fdr.id === selectedId);
  const eligibleRecords = useMemo(() => records.filter((fdr) => !['RELEASED', 'REJECTED'].includes(fdr.status)), [records]);
  const refreshLifecycle = () => {
    queryClient.invalidateQueries({ queryKey: ['fdrs'] });
    queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  };
  const renewalMutation = useMutation({
    mutationFn: async () => apiClient.post(`/api/fdrs/${selectedId}/renewal-request`, { notes: notes.trim() || null }),
    onSuccess: () => { toast.success('Renewal request submitted'); setNotes(''); refreshLifecycle(); },
    onError: () => toast.error('Could not submit the renewal request. Please try again.'),
  });
  const releaseMutation = useMutation({
    mutationFn: async () => apiClient.post(`/api/fdrs/${selectedId}/release-request`, { reason: releaseReason.trim() }),
    onSuccess: () => { toast.success('Release request submitted'); setReleaseReason(''); refreshLifecycle(); },
    onError: () => toast.error('Could not submit the release request. Please try again.'),
  });

  return (
    <div className="space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Renewals & lien releases</h1>
        <p className="mt-1 text-sm text-muted-foreground">Start a lifecycle request for an accessible fixed deposit record.</p>
      </div>
      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Start a request</CardTitle><CardDescription>Requests are recorded against the selected FDR.</CardDescription></CardHeader>
          <CardContent className="space-y-4">
            {fdrsQuery.isError ? <div className="space-y-3"><p className="text-sm text-destructive">Unable to load FDR records.</p><Button variant="outline" onClick={() => fdrsQuery.refetch()}><RefreshCw className="mr-2 h-4 w-4" />Retry</Button></div> : <>
              <label className="block space-y-2 text-sm font-medium">Fixed deposit
                <select className="w-full rounded-md border bg-background px-3 py-2 font-normal" value={selectedId} onChange={(event) => setSelectedId(event.target.value)} disabled={fdrsQuery.isLoading}>
                  <option value="">Select a record</option>
                  {eligibleRecords.map((fdr) => <option key={fdr.id} value={fdr.id}>{fdr.internal_reference} · {fdr.bank_name} · {formatDate(fdr.maturity_date)}</option>)}
                </select>
              </label>
              {selectedFdr && <div className="rounded-md bg-muted/50 p-3 text-sm"><p className="font-medium">{selectedFdr.fdr_number}</p><p className="text-muted-foreground">{selectedFdr.institution_name ?? selectedFdr.institution?.name ?? selectedFdr.institution_id}</p><p>{formatCurrency(selectedFdr.deposit_amount, selectedFdr.currency)} · <Badge variant="secondary">{selectedFdr.status.replace(/_/g, ' ')}</Badge></p></div>}
              <label className="block space-y-2 text-sm font-medium">Renewal notes <span className="font-normal text-muted-foreground">(optional)</span>
                <textarea className="min-h-20 w-full rounded-md border bg-background p-3 font-normal" value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Add renewal context or supporting details" />
              </label>
              <Button className="w-full" disabled={!selectedId || renewalMutation.isPending || fdrsQuery.isLoading} onClick={() => renewalMutation.mutate()}><ArrowRightLeft className="mr-2 h-4 w-4" />{renewalMutation.isPending ? 'Submitting…' : 'Request renewal'}</Button>
              <div className="border-t pt-4">
                <label className="block space-y-2 text-sm font-medium">Release reason <span className="font-normal text-muted-foreground">(at least 10 characters)</span>
                  <textarea className="min-h-20 w-full rounded-md border bg-background p-3 font-normal" value={releaseReason} onChange={(event) => setReleaseReason(event.target.value)} placeholder="Explain why the deposit should be released" />
                </label>
                <Button className="mt-3 w-full" variant="outline" disabled={!selectedId || releaseReason.trim().length < 10 || releaseMutation.isPending} onClick={() => releaseMutation.mutate()}><Unlock className="mr-2 h-4 w-4" />{releaseMutation.isPending ? 'Submitting…' : 'Request lien release'}</Button>
              </div>
            </>}
          </CardContent>
        </Card>
        <Card className="lg:col-span-3">
          <CardHeader><CardTitle>FDR lifecycle</CardTitle><CardDescription>Accessible records sorted by their maturity date. The API currently supports submitting requests, but not listing prior renewal or release requests.</CardDescription></CardHeader>
          <CardContent>
            {fdrsQuery.isLoading ? <p className="py-8 text-center text-sm text-muted-foreground">Loading records…</p> : eligibleRecords.length ? <div className="space-y-3">{eligibleRecords.map((fdr) => <button type="button" key={fdr.id} onClick={() => setSelectedId(fdr.id)} className={`flex w-full items-center justify-between gap-4 rounded-lg border p-4 text-left transition-colors hover:bg-muted/50 ${selectedId === fdr.id ? 'border-primary bg-muted/30' : ''}`}>
              <div className="min-w-0"><p className="truncate font-medium">{fdr.internal_reference}</p><p className="truncate text-sm text-muted-foreground">{fdr.bank_name} · {fdr.institution_name ?? fdr.institution?.name ?? 'Institution'}</p><p className="mt-1 text-xs text-muted-foreground">Matures {formatDate(fdr.maturity_date)} · {formatCurrency(fdr.deposit_amount, fdr.currency)}</p></div>
              <Badge variant={fdr.status === 'RENEWAL_PENDING' ? 'outline' : 'secondary'}>{fdr.status.replace(/_/g, ' ')}</Badge>
            </button>)}</div> : <p className="py-8 text-center text-sm text-muted-foreground">No accessible FDR records are available.</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default RenewalsPage;
