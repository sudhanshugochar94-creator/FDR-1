import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, ExternalLink, RefreshCw, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiClient } from '@/lib/api';
import { FDRInstrument } from '@/types';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from '@/components/ui/toast';

interface DuplicateCandidate {
  id: string;
  fdr_a_id: string;
  fdr_b_id: string;
  match_score: number;
  match_reasons: string[];
  matching_fields: Record<string, unknown>;
  differing_fields: Record<string, unknown>;
  file_hash_match: boolean;
  status: string;
  review_notes?: string | null;
  created_at: string;
}

const DuplicateReviewPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [notes, setNotes] = useState<Record<string, string>>({});
  const candidatesQuery = useQuery({
    queryKey: ['duplicate-candidates'],
    queryFn: async () => (await apiClient.get<DuplicateCandidate[]>('/api/reports/duplicates')).data,
  });
  const fdrsQuery = useQuery({
    queryKey: ['fdrs', 'duplicate-review'],
    queryFn: async () =>
      (await apiClient.get<{ items: FDRInstrument[] }>('/api/fdrs', { params: { page_size: 100 } })).data.items,
  });
  const resolveMutation = useMutation({
    mutationFn: async ({ id, status, review_notes }: { id: string; status: string; review_notes: string }) =>
      apiClient.post(`/api/duplicates/${id}/resolve`, { status, review_notes }),
    onSuccess: () => {
      toast.success('Duplicate candidate updated');
      queryClient.invalidateQueries({ queryKey: ['duplicate-candidates'] });
      queryClient.invalidateQueries({ queryKey: ['fdrs'] });
    },
    onError: () => toast.error('Could not update the duplicate candidate. Please try again.'),
  });

  const fdrById = new Map((fdrsQuery.data ?? []).map((fdr) => [fdr.id, fdr]));
  const candidates = candidatesQuery.data ?? [];
  const pendingCount = candidates.filter((candidate) => candidate.status === 'PENDING').length;

  const resolve = (candidate: DuplicateCandidate, status: string) => {
    const review_notes = notes[candidate.id]?.trim() ?? '';
    if (review_notes.length < 2) {
      toast.error('Add a review note with at least 2 characters before resolving.');
      return;
    }
    resolveMutation.mutate({ id: candidate.id, status, review_notes });
  };

  return (
    <div className="space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Duplicate review</h1>
        <p className="mt-1 text-sm text-muted-foreground">Compare flagged FDR pairs and record a resolution.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card><CardHeader className="pb-2"><CardDescription>All candidates</CardDescription><CardTitle>{candidatesQuery.isLoading ? '—' : candidates.length}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Awaiting review</CardDescription><CardTitle className="text-amber-600">{candidatesQuery.isLoading ? '—' : pendingCount}</CardTitle></CardHeader></Card>
        <Card><CardHeader className="pb-2"><CardDescription>Resolved</CardDescription><CardTitle className="text-emerald-600">{candidatesQuery.isLoading ? '—' : candidates.length - pendingCount}</CardTitle></CardHeader></Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><AlertTriangle className="h-5 w-5 text-amber-500" />Candidate pairs</CardTitle>
          <CardDescription>Review evidence before marking a pair as a confirmed duplicate or false positive.</CardDescription>
        </CardHeader>
        <CardContent>
          {candidatesQuery.isLoading || fdrsQuery.isLoading ? (
            <p className="py-8 text-center text-sm text-muted-foreground">Loading duplicate candidates…</p>
          ) : candidatesQuery.isError || fdrsQuery.isError ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <p className="text-sm text-destructive">Unable to load duplicate review data from the server.</p>
              <Button variant="outline" onClick={() => { candidatesQuery.refetch(); fdrsQuery.refetch(); }}><RefreshCw className="mr-2 h-4 w-4" />Retry</Button>
            </div>
          ) : candidates.length === 0 ? (
            <div className="py-12 text-center">
              <ShieldCheck className="mx-auto mb-3 h-9 w-9 text-emerald-500" />
              <p className="font-medium">No duplicate candidates</p>
              <p className="mt-1 text-sm text-muted-foreground">New potential matches will appear here for review.</p>
            </div>
          ) : (
            <Table>
              <TableHeader><TableRow><TableHead>FDR pair</TableHead><TableHead>Match</TableHead><TableHead>Evidence</TableHead><TableHead>Status</TableHead><TableHead className="min-w-64">Resolution</TableHead></TableRow></TableHeader>
              <TableBody>
                {candidates.map((candidate) => {
                  const a = fdrById.get(candidate.fdr_a_id);
                  const b = fdrById.get(candidate.fdr_b_id);
                  return (
                    <TableRow key={candidate.id} className="align-top">
                      <TableCell className="min-w-56">
                        {[a, b].map((fdr, index) => {
                          const id = index === 0 ? candidate.fdr_a_id : candidate.fdr_b_id;
                          return <div key={id} className="mb-2 last:mb-0">
                            {fdr ? <Link className="font-medium text-primary hover:underline" to={`/fdrs/${id}`}>{fdr.internal_reference}<ExternalLink className="ml-1 inline h-3 w-3" /></Link> : <span className="font-medium">FDR {id.slice(0, 8)}</span>}
                            <p className="text-xs text-muted-foreground">{fdr ? `${fdr.bank_name} · ${fdr.fdr_number}` : 'Record details unavailable on this page'}</p>
                            {fdr && <p className="text-xs text-muted-foreground">{formatCurrency(fdr.deposit_amount, fdr.currency)} · matures {formatDate(fdr.maturity_date)}</p>}
                          </div>;
                        })}
                      </TableCell>
                      <TableCell><Badge variant={candidate.match_score >= 0.8 ? 'destructive' : 'secondary'}>{Math.round(candidate.match_score * 100)}%</Badge>{candidate.file_hash_match && <p className="mt-2 text-xs font-medium text-destructive">File hash match</p>}</TableCell>
                      <TableCell className="max-w-64">
                        <p className="text-sm">{Object.keys(candidate.matching_fields ?? {}).length ? Object.entries(candidate.matching_fields).map(([field, value]) => `${field.replace(/_/g, ' ')}: ${String(value)}`).join(', ') : 'No matching fields listed'}</p>
                        {candidate.differing_fields && Object.keys(candidate.differing_fields).length > 0 && <details className="mt-2 text-xs"><summary className="cursor-pointer text-muted-foreground">View differences</summary><pre className="mt-1 whitespace-pre-wrap break-words">{JSON.stringify(candidate.differing_fields, null, 2)}</pre></details>}
                        <p className="mt-2 text-xs text-muted-foreground">Added {formatDate(candidate.created_at)}</p>
                      </TableCell>
                      <TableCell><Badge variant={candidate.status === 'PENDING' ? 'outline' : candidate.status === 'CONFIRMED_DUPLICATE' ? 'destructive' : 'secondary'}>{candidate.status.replace(/_/g, ' ')}</Badge>{candidate.review_notes && <p className="mt-2 max-w-40 text-xs text-muted-foreground">{candidate.review_notes}</p>}</TableCell>
                      <TableCell>
                        {candidate.status === 'PENDING' ? <div className="space-y-2">
                          <textarea className="min-h-16 w-full rounded-md border bg-background p-2 text-sm" placeholder="Review note (required)" value={notes[candidate.id] ?? ''} onChange={(event) => setNotes((current) => ({ ...current, [candidate.id]: event.target.value }))} />
                          <div className="flex flex-wrap gap-2">
                            <Button size="sm" variant="destructive" disabled={resolveMutation.isPending} onClick={() => resolve(candidate, 'CONFIRMED_DUPLICATE')}>Confirm duplicate</Button>
                            <Button size="sm" variant="outline" disabled={resolveMutation.isPending} onClick={() => resolve(candidate, 'FALSE_POSITIVE')}>False positive</Button>
                          </div>
                        </div> : <span className="text-sm text-muted-foreground">Review complete</span>}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default DuplicateReviewPage;
