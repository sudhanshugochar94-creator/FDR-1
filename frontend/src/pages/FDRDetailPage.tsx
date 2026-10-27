import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FileText, Shield, CheckCircle, Clock, RefreshCw, Download, MessageSquare, Bot, ArrowLeft, Loader2, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { useAuth } from '@/hooks/useAuth';
import api from '@/lib/api';
import { useState } from 'react';

const STATUS_COLORS: Record<string, string> = {
  DRAFT: 'bg-gray-100 text-gray-800',
  SUBMITTED: 'bg-blue-100 text-blue-800',
  EXTRACTED: 'bg-indigo-100 text-indigo-800',
  VALIDATED: 'bg-purple-100 text-purple-800',
  UNDER_REVIEW: 'bg-yellow-100 text-yellow-800',
  VERIFIED: 'bg-green-100 text-green-800',
  ACTIVE: 'bg-emerald-100 text-emerald-800',
  RENEWAL_PENDING: 'bg-orange-100 text-orange-800',
  RELEASED: 'bg-teal-100 text-teal-800',
  REJECTED: 'bg-red-100 text-red-800',
  CORRECTION_REQUESTED: 'bg-amber-100 text-amber-800',
};

const LIFECYCLE_STEPS = ['SUBMITTED', 'EXTRACTED', 'VALIDATED', 'UNDER_REVIEW', 'VERIFIED', 'ACTIVE'];

