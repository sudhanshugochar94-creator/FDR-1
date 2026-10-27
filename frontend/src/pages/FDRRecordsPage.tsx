import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Search,
  Filter,
  Download,
  Plus,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Eye,
  AlertTriangle,
  RotateCcw,
  CheckCircle,
  Clock,
  XCircle,
  RefreshCw,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { FDRInstrument, FDRStatus, PaginatedResponse, VerificationStatus } from '@/types';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

type SortField = 'deposit_amount' | 'maturity_date' | 'issue_date' | 'review_priority_score' | 'internal_reference';
type SortDirection = 'asc' | 'desc';

export const FDRRecordsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Filters from query params or local state
  const [statusFilter, setStatusFilter] = useState<string>(searchParams.get('status') || 'ALL');
  const [verificationFilter, setVerificationFilter] = useState<string>(searchParams.get('verification') || 'ALL');
  const [bankFilter, setBankFilter] = useState<string>(searchParams.get('bank') || '');
  const [searchQuery, setSearchQuery] = useState<string>(searchParams.get('search') || '');

  // Sorting
  const [sortField, setSortField] = useState<SortField>('review_priority_score');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // React Query fetch
  const { data, isLoading, isError, error, refetch } = useQuery<PaginatedResponse<FDRInstrument>>({
    queryKey: ['fdr-records', statusFilter, verificationFilter, bankFilter, searchQuery, currentPage, sortField, sortDirection],
    queryFn: async () => {
      const params: Record<string, string | number> = {
        page: currentPage,
        page_size: pageSize,
        sort_by: sortField,
        sort_order: sortDirection,
      };
      if (statusFilter !== 'ALL') params.status = statusFilter;
      if (verificationFilter !== 'ALL') params.verification_status = verificationFilter;
      if (bankFilter) params.bank_name = bankFilter;
      if (searchQuery) params.search = searchQuery;

      const res = await apiClient.get<PaginatedResponse<FDRInstrument>>('/api/fdrs', { params });
      return res.data;
    },
    staleTime: 30000,
  });

  const records = data?.items ?? [];
  const totalItems = data?.total ?? 0;
  const totalPages = data?.pages ?? 1;

  // Pagination calculation
  const paginatedRecords = records;

  useEffect(() => {
    setCurrentPage(1);
  }, [statusFilter, verificationFilter, bankFilter, searchQuery]);

  const handleResetFilters = () => {
    setStatusFilter('ALL');
    setVerificationFilter('ALL');
    setBankFilter('');
    setSearchQuery('');
    setSearchParams({});
    setCurrentPage(1);
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
    setCurrentPage(1);
  };

  const exportCSV = () => {
    const headers = [
      'Internal Reference',
      'Institution Name',
      'Institution Code',
      'Bank Name',
      'Branch',
      'FDR Number',
      'Amount',
      'Currency',
      'Issue Date',
      'Maturity Date',
      'Status',
      'Verification Status',
      'Risk Score',
      'Potential Duplicate',
    ];

    const rows = records.map((r) => [
      r.internal_reference,
      `"${r.institution_name || ''}"`,
      r.institution_code || '',
      `"${r.bank_name}"`,
      `"${r.branch_name || ''}"`,
      r.fdr_number,
      r.deposit_amount,
      r.currency,
      r.issue_date,
      r.maturity_date,
      r.status,
      r.verification_status,
      r.review_priority_score,
      r.has_potential_duplicate ? 'YES' : 'NO',
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `FDR_Regulatory_Records_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getStatusBadge = (status: FDRStatus) => {
    switch (status) {
      case 'ACTIVE':
        return <Badge variant="success">ACTIVE</Badge>;
      case 'VERIFIED':
        return <Badge variant="info">VERIFIED</Badge>;
      case 'UNDER_REVIEW':
        return <Badge variant="warning">UNDER REVIEW</Badge>;
      case 'RENEWAL_PENDING':
        return <Badge variant="outline" className="text-purple-600 border-purple-300">RENEWAL PENDING</Badge>;
      case 'RELEASED':
        return <Badge variant="secondary">RELEASED</Badge>;
      case 'REJECTED':
        return <Badge variant="destructive">REJECTED</Badge>;
      case 'SUBMITTED':
      case 'EXTRACTED':
      case 'VALIDATED':
        return <Badge variant="outline">{status}</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getVerificationBadge = (vStatus: VerificationStatus) => {
    switch (vStatus) {
      case 'VERIFIED':
        return (
          <span className="inline-flex items-center text-xs font-semibold text-emerald-600">
            <CheckCircle className="mr-1 h-3.5 w-3.5" />
            Verified
          </span>
        );
      case 'AWAITING_BANK_VERIFICATION':
        return (
          <span className="inline-flex items-center text-xs font-medium text-amber-600">
            <Clock className="mr-1 h-3.5 w-3.5" />
            Bank Awaiting
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center text-xs font-semibold text-destructive">
            <XCircle className="mr-1 h-3.5 w-3.5" />
            Failed
          </span>
        );
      case 'PENDING':
      default:
        return (
          <span className="inline-flex items-center text-xs text-muted-foreground">
            <Clock className="mr-1 h-3.5 w-3.5" />
            Pending
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Page Title & Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            FDR Regulatory Records
          </h1>
          <p className="text-sm text-muted-foreground">
            Comprehensive registry of all fixed deposit receipts, liens, and compliance instruments.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" onClick={exportCSV} className="text-xs">
            <Download className="mr-1.5 h-3.5 w-3.5" />
            Export CSV
          </Button>
          <Button
            size="sm"
            onClick={() => navigate('/fdrs/new')}
            className="bg-blue-600 hover:bg-blue-700 text-white text-xs"
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Submit New FDR
          </Button>
        </div>
      </div>

      {/* Filter Toolbar Card */}
      <Card className="shadow-xs">
        <CardHeader className="pb-3 pt-4 px-4 sm:px-6">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold flex items-center space-x-2">
              <Filter className="h-4 w-4 text-primary" />
              <span>Filter Instruments</span>
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleResetFilters}
              className="h-7 text-xs text-muted-foreground hover:text-foreground"
            >
              <RotateCcw className="mr-1 h-3 w-3" />
              Reset Filters
            </Button>
          </div>
        </CardHeader>
        <CardContent className="px-4 sm:px-6 pb-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {/* Search by text */}
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search reference, FDR #, institution..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 text-xs"
              />
            </div>

            {/* Status Select */}
            <Select value={statusFilter} onValueChange={(val) => setStatusFilter(val)}>
              <SelectTrigger className="text-xs">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Statuses</SelectItem>
                <SelectItem value="ACTIVE">ACTIVE</SelectItem>
                <SelectItem value="UNDER_REVIEW">UNDER REVIEW</SelectItem>
                <SelectItem value="VERIFIED">VERIFIED</SelectItem>
                <SelectItem value="EXTRACTED">EXTRACTED</SelectItem>
                <SelectItem value="RENEWAL_PENDING">RENEWAL PENDING</SelectItem>
                <SelectItem value="RELEASED">RELEASED</SelectItem>
                <SelectItem value="REJECTED">REJECTED</SelectItem>
              </SelectContent>
            </Select>

            {/* Verification Status */}
            <Select value={verificationFilter} onValueChange={(val) => setVerificationFilter(val)}>
              <SelectTrigger className="text-xs">
                <SelectValue placeholder="All Verification Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Verification</SelectItem>
                <SelectItem value="VERIFIED">Verified</SelectItem>
                <SelectItem value="AWAITING_BANK_VERIFICATION">Awaiting Bank</SelectItem>
                <SelectItem value="PENDING">Pending</SelectItem>
                <SelectItem value="REJECTED">Rejected</SelectItem>
              </SelectContent>
            </Select>

            {/* Bank Filter */}
            <Input
              placeholder="Filter by Bank Name..."
              value={bankFilter}
              onChange={(e) => setBankFilter(e.target.value)}
              className="text-xs"
            />
          </div>
        </CardContent>
      </Card>

      {/* Main Table Card */}
      <Card className="shadow-xs overflow-hidden">
        <CardHeader className="py-3 px-4 sm:px-6 border-b flex flex-row items-center justify-between">
          <div className="text-xs font-semibold text-muted-foreground">
            Showing <span className="font-bold text-foreground">{paginatedRecords.length}</span> of{' '}
            <span className="font-bold text-foreground">{totalItems}</span> matching records
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : isError ? (
            <div className="p-12 text-center space-y-3">
              <h3 className="text-sm font-semibold text-foreground">Could not load FDR records</h3>
              <p className="text-xs text-muted-foreground">
                {error instanceof Error ? error.message : 'The records service returned an unexpected response.'}
              </p>
              <Button variant="outline" size="sm" onClick={() => refetch()} className="text-xs">
                <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                Try again
              </Button>
            </div>
          ) : paginatedRecords.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-muted">
                <Search className="h-6 w-6 text-muted-foreground" />
              </div>
              <h3 className="text-sm font-semibold text-foreground">No FDR records found</h3>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                No instruments match your active filter criteria. Try adjusting your query or resetting filters.
              </p>
              <Button variant="outline" size="sm" onClick={handleResetFilters} className="text-xs">
                Clear Filters
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40">
                  <TableHead
                    className="cursor-pointer select-none"
                    onClick={() => handleSort('internal_reference')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Internal Ref</span>
                      {sortField === 'internal_reference' ? (
                        sortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowUpDown className="h-3 w-3 opacity-40" />
                      )}
                    </div>
                  </TableHead>
                  <TableHead>Institution</TableHead>
                  <TableHead>Bank / FDR #</TableHead>
                  <TableHead
                    className="cursor-pointer select-none"
                    onClick={() => handleSort('deposit_amount')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Amount</span>
                      {sortField === 'deposit_amount' ? (
                        sortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowUpDown className="h-3 w-3 opacity-40" />
                      )}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none"
                    onClick={() => handleSort('issue_date')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Issue Date</span>
                      {sortField === 'issue_date' ? (
                        sortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowUpDown className="h-3 w-3 opacity-40" />
                      )}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none"
                    onClick={() => handleSort('maturity_date')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Maturity Date</span>
                      {sortField === 'maturity_date' ? (
                        sortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowUpDown className="h-3 w-3 opacity-40" />
                      )}
                    </div>
                  </TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Verification</TableHead>
                  <TableHead
                    className="cursor-pointer select-none"
                    onClick={() => handleSort('review_priority_score')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Risk</span>
                      {sortField === 'review_priority_score' ? (
                        sortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowUpDown className="h-3 w-3 opacity-40" />
                      )}
                    </div>
                  </TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedRecords.map((fdr) => (
                  <TableRow
                    key={fdr.id}
                    onClick={() => navigate(`/fdrs/${fdr.id}`)}
                    className="cursor-pointer hover:bg-muted/50 transition-colors"
                  >
                    <TableCell className="font-semibold text-xs text-primary font-mono">
                      {fdr.internal_reference}
                    </TableCell>
                    <TableCell>
                      <div className="text-xs font-medium text-foreground">
                        {fdr.institution_name}
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        {fdr.institution_code || 'Institution'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-xs font-semibold text-foreground">
                        {fdr.bank_name}
                      </div>
                      <div className="text-[11px] font-mono text-muted-foreground">
                        {fdr.fdr_number}
                      </div>
                    </TableCell>
                    <TableCell className="font-semibold text-xs text-foreground">
                      {formatCurrency(fdr.deposit_amount, fdr.currency)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(fdr.issue_date)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(fdr.maturity_date)}
                    </TableCell>
                    <TableCell>{getStatusBadge(fdr.status)}</TableCell>
                    <TableCell>{getVerificationBadge(fdr.verification_status)}</TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-1">
                        <Badge
                          variant={
                            fdr.review_priority_score >= 80
                              ? 'destructive'
                              : fdr.review_priority_score >= 50
                              ? 'warning'
                              : 'secondary'
                          }
                          className="font-mono text-[10px] px-1.5"
                        >
                          {fdr.review_priority_score}
                        </Badge>
                        {fdr.has_potential_duplicate && (
                          <AlertTriangle className="h-3.5 w-3.5 text-destructive" />
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate(`/fdrs/${fdr.id}`)}
                        className="h-8 px-2 text-xs"
                      >
                        <Eye className="h-3.5 w-3.5 mr-1" />
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t px-4 py-3 sm:px-6">
            <div className="text-xs text-muted-foreground">
              Page <span className="font-medium text-foreground">{currentPage}</span> of{' '}
              <span className="font-medium text-foreground">{totalPages}</span>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                disabled={currentPage === 1}
                className="text-xs h-8"
              >
                Previous
              </Button>
              {Array.from({ length: totalPages }).map((_, idx) => {
                const pageNum = idx + 1;
                return (
                  <Button
                    key={pageNum}
                    variant={currentPage === pageNum ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setCurrentPage(pageNum)}
                    className="h-8 w-8 text-xs p-0 hidden sm:inline-flex"
                  >
                    {pageNum}
                  </Button>
                );
              })}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="text-xs h-8"
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};

export default FDRRecordsPage;
