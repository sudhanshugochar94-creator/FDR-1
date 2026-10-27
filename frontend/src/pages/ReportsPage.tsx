import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, FileBarChart2, RefreshCw } from 'lucide-react';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { apiClient } from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from '@/components/ui/toast';

interface OverviewReport {
  total_fdrs: number;
  status_distribution: Record<string, number>;
  verification_distribution: Record<string, number>;
  total_deposit_value: number;
  average_priority_score: number;
  pending_duplicates: number;
  pending_releases: number;
  pending_renewals: number;
}

interface PendingCase {
  id: string;
  reference: string;
  institution: string;
  bank: string;
  amount: number;
  status: string;
  priority_score: number;
  priority_reasons?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

const COLORS = ['#2563eb', '#7c3aed', '#f59e0b', '#10b981', '#ef4444', '#64748b', '#06b6d4'];

const ReportsPage: React.FC = () => {
  const overview = useQuery({
    queryKey: ['reports', 'overview'],
    queryFn: async () => (await apiClient.get<OverviewReport>('/api/reports/overview')).data,
  });
  const pending = useQuery({
    queryKey: ['reports', 'pending-cases'],
    queryFn: async () => (await apiClient.get<PendingCase[]>('/api/reports/pending-cases')).data,
  });
  const downloadCsv = async () => {
    try {
      const response = await apiClient.get<Blob>('/api/reports/export', { responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `fdr-export-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      toast.success('FDR report downloaded');
    } catch {
      toast.error('Could not download the FDR report. Please try again.');
    }
  };
  const chartData = Object.entries(overview.data?.status_distribution ?? {}).map(([status, count]) => ({ status: status.replace(/_/g, ' '), count }));
  const reload = () => { overview.refetch(); pending.refetch(); };

  return (
    <div className="space-y-6 pb-10">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><h1 className="text-2xl font-bold tracking-tight">Reports & analytics</h1><p className="mt-1 text-sm text-muted-foreground">Compliance overview, review workload, and downloadable FDR register.</p></div>
        <div className="flex gap-2"><Button variant="outline" onClick={reload}><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button><Button onClick={downloadCsv}><Download className="mr-2 h-4 w-4" />Export CSV</Button></div>
      </div>
      {(overview.isError || pending.isError) && <Card><CardContent className="flex items-center justify-between gap-4 py-4"><p className="text-sm text-destructive">Some report data could not be loaded. Retry the affected request.</p><Button variant="outline" size="sm" onClick={reload}>Retry</Button></CardContent></Card>}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ['Total FDRs', overview.data?.total_fdrs],
          ['Deposit value', overview.data ? formatCurrency(overview.data.total_deposit_value) : undefined],
          ['Pending duplicates', overview.data?.pending_duplicates],
          ['Renewals / releases', overview.data ? `${overview.data.pending_renewals} / ${overview.data.pending_releases}` : undefined],
        ].map(([label, value]) => <Card key={String(label)}><CardHeader className="pb-2"><CardDescription>{label}</CardDescription><CardTitle>{overview.isLoading ? '—' : value ?? 'Unavailable'}</CardTitle></CardHeader></Card>)}
      </div>
      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle className="flex items-center gap-2"><FileBarChart2 className="h-5 w-5 text-primary" />Status distribution</CardTitle><CardDescription>Current count by FDR workflow status.</CardDescription></CardHeader>
          <CardContent className="h-72">
            {overview.isLoading ? <p className="py-20 text-center text-sm text-muted-foreground">Loading overview…</p> : chartData.length ? <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={chartData} dataKey="count" nameKey="status" cx="50%" cy="50%" outerRadius={92} label={({ status, count }) => `${status}: ${count}`} labelLine={false}>{chartData.map((entry, index) => <Cell key={entry.status} fill={COLORS[index % COLORS.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer> : <p className="py-20 text-center text-sm text-muted-foreground">No status data available.</p>}
          </CardContent>
          {overview.data && <div className="px-6 pb-5 text-sm text-muted-foreground">Average review priority: <span className="font-medium text-foreground">{overview.data.average_priority_score.toFixed(1)}</span></div>}
        </Card>
        <Card className="lg:col-span-3">
          <CardHeader><CardTitle>Verification distribution</CardTitle><CardDescription>Counts reported by the verification workflow.</CardDescription></CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {overview.isLoading ? <p className="text-sm text-muted-foreground">Loading verification summary…</p> : Object.entries(overview.data?.verification_distribution ?? {}).map(([status, count]) => <div key={status} className="flex items-center justify-between rounded-lg border p-4"><span className="text-sm">{status.replace(/_/g, ' ')}</span><Badge variant="secondary">{count}</Badge></div>)}
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader><CardTitle>Pending review cases</CardTitle><CardDescription>Open cases sorted by review priority.</CardDescription></CardHeader>
        <CardContent>
          {pending.isLoading ? <p className="py-8 text-center text-sm text-muted-foreground">Loading pending cases…</p> : pending.data?.length ? <Table><TableHeader><TableRow><TableHead>Reference</TableHead><TableHead>Institution / bank</TableHead><TableHead>Amount</TableHead><TableHead>Status</TableHead><TableHead>Priority</TableHead><TableHead>Updated</TableHead></TableRow></TableHeader><TableBody>{pending.data.map((item) => <TableRow key={item.id}><TableCell className="font-medium">{item.reference}</TableCell><TableCell>{item.institution}<p className="text-xs text-muted-foreground">{item.bank}</p></TableCell><TableCell>{formatCurrency(item.amount)}</TableCell><TableCell><Badge variant="outline">{item.status.replace(/_/g, ' ')}</Badge></TableCell><TableCell>{item.priority_score}</TableCell><TableCell>{formatDate(item.updated_at)}</TableCell></TableRow>)}</TableBody></Table> : <p className="py-8 text-center text-sm text-muted-foreground">{pending.isError ? 'Pending cases are unavailable.' : 'There are no pending cases.'}</p>}
        </CardContent>
      </Card>
    </div>
  );
};

export default ReportsPage;
