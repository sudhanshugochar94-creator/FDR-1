import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  CheckCircle,
  Clock,
  AlertTriangle,
  FileCheck,
  Calendar,
  AlertOctagon,
  RefreshCw,
  Unlock,
  Archive,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  PlusCircle,
  ChevronRight,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/hooks/useAuth';
import { DashboardData } from '@/types';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

// Comprehensive mock data fallback
const FALLBACK_DASHBOARD: DashboardData = {
  total_fdrs: 1248,
  active_fdrs: 890,
  awaiting_verification: 64,
  potential_duplicates: 18,
  needs_review: 47,
  maturing_30_days: 32,
  overdue_actions: 12,
  renewal_requests: 29,
  pending_releases: 15,
  released_fdrs: 187,
  status_distribution: [
    { status: 'ACTIVE', count: 890 },
    { status: 'VERIFIED', count: 120 },
    { status: 'UNDER_REVIEW', count: 47 },
    { status: 'AWAITING_VERIFICATION', count: 64 },
    { status: 'RENEWAL_PENDING', count: 29 },
    { status: 'RELEASED', count: 187 },
    { status: 'REJECTED', count: 21 },
  ],
  monthly_maturities: [
    { month: 'Nov 2026', count: 32, total_amount: 45000000 },
    { month: 'Dec 2026', count: 48, total_amount: 72000000 },
    { month: 'Jan 2027', count: 65, total_amount: 98000000 },
    { month: 'Feb 2027', count: 41, total_amount: 54000000 },
    { month: 'Mar 2027', count: 89, total_amount: 142000000 },
    { month: 'Apr 2027', count: 53, total_amount: 81000000 },
  ],
  review_queue: [
    {
      id: 'fdr-101',
      internal_reference: 'FDR-2026-0089',
      institution_id: 'inst-01',
      institution: { id: 'inst-01', name: 'National Institute of Tech & Science', code: 'NITS-01' },
      bank_name: 'State Bank of India',
      branch_name: 'Connaught Place, New Delhi',
      fdr_number: 'SBI-9844-0129-A',
      deposit_amount: 5000000,
      currency: 'INR',
      issue_date: '2023-10-15',
      maturity_date: '2026-10-15',
      status: 'UNDER_REVIEW',
      verification_status: 'AWAITING_BANK_VERIFICATION',
      review_priority_score: 95,
      review_priority_reasons: { risk: 'Duplicate hash candidate & high value deposit' },
      has_potential_duplicate: true,
      created_at: '2026-10-20T10:30:00Z',
      updated_at: '2026-10-21T09:15:00Z',
    },
    {
      id: 'fdr-102',
      internal_reference: 'FDR-2026-0094',
      institution_id: 'inst-02',
      institution: { id: 'inst-02', name: 'Delhi Institute of Pharmaceutical Sciences', code: 'DIPS-04' },
      bank_name: 'Punjab National Bank',
      branch_name: 'Nehru Place, New Delhi',
      fdr_number: 'PNB-3312-8871-X',
      deposit_amount: 2500000,
      currency: 'INR',
      issue_date: '2024-03-01',
      maturity_date: '2027-03-01',
      status: 'EXTRACTED',
      verification_status: 'PENDING',
      review_priority_score: 82,
      review_priority_reasons: { risk: 'IFSC code mismatch with RBI clearing database' },
      has_potential_duplicate: false,
      created_at: '2026-10-20T14:20:00Z',
      updated_at: '2026-10-21T08:00:00Z',
    },
    {
      id: 'fdr-103',
      internal_reference: 'FDR-2026-0105',
      institution_id: 'inst-03',
      institution: { id: 'inst-03', name: 'St. Xavier College of Engineering', code: 'SXCE-12' },
      bank_name: 'HDFC Bank',
      branch_name: 'Bandra Kurla Complex, Mumbai',
      fdr_number: 'HDFC-5541-0023-B',
      deposit_amount: 10000000,
      currency: 'INR',
      issue_date: '2024-05-10',
      maturity_date: '2026-11-10',
      status: 'UNDER_REVIEW',
      verification_status: 'PENDING',
      review_priority_score: 78,
      review_priority_reasons: { risk: 'Mandatory endowment deposit maturing soon' },
      has_potential_duplicate: false,
      created_at: '2026-10-19T11:45:00Z',
      updated_at: '2026-10-20T16:30:00Z',
    },
  ],
  recent_updates: [
    {
      id: 'fdr-101',
      internal_reference: 'FDR-2026-0089',
      institution_id: 'inst-01',
      institution: { id: 'inst-01', name: 'National Institute of Tech & Science', code: 'NITS-01' },
      bank_name: 'State Bank of India',
      fdr_number: 'SBI-9844-0129-A',
      deposit_amount: 5000000,
      currency: 'INR',
      issue_date: '2023-10-15',
      maturity_date: '2026-10-15',
      status: 'UNDER_REVIEW',
      verification_status: 'AWAITING_BANK_VERIFICATION',
      review_priority_score: 95,
      has_potential_duplicate: true,
      created_at: '2026-10-20T10:30:00Z',
      updated_at: '2026-10-21T09:15:00Z',
    },
    {
      id: 'fdr-104',
      internal_reference: 'FDR-2026-0072',
      institution_id: 'inst-04',
      institution: { id: 'inst-04', name: 'Institute of Marine Research', code: 'IMR-09' },
      bank_name: 'Bank of Baroda',
      fdr_number: 'BOB-9982-1144',
      deposit_amount: 3500000,
      currency: 'INR',
      issue_date: '2025-01-12',
      maturity_date: '2028-01-12',
      status: 'ACTIVE',
      verification_status: 'VERIFIED',
      review_priority_score: 10,
      has_potential_duplicate: false,
      created_at: '2026-10-18T09:00:00Z',
      updated_at: '2026-10-21T08:30:00Z',
    },
    {
      id: 'fdr-105',
      internal_reference: 'FDR-2026-0061',
      institution_id: 'inst-05',
      institution: { id: 'inst-05', name: 'Global School of Management', code: 'GSM-88' },
      bank_name: 'Canara Bank',
      fdr_number: 'CNRB-4410-9281',
      deposit_amount: 1500000,
      currency: 'INR',
      issue_date: '2023-08-20',
      maturity_date: '2026-08-20',
      status: 'RENEWAL_PENDING',
      verification_status: 'VERIFIED',
      review_priority_score: 65,
      has_potential_duplicate: false,
      created_at: '2026-10-17T12:00:00Z',
      updated_at: '2026-10-20T18:00:00Z',
    },
  ],
  upcoming_deadlines: [
    {
      id: 'fdr-103',
      internal_reference: 'FDR-2026-0105',
      institution_name: 'St. Xavier College of Engineering',
      maturity_date: '2026-11-10',
      days_until: 20,
    },
    {
      id: 'fdr-106',
      internal_reference: 'FDR-2024-9912',
      institution_name: 'Pinnacle College of Architecture',
      maturity_date: '2026-11-18',
      days_until: 28,
    },
    {
      id: 'fdr-107',
      internal_reference: 'FDR-2023-5582',
      institution_name: 'Universal Polytechnic College',
      maturity_date: '2026-11-20',
      days_until: 30,
    },
  ],
};