export default function FDRDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [verifyNotes, setVerifyNotes] = useState('');
  const [observationText, setObservationText] = useState('');
  const [caseSummary, setCaseSummary] = useState<any>(null);

  const { data: fdr, isLoading, error } = useQuery({
    queryKey: ['fdr', id],
    queryFn: async () => {
      const resp = await api.get(`/api/fdrs/${id}`);
      return resp.data;
    },
    enabled: !!id,
  });

  // Verify mutation
  const verifyMutation = useMutation({
    mutationFn: async (result: string) => {
      const resp = await api.post(`/api/fdrs/${id}/verify`, {
        verification_type: 'DOCUMENT_CHECK',
        result,
        notes: verifyNotes,
        evidence_summary: `Verified by ${user?.full_name}`,
      });
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fdr', id] });
      setVerifyNotes('');
    },
  });

  // Add observation
  const observationMutation = useMutation({
    mutationFn: async (type: string) => {
      const resp = await api.post(`/api/fdrs/${id}/observations`, {
        observation_type: type,
        content: observationText,
      });
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fdr', id] });
      setObservationText('');
    },
  });

  // AI Case Summary
  const summarizeMutation = useMutation({
    mutationFn: async () => {
      const resp = await api.post('/api/ai/summarize-case', { fdr_id: id });
      return resp.data;
    },
    onSuccess: (data) => setCaseSummary(data),
  });

  const agentRunsQuery = useQuery({
    queryKey: ['agent-runs', id],
    queryFn: async () => {
      const resp = await api.get(`/api/ai/agents/${id}/runs`);
      return resp.data;
    },
    enabled: !!id,
  });

  const agentCatalogQuery = useQuery({
    queryKey: ['agent-catalog'],
    queryFn: async () => {
      const resp = await api.get('/api/ai/agents/catalog');
      return resp.data;
    },
  });

  const runAgentsMutation = useMutation({
    mutationFn: async () => {
      const resp = await api.post(`/api/ai/agents/${id}/run`, undefined, { timeout: 70000 });
      return resp.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agent-runs', id] }),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (error || !fdr) {
    return (
      <Card><CardContent className="py-8 text-center">
        <XCircle className="h-12 w-12 mx-auto text-destructive mb-4" />
        <p className="text-lg font-medium">FDR Not Found</p>
        <p className="text-muted-foreground mb-4">The requested FDR record could not be loaded.</p>
        <Button onClick={() => navigate('/fdrs')}>Back to Records</Button>
      </CardContent></Card>
    );
  }

  const isReviewer = user?.role === 'reviewer' || user?.role === 'admin' || user?.role === 'approving_authority';
  const currentStepIndex = LIFECYCLE_STEPS.indexOf(fdr.status);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/fdrs')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{fdr.internal_reference}</h1>
            <p className="text-muted-foreground">{fdr.institution_name} — {fdr.bank_name}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Badge className={STATUS_COLORS[fdr.status] || 'bg-gray-100'}>{fdr.status.replace(/_/g, ' ')}</Badge>
          <Badge variant={fdr.verification_status === 'VERIFIED' ? 'default' : 'secondary'}>
            {fdr.verification_status}
          </Badge>
          {fdr.has_potential_duplicate && <Badge variant="destructive">⚠ Duplicate Flag</Badge>}
        </div>
      </div>

      {/* Lifecycle Timeline */}
      <Card>
        <CardHeader><CardTitle className="text-sm">Lifecycle Progress</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            {LIFECYCLE_STEPS.map((step, i) => (
              <div key={step} className="flex items-center">
                <div className={`flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold ${
                  i <= currentStepIndex ? 'bg-primary text-primary-foreground' :
                  fdr.status === 'REJECTED' ? 'bg-red-100 text-red-600' :
                  'bg-muted text-muted-foreground'
                }`}>
                  {i <= currentStepIndex ? '✓' : i + 1}
                </div>
                <span className="ml-1 text-xs hidden lg:inline">{step.replace(/_/g, ' ')}</span>
                {i < LIFECYCLE_STEPS.length - 1 && (
                  <div className={`w-12 h-0.5 mx-1 ${i < currentStepIndex ? 'bg-primary' : 'bg-muted'}`} />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Tabs defaultValue="details" className="space-y-4">
        <TabsList>
          <TabsTrigger value="details">Details</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
          <TabsTrigger value="validation">Validation</TabsTrigger>
          <TabsTrigger value="duplicates">Duplicates</TabsTrigger>
          <TabsTrigger value="verification">Verification</TabsTrigger>
          <TabsTrigger value="agents">AI Agents</TabsTrigger>
          <TabsTrigger value="lifecycle">Lifecycle</TabsTrigger>
          <TabsTrigger value="audit">Audit</TabsTrigger>
        </TabsList>

        {/* Details Tab */}
        <TabsContent value="details">
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[
                  { label: 'Internal Reference', value: fdr.internal_reference },
                  { label: 'Application Number', value: fdr.application_number || '—' },
                  { label: 'Bank Name', value: fdr.bank_name },
                  { label: 'Branch', value: fdr.branch_name || '—' },
                  { label: 'FDR Number', value: fdr.fdr_number },
                  { label: 'Deposit Amount', value: `₹${Number(fdr.deposit_amount).toLocaleString('en-IN')} ${fdr.currency}` },
                  { label: 'Issue Date', value: fdr.issue_date },
                  { label: 'Maturity Date', value: fdr.maturity_date },
                  { label: 'Review Priority', value: `${fdr.review_priority_score}/100` },
                  { label: 'Compliance Reference', value: fdr.compliance_reference || '—' },
                ].map(item => (
                  <div key={item.label} className="space-y-1">
                    <p className="text-xs text-muted-foreground font-medium">{item.label}</p>
                    <p className="text-sm font-medium">{item.value}</p>
                  </div>
                ))}
              </div>
              {fdr.review_priority_reasons?.length > 0 && (
                <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
                  <p className="text-sm font-medium mb-1">Priority Reasons:</p>
                  <ul className="list-disc list-inside text-sm text-muted-foreground">
                    {fdr.review_priority_reasons.map((r: string, i: number) => <li key={i}>{r}</li>)}
                  </ul>
                </div>
              )}
              {fdr.notes && <div className="mt-4"><p className="text-xs text-muted-foreground">Notes</p><p className="text-sm">{fdr.notes}</p></div>}

              {/* AI Summary */}
              <Separator className="my-4" />
              <div className="flex items-center gap-2 mb-2">
                <Bot className="h-4 w-4 text-primary" />
                <span className="font-medium text-sm">AI Case Summary</span>
                <Button variant="outline" size="sm" onClick={() => summarizeMutation.mutate()} disabled={summarizeMutation.isPending}>
                  {summarizeMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Generate'}
                </Button>
              </div>
              {caseSummary && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm space-y-2">
                  <p><strong>Status:</strong> {caseSummary.current_status} | <strong>Verification:</strong> {caseSummary.verification_status}</p>
                  <p><strong>Next Step:</strong> {caseSummary.pending_next_step}</p>
                  {caseSummary.unresolved_issues?.length > 0 && (
                    <div><strong>Issues:</strong> {caseSummary.unresolved_issues.join(', ')}</div>
                  )}
                  {caseSummary.ai_narrative && (
                    <div className="italic text-muted-foreground border-t pt-2 mt-2">
                      <span className="text-xs font-medium text-blue-600">AI-Generated:</span> {caseSummary.ai_narrative}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Documents Tab */}
        <TabsContent value="documents">
          <Card>
            <CardContent className="pt-6 space-y-3">
              {fdr.documents?.length === 0 ? (
                <p className="text-center text-muted-foreground py-4">No documents uploaded yet.</p>
              ) : (
                fdr.documents?.map((doc: any) => (
                  <div key={doc.id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <FileText className="h-8 w-8 text-primary" />
                      <div>
                        <p className="font-medium text-sm">{doc.original_filename}</p>
                        <p className="text-xs text-muted-foreground">
                          {doc.upload_type} • {(doc.file_size / 1024).toFixed(1)} KB • SHA-256: {doc.file_hash_sha256?.substring(0, 16)}...
                        </p>
                      </div>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => window.open(`${api.defaults.baseURL}/api/documents/${doc.id}/download`, '_blank')}>
                      <Download className="h-4 w-4 mr-1" /> Download
                    </Button>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Validation Tab */}
        <TabsContent value="validation">
          <Card>
            <CardContent className="pt-6 space-y-3">
              {fdr.validation_findings?.length === 0 ? (
                <p className="text-center text-muted-foreground py-4">No validation findings.</p>
              ) : (
                fdr.validation_findings?.map((f: any) => (
                  <div key={f.id} className={`p-3 rounded-lg border ${
                    f.severity === 'CRITICAL' ? 'bg-red-50 border-red-200' :
                    f.severity === 'WARNING' ? 'bg-yellow-50 border-yellow-200' :
                    'bg-green-50 border-green-200'
                  }`}>
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex gap-2 mb-1">
                          <Badge variant={f.severity === 'CRITICAL' ? 'destructive' : 'secondary'} className="text-xs">{f.severity}</Badge>
                          <Badge variant="outline" className="text-xs">{f.finding_type}</Badge>
                        </div>
                        <p className="text-sm font-medium">{f.field_name}</p>
                        <p className="text-sm text-muted-foreground">{f.description}</p>
                      </div>
                    </div>
                    {f.submitted_value && f.extracted_value && (
                      <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                        <div className="bg-white/50 p-2 rounded"><strong>Submitted:</strong> {f.submitted_value}</div>
                        <div className="bg-white/50 p-2 rounded"><strong>Extracted:</strong> {f.extracted_value}</div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Duplicates Tab */}
        <TabsContent value="duplicates">
          <Card>
            <CardContent className="pt-6 space-y-3">
              {fdr.duplicate_candidates?.length === 0 ? (
                <div className="text-center py-4">
                  <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2" />
                  <p className="text-muted-foreground">No duplicate candidates detected.</p>
                </div>
              ) : (
                fdr.duplicate_candidates?.map((dc: any) => (
                  <div key={dc.id} className="p-4 border rounded-lg bg-red-50/50">
                    <div className="flex items-center justify-between mb-2">
                      <Badge variant="destructive">Match Score: {(dc.match_score * 100).toFixed(0)}%</Badge>
                      <Badge variant="outline">{dc.status}</Badge>
                    </div>
                    {dc.match_reasons && (
                      <ul className="text-sm list-disc list-inside mb-2">
                        {(Array.isArray(dc.match_reasons) ? dc.match_reasons : []).map((r: string, i: number) => <li key={i}>{r}</li>)}
                      </ul>
                    )}
                    {dc.matching_fields && (
                      <div className="text-xs"><strong>Matching:</strong> {JSON.stringify(dc.matching_fields)}</div>
                    )}
                    {dc.differing_fields && Object.keys(dc.differing_fields).length > 0 && (
                      <div className="text-xs mt-1"><strong>Differing:</strong> {JSON.stringify(dc.differing_fields)}</div>
                    )}
                    {dc.file_hash_match && <Badge variant="destructive" className="mt-1 text-xs">Identical File Hash</Badge>}
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Verification Tab */}
        <TabsContent value="verification">
          <Card>
            <CardContent className="pt-6 space-y-4">
              {/* Existing verifications */}
              {fdr.verification_records?.map((vr: any) => (
                <div key={vr.id} className={`p-3 rounded-lg border ${
                  vr.result === 'VERIFIED' ? 'bg-green-50 border-green-200' :
                  vr.result === 'REJECTED' ? 'bg-red-50 border-red-200' :
                  'bg-yellow-50 border-yellow-200'
                }`}>
                  <div className="flex items-center gap-2 mb-1">
                    <Shield className="h-4 w-4" />
                    <Badge>{vr.result}</Badge>
                    <span className="text-xs text-muted-foreground">{vr.verification_type}</span>
                    {vr.verification_type === 'BANK_CONFIRMATION' && (
                      <Badge variant="outline">MANUALLY ENTERED — NOT LIVE BANK VERIFICATION</Badge>
                    )}
                  </div>
                  {vr.notes && <p className="text-sm">{vr.notes}</p>}
                  <p className="text-xs text-muted-foreground mt-1">at {new Date(vr.created_at).toLocaleString()}</p>
                </div>
              ))}

              <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">
                No live bank integration is configured. A BANK_CONFIRMATION record entered here is a
                manual/demo record and does not mean the bank was contacted.
              </div>

              {/* Observations */}
              <Separator />
              <h4 className="font-medium">Review Observations</h4>
              {fdr.review_observations?.map((obs: any) => (
                <div key={obs.id} className="p-2 bg-muted/50 rounded text-sm">
                  <Badge variant="outline" className="text-xs mb-1">{obs.observation_type}</Badge>
                  <p>{obs.content}</p>
                  <p className="text-xs text-muted-foreground mt-1">{new Date(obs.created_at).toLocaleString()}</p>
                </div>
              ))}

              {/* Reviewer actions */}
              {isReviewer && (
                <div className="border-t pt-4 space-y-3">
                  <h4 className="font-medium">Reviewer Actions</h4>
                  <Textarea
                    placeholder="Verification notes or observation..."
                    value={verifyNotes || observationText}
                    onChange={e => { setVerifyNotes(e.target.value); setObservationText(e.target.value); }}
                  />
                  <div className="flex gap-2 flex-wrap">
                    <Button size="sm" onClick={() => verifyMutation.mutate('VERIFIED')} disabled={verifyMutation.isPending}>
                      <CheckCircle className="h-4 w-4 mr-1" /> Verify
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => verifyMutation.mutate('REJECTED')} disabled={verifyMutation.isPending}>
                      <XCircle className="h-4 w-4 mr-1" /> Reject
                    </Button>
                    <Button size="sm" variant="secondary" onClick={() => verifyMutation.mutate('NEEDS_INFO')} disabled={verifyMutation.isPending}>
                      Request Info
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => observationMutation.mutate('NOTE')} disabled={observationMutation.isPending || !observationText}>
                      <MessageSquare className="h-4 w-4 mr-1" /> Add Note
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => observationMutation.mutate('CORRECTION_REQUEST')} disabled={observationMutation.isPending || !observationText}>
                      Request Correction
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* AI Agents Tab */}
        <TabsContent value="agents">
          <div className="space-y-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Bot className="h-5 w-5" /> Coordinated workflow agents
                  </CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">
                    Runs automatically after document upload. You can also request a fresh review.
                  </p>
                </div>
                <Button
                  onClick={() => runAgentsMutation.mutate()}
                  disabled={runAgentsMutation.isPending}
                >
                  {runAgentsMutation.isPending
                    ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Running agents</>
                    : <><Bot className="h-4 w-4 mr-2" /> Run agents</>}
                </Button>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">
                  Agents only provide recommendations. Authorized people retain all verification,
                  compliance, approval, and release decisions. No live bank connection is configured;
                  bank confirmation records are manually entered and are not live verification.
                </div>
                {runAgentsMutation.isError && (
                  <p role="alert" className="text-sm text-destructive">
                    Could not confirm that the workflow completed. Check saved results before retrying.
                  </p>
                )}
                {agentRunsQuery.isError && (
                  <p role="alert" className="text-sm text-destructive">
                    Could not load saved agent results.
                  </p>
                )}
                {agentCatalogQuery.isError && (
                  <p role="alert" className="text-sm text-destructive">
                    Could not load the agent capability list.
                  </p>
                )}
                {agentRunsQuery.isLoading ? (
                  <Skeleton className="h-24 w-full" />
                ) : agentRunsQuery.data?.[0] ? (
                  <>
                    <div className="rounded-md bg-muted/50 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="font-medium">Workflow summary</p>
                        <Badge variant="outline">
                          {agentRunsQuery.data[0].ai_generated
                            ? `Local Ollama • ${agentRunsQuery.data[0].ai_model}`
                            : 'Rule-based summary'}
                        </Badge>
                      </div>
                      <p className="text-sm mt-2">{agentRunsQuery.data[0].ai_summary}</p>
                      <p className="text-xs text-muted-foreground mt-2">
                        Saved {new Date(agentRunsQuery.data[0].created_at).toLocaleString()}.
                        Human review is required; no decisions were made.
                      </p>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2">
                      {agentRunsQuery.data[0].agents.map((agent: any) => (
                        <Card key={agent.agent_id}>
                          <CardHeader className="pb-2">
                            <div className="flex items-center justify-between gap-2">
                              <CardTitle className="text-sm">{agent.name}</CardTitle>
                              <Badge variant={agent.status === 'attention' ? 'destructive' : 'secondary'}>
                                {agent.status}
                              </Badge>
                            </div>
                          </CardHeader>
                          <CardContent className="space-y-2 text-sm">
                            <ul className="list-disc pl-5 space-y-1">
                              {agent.findings.map((finding: string, index: number) => (
                                <li key={index}>{finding}</li>
                              ))}
                            </ul>
                            {agent.recommendations.length > 0 && (
                              <div>
                                <p className="font-medium">Recommended next steps</p>
                                <ul className="list-disc pl-5 text-muted-foreground">
                                  {agent.recommendations.map((recommendation: string, index: number) => (
                                    <li key={index}>{recommendation}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {agent.evidence.length > 0 && (
                              <p className="text-xs text-muted-foreground">
                                Evidence: {agent.evidence.join(' ')}
                              </p>
                            )}
                            {agent.simulated && (
                              <Badge variant="outline">Manual/demo workflow only</Badge>
                            )}
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No agent run has been saved for this record yet. Run agents to create a review.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="text-base">Implemented and planned capabilities</CardTitle></CardHeader>
              <CardContent className="grid gap-3 md:grid-cols-2">
                {agentCatalogQuery.data?.map((agent: any) => (
                  <div key={agent.id} className="rounded-md border p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium text-sm">{agent.name}</p>
                      <Badge variant={agent.implemented ? 'default' : 'outline'}>
                        {agent.implemented ? 'Implemented' : 'Planned'}
                      </Badge>
                    </div>
                    {agent.implemented_features?.length > 0 && (
                      <p className="mt-2 text-xs text-muted-foreground">
                        Available: {agent.implemented_features.join(' ')}
                      </p>
                    )}
                    {agent.planned_features?.length > 0 && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Planned: {agent.planned_features.join(' ')}
                      </p>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Lifecycle Tab */}
        <TabsContent value="lifecycle">
          <Card>
            <CardContent className="pt-6 space-y-4">
              <h4 className="font-medium">Lifecycle Relationships</h4>
              {(fdr.parent_lifecycle_links?.length === 0 && fdr.child_lifecycle_links?.length === 0) ? (
                <p className="text-muted-foreground text-sm">No lifecycle relationships.</p>
              ) : (
                <>
                  {fdr.parent_lifecycle_links?.map((l: any) => (
                    <div key={l.id} className="p-3 bg-muted/50 rounded flex items-center gap-2">
                      <RefreshCw className="h-4 w-4" />
                      <span className="text-sm">{l.relationship_type}: Parent FDR {l.parent_fdr_id.substring(0, 8)}...</span>
                    </div>
                  ))}
                  {fdr.child_lifecycle_links?.map((l: any) => (
                    <div key={l.id} className="p-3 bg-muted/50 rounded flex items-center gap-2">
                      <RefreshCw className="h-4 w-4" />
                      <span className="text-sm">{l.relationship_type}: Child FDR {l.child_fdr_id.substring(0, 8)}...</span>
                    </div>
                  ))}
                </>
              )}

              <Separator />
              <h4 className="font-medium">Renewal Requests</h4>
              {fdr.renewal_requests?.length === 0 ? (
                <p className="text-muted-foreground text-sm">No renewal requests.</p>
              ) : (
                fdr.renewal_requests?.map((r: any) => (
                  <div key={r.id} className="p-3 bg-muted/50 rounded">
                    <Badge>{r.status}</Badge>
                    <p className="text-sm mt-1">{r.review_notes || 'Pending'}</p>
                  </div>
                ))
              )}

              <Separator />
              <h4 className="font-medium">Release Requests</h4>
              {fdr.release_requests?.length === 0 ? (
                <p className="text-muted-foreground text-sm">No release requests.</p>
              ) : (
                fdr.release_requests?.map((r: any) => (
                  <div key={r.id} className="p-3 bg-muted/50 rounded">
                    <Badge variant={r.status === 'APPROVED' ? 'default' : r.status === 'REJECTED' ? 'destructive' : 'secondary'}>{r.status}</Badge>
                    <p className="text-sm mt-1">{r.reason}</p>
                    {r.approver_notes && <p className="text-xs text-muted-foreground mt-1">Decision: {r.approver_notes}</p>}
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Audit Tab */}
        <TabsContent value="audit">
          <AuditSection fdrId={id!} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function AuditSection({ fdrId }: { fdrId: string }) {
  const { data: events, isLoading } = useQuery({
    queryKey: ['audit', fdrId],
    queryFn: async () => {
      const resp = await api.get('/api/audit', { params: { entity_id: fdrId, limit: 50 } });
      return resp.data;
    },
  });

  if (isLoading) return <Skeleton className="h-32" />;

  return (
    <Card>
      <CardContent className="pt-6">
        {events?.length === 0 ? (
          <p className="text-muted-foreground text-center py-4">No audit events for this record.</p>
        ) : (
          <div className="space-y-2">
            {events?.map((e: any) => (
              <div key={e.id} className="flex items-start gap-3 p-2 border-b last:border-0">
                <Clock className="h-4 w-4 mt-1 text-muted-foreground flex-shrink-0" />
                <div>
                  <p className="text-sm"><strong>{e.action}</strong> by <Badge variant="outline" className="text-xs">{e.role}</Badge></p>
                  {e.reason && <p className="text-xs text-muted-foreground">{e.reason}</p>}
                  <p className="text-xs text-muted-foreground">{new Date(e.timestamp).toLocaleString()}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
