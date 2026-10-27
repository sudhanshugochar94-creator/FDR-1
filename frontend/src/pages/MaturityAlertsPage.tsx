import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, CalendarClock, RefreshCw } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { apiClient } from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface MaturityReport {
  maturing_7_days: number;
  maturing_15_days: number;
  maturing_30_days: number;
  already_matured: number;
  fdrs: Array<{
    id: string;
    reference: string;
    institution: string;
    bank: string;
    amount: number;
    maturity_date: string;
    days_until: number;
    status: string;
  }>;
}

const MaturityAlertsPage: React.FC = () => {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['reports', 'maturity'],
    queryFn: async () => (await apiClient.get<MaturityReport>('/api/reports/maturity')).data,
  });
  const chartData = data ? [
    { window: '7 days', count: data.maturing_7_days },
    { window: '15 days', count: data.maturing_15_days },
    { window: '30 days', count: data.maturing_30_days },
    { window: 'Already matured', count: data.already_matured },
  ] : [];

  return (
    <div className="space-y-6 pb-10">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Maturity schedule & alerts</h1>
        <p className="mt-1 text-sm text-muted-foreground">Upcoming maturities and overdue instruments from the live FDR register.</p>
      </div>
      {isError ? <Card><CardContent className="flex flex-col items-center gap-3 py-10"><p className="text-sm text-destructive">Unable to load maturity data.</p><Button variant="outline" onClick={() => refetch()}><RefreshCw className="mr-2 h-4 w-4" />Retry</Button></CardContent></Card> : <>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: 'Maturing in 7 days', value: data?.maturing_7_days },
            { label: 'Maturing in 15 days', value: data?.maturing_15_days },
            { label: 'Maturing in 30 days', value: data?.maturing_30_days },
            { label: 'Already matured', value: data?.already_matured },
          ].map((stat) => <Card key={stat.label}><CardHeader className="pb-2"><CardDescription>{stat.label}</CardDescription><CardTitle>{isLoading ? '—' : stat.value}</CardTitle></CardHeader></Card>)}
        </div>
        <div className="grid gap-6 lg:grid-cols-5">
          <Card className="lg:col-span-2">
            <CardHeader><CardTitle className="flex items-center gap-2"><CalendarClock className="h-5 w-5 text-primary" />Maturity windows</CardTitle><CardDescription>Current report counts by deadline.</CardDescription></CardHeader>
            <CardContent className="h-72">
              {isLoading ? <p className="py-20 text-center text-sm text-muted-foreground">Loading maturity report…</p> : <ResponsiveContainer width="100%" height="100%"><BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 8, left: -20 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="window" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer>}
            </CardContent>
          </Card>
          <Card className="lg:col-span-3">
            <CardHeader><CardTitle className="flex items-center gap-2"><AlertTriangle className="h-5 w-5 text-amber-500" />Next 60 days & overdue</CardTitle><CardDescription>Records are ordered by maturity date.</CardDescription></CardHeader>
            <CardContent>
              {isLoading ? <p className="py-8 text-center text-sm text-muted-foreground">Loading records…</p> : data?.fdrs.length ? <Table><TableHeader><TableRow><TableHead>Reference</TableHead><TableHead>Institution / bank</TableHead><TableHead>Amount</TableHead><TableHead>Maturity</TableHead><TableHead>Timing</TableHead></TableRow></TableHeader><TableBody>{data.fdrs.map((fdr) => <TableRow key={fdr.id}><TableCell className="font-medium">{fdr.reference}</TableCell><TableCell><p>{fdr.institution}</p><p className="text-xs text-muted-foreground">{fdr.bank}</p></TableCell><TableCell>{formatCurrency(fdr.amount)}</TableCell><TableCell>{formatDate(fdr.maturity_date)}</TableCell><TableCell><Badge variant={fdr.days_until < 0 ? 'destructive' : fdr.days_until <= 7 ? 'outline' : 'secondary'}>{fdr.days_until < 0 ? `${Math.abs(fdr.days_until)} days overdue` : fdr.days_until === 0 ? 'Due today' : `${fdr.days_until} days`}</Badge></TableCell></TableRow>)}</TableBody></Table> : <p className="py-10 text-center text-sm text-muted-foreground">No active FDRs due within the next 60 days.</p>}
            </CardContent>
          </Card>
        </div>
      </>}
    </div>
  );
};

export default MaturityAlertsPage;