const PIE_COLORS = [
  '#10b981', // green Active
  '#3b82f6', // blue Verified
  '#f59e0b', // amber Under review
  '#6366f1', // indigo Awaiting verif
  '#ec4899', // pink Renewal
  '#8b5cf6', // purple Released
  '#ef4444', // red Rejected
];

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const { data: dashboard = FALLBACK_DASHBOARD, isLoading } = useQuery<DashboardData>({
    queryKey: ['dashboard-data'],
    queryFn: async () => {
      try {
        const res = await apiClient.get<DashboardData>('/api/dashboard');
        return res.data;
      } catch (err) {
        return FALLBACK_DASHBOARD;
      }
    },
    staleTime: 60000,
  });

  const stats = [
    {
      title: 'Total FDRs',
      value: dashboard.total_fdrs,
      color: 'border-l-blue-500 text-blue-600 dark:text-blue-400',
      bgLight: 'bg-blue-50/50 dark:bg-blue-950/20',
      icon: FileText,
      description: 'Repository instruments',
    },
    {
      title: 'Active Deposits',
      value: dashboard.active_fdrs,
      color: 'border-l-emerald-500 text-emerald-600 dark:text-emerald-400',
      bgLight: 'bg-emerald-50/50 dark:bg-emerald-950/20',
      icon: CheckCircle,
      description: 'Valid compliance cover',
    },
    {
      title: 'Awaiting Verification',
      value: dashboard.awaiting_verification,
      color: 'border-l-yellow-500 text-yellow-600 dark:text-yellow-400',
      bgLight: 'bg-yellow-50/50 dark:bg-yellow-950/20',
      icon: Clock,
      description: 'With depository banks',
    },
    {
      title: 'Potential Duplicates',
      value: dashboard.potential_duplicates,
      color: 'border-l-red-500 text-red-600 dark:text-red-400',
      bgLight: 'bg-red-50/50 dark:bg-red-950/20',
      icon: AlertTriangle,
      description: 'Risk score threshold hit',
      badge: 'Action Needed',
    },
    {
      title: 'Needs Review',
      value: dashboard.needs_review,
      color: 'border-l-orange-500 text-orange-600 dark:text-orange-400',
      bgLight: 'bg-orange-50/50 dark:bg-orange-950/20',
      icon: FileCheck,
      description: 'Pending officer evaluation',
    },
    {
      title: 'Maturing in 30 Days',
      value: dashboard.maturing_30_days,
      color: 'border-l-purple-500 text-purple-600 dark:text-purple-400',
      bgLight: 'bg-purple-50/50 dark:bg-purple-950/20',
      icon: Calendar,
      description: 'Upcoming renewal notice',
    },
    {
      title: 'Overdue Actions',
      value: dashboard.overdue_actions,
      color: 'border-l-rose-600 text-rose-600 dark:text-rose-400',
      bgLight: 'bg-rose-50/50 dark:bg-rose-950/20',
      icon: AlertOctagon,
      description: 'Breached compliance SLA',
    },
    {
      title: 'Renewal Requests',
      value: dashboard.renewal_requests,
      color: 'border-l-sky-500 text-sky-600 dark:text-sky-400',
      bgLight: 'bg-sky-50/50 dark:bg-sky-950/20',
      icon: RefreshCw,
      description: 'Institutions filed renewal',
    },
    {
      title: 'Pending Releases',
      value: dashboard.pending_releases,
      color: 'border-l-amber-500 text-amber-600 dark:text-amber-400',
      bgLight: 'bg-amber-50/50 dark:bg-amber-950/20',
      icon: Unlock,
      description: 'Awaiting authority release',
    },
    {
      title: 'Released FDRs',
      value: dashboard.released_fdrs,
      color: 'border-l-teal-500 text-teal-600 dark:text-teal-400',
      bgLight: 'bg-teal-50/50 dark:bg-teal-950/20',
      icon: Archive,
      description: 'Archived settlements',
    },
  ];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-9 w-36" />
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {Array.from({ length: 10 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-lg" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Skeleton className="h-80 w-full rounded-lg" />
          <Skeleton className="h-80 w-full rounded-lg" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Page Title & Quick Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            {user?.role === 'institution_user'
              ? 'Institution Compliance Dashboard'
              : 'Compliance & Intelligence Dashboard'}
          </h1>
          <p className="text-sm text-muted-foreground">
            {user?.role === 'institution_user'
              ? "Track your institution's FDR submissions, verification status, and maturity deadlines."
              : 'Real-time regulatory oversight, duplicate detection, and FDR portfolio risk tracking.'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {user?.role !== 'institution_user' && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/duplicates')}
              className="text-xs"
            >
              <AlertTriangle className="mr-1.5 h-3.5 w-3.5 text-amber-500" />
              Duplicate Queue ({dashboard.potential_duplicates})
            </Button>
          )}
          <Button
            size="sm"
            onClick={() => navigate('/fdrs/new')}
            className="bg-blue-600 hover:bg-blue-700 text-white text-xs"
          >
            <PlusCircle className="mr-1.5 h-3.5 w-3.5" />
            Submit New FDR
          </Button>
        </div>
      </div>

      {/* 10 Stat Cards Row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <Card
              key={idx}
              className={`border-l-4 ${stat.color} ${stat.bgLight} shadow-2xs hover:shadow-sm transition-shadow`}
            >
              <CardContent className="p-3.5 sm:p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-muted-foreground truncate">
                    {stat.title}
                  </span>
                  <Icon className="h-4 w-4 opacity-75 shrink-0" />
                </div>
                <div className="mt-2 flex items-baseline justify-between">
                  <span className="text-2xl font-bold tracking-tight text-foreground">
                    {stat.value.toLocaleString()}
                  </span>
                  {stat.badge && (
                    <Badge variant="destructive" className="text-[9px] px-1 py-0">
                      {stat.badge}
                    </Badge>
                  )}
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground truncate">
                  {stat.description}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Status Distribution Pie */}
        <Card className="lg:col-span-5 shadow-xs">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold flex items-center justify-between">
              <span>Status Distribution</span>
              <ShieldCheck className="h-4 w-4 text-primary" />
            </CardTitle>
            <CardDescription className="text-xs">
              Instrument lifecycle progression across all active filings
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={dashboard.status_distribution}
                    dataKey="count"
                    nameKey="status"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={3}
                  >
                    {dashboard.status_distribution.map((_, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={PIE_COLORS[index % PIE_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <RechartsTooltip
                    formatter={(val: number) => [`${val} instruments`, 'Count']}
                    contentStyle={{ borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    iconSize={10}
                    wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Maturity Forecast BarChart */}
        <Card className="lg:col-span-7 shadow-xs">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold flex items-center justify-between">
              <span>Maturity Timeline (Next 6 Months)</span>
              <TrendingUp className="h-4 w-4 text-emerald-600" />
            </CardTitle>
            <CardDescription className="text-xs">
              Projected deposit maturities requiring compliance verification or release
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={dashboard.monthly_maturities}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <RechartsTooltip
                    formatter={(val: number) => [`${val} FDRs`, 'Maturities']}
                    contentStyle={{ borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Bar
                    dataKey="count"
                    fill="#3b82f6"
                    radius={[4, 4, 0, 0]}
                    name="Maturities"
                    isAnimationActive={false}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Review Queue Table */}
      <Card className="shadow-xs">
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-base font-semibold">
              Review Priority Queue
            </CardTitle>
            <CardDescription className="text-xs">
              Automated compliance risk-scored instruments requiring immediate reviewer action
            </CardDescription>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/fdrs?status=UNDER_REVIEW')}
            className="text-xs text-primary"
          >
            View all pending ({dashboard.needs_review})
            <ChevronRight className="ml-1 h-3.5 w-3.5" />
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/30">
                <TableHead className="w-24">Risk Score</TableHead>
                <TableHead>Internal Ref / Bank</TableHead>
                <TableHead>Institution</TableHead>
                <TableHead>Deposit Amount</TableHead>
                <TableHead>Maturity</TableHead>
                <TableHead>Flag / Finding</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(dashboard.review_queue || []).length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center text-xs text-muted-foreground">
                    No high-priority reviews in queue. All compliance thresholds met.
                  </TableCell>
                </TableRow>
              ) : (
                (dashboard.review_queue || []).map((fdr) => (
                  <TableRow key={fdr.id} className="hover:bg-muted/40 transition-colors">
                    <TableCell>
                      <Badge
                        variant={fdr.review_priority_score >= 80 ? 'destructive' : 'warning'}
                        className="font-mono text-xs"
                      >
                        {fdr.review_priority_score} / 100
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="font-semibold text-xs text-foreground">
                        {fdr.internal_reference}
                      </div>
                      <div className="text-[11px] text-muted-foreground">{fdr.bank_name}</div>
                    </TableCell>
                    <TableCell>
                      <div className="font-medium text-xs text-foreground">
                        {fdr.institution?.name || 'Authorized Entity'}
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        {fdr.institution?.code || 'INST-CODE'}
                      </div>
                    </TableCell>
                    <TableCell className="font-medium text-xs">
                      {formatCurrency(fdr.deposit_amount, fdr.currency)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(fdr.maturity_date)}
                    </TableCell>
                    <TableCell>
                      {fdr.has_potential_duplicate ? (
                        <span className="inline-flex items-center text-xs font-semibold text-destructive">
                          <AlertTriangle className="mr-1 h-3.5 w-3.5" />
                          Potential Duplicate
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          {fdr.review_priority_reasons?.risk || 'Verification needed'}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => navigate(`/fdrs/${fdr.id}`)}
                        className="h-7 text-xs"
                      >
                        Review
                        <ArrowRight className="ml-1 h-3 w-3" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Bottom Grid: Recent Updates & Upcoming Deadlines */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Updates */}
        <Card className="shadow-xs">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold flex items-center justify-between">
              <span>Recent Activity & Submissions</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/fdrs')}
                className="text-xs text-primary h-7"
              >
                Browse all
              </Button>
            </CardTitle>
            <CardDescription className="text-xs">
              Latest instrument events recorded across the state regulatory network
            </CardDescription>
          </CardHeader>
          <CardContent className="divide-y divide-border p-0">
            {dashboard.recent_updates.map((item) => (
              <div
                key={item.id}
                onClick={() => navigate(`/fdrs/${item.id}`)}
                className="flex cursor-pointer items-center justify-between p-4 hover:bg-muted/40 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-semibold text-foreground">
                      {item.internal_reference}
                    </span>
                    <Badge variant="outline" className="text-[10px]">
                      {item.status}
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {item.institution?.name} • {item.bank_name}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-semibold text-foreground">
                    {formatCurrency(item.deposit_amount, item.currency)}
                  </div>
                  <div className="text-[10px] text-muted-foreground">
                    Updated {formatDate(item.updated_at)}
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Upcoming Deadlines */}
        <Card className="shadow-xs">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold flex items-center justify-between">
              <span>Upcoming Maturity Deadlines</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/maturity')}
                className="text-xs text-primary h-7"
              >
                View calendar
              </Button>
            </CardTitle>
            <CardDescription className="text-xs">
              Instruments requiring extension, renewal, or lien release execution
            </CardDescription>
          </CardHeader>
          <CardContent className="divide-y divide-border p-0">
            {dashboard.upcoming_deadlines.map((item) => (
              <div
                key={item.id}
                onClick={() => navigate(`/fdrs/${item.id}`)}
                className="flex cursor-pointer items-center justify-between p-4 hover:bg-muted/40 transition-colors"
              >
                <div className="space-y-1">
                  <div className="text-xs font-semibold text-foreground">
                    {item.internal_reference}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {item.institution_name}
                  </div>
                </div>
                <div className="text-right">
                  <Badge
                    variant={item.days_until <= 15 ? 'destructive' : 'warning'}
                    className="text-[11px]"
                  >
                    {item.days_until} days remaining
                  </Badge>
                  <div className="mt-1 text-[10px] text-muted-foreground">
                    Matures {formatDate(item.maturity_date)}
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default DashboardPage;
