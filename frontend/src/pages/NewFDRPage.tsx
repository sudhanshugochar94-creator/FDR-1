import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { FileText, Upload, Search, CheckCircle, Send, ArrowLeft, ArrowRight, AlertTriangle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import api from '@/lib/api';
import type { FDRInstrument, ExtractionResult, ValidationFinding } from '@/types';

interface UploadedDocument {
  id: string;
  original_filename: string;
  file_hash_sha256: string;
  file_size: number;
}

interface FDRDetail {
  validation_findings?: ValidationFinding[];
}

function getApiError(error: unknown): string {
  if (typeof error !== 'object' || error === null || !('response' in error)) {
    return error instanceof Error ? error.message : 'The request failed.';
  }
  const response = error.response;
  if (typeof response !== 'object' || response === null || !('data' in response)) {
    return 'The request failed.';
  }
  const data = response.data;
  if (typeof data === 'object' && data !== null) {
    if ('detail' in data && typeof data.detail === 'string') return data.detail;
    if ('error' in data && typeof data.error === 'object' && data.error !== null && 'message' in data.error && typeof data.error.message === 'string') {
      return data.error.message;
    }
  }
  return 'The request failed.';
}

const fdrSchema = z.object({
  bank_name: z.string().min(2, 'Bank name is required'),
  branch_name: z.string().optional(),
  fdr_number: z.string().min(2, 'FDR number is required'),
  deposit_amount: z.coerce.number().positive('Amount must be positive'),
  currency: z.string().default('INR'),
  issue_date: z.string().min(1, 'Issue date is required'),
  maturity_date: z.string().min(1, 'Maturity date is required'),
  application_number: z.string().optional(),
  compliance_reference: z.string().optional(),
  notes: z.string().optional(),
});

type FDRFormData = z.infer<typeof fdrSchema>;

const STEPS = [
  { id: 1, title: 'Instrument Details', icon: FileText },
  { id: 2, title: 'Upload Document', icon: Upload },
  { id: 3, title: 'Extract Information', icon: Search },
  { id: 4, title: 'Review Findings', icon: AlertTriangle },
  { id: 5, title: 'Submit', icon: Send },
];

export default function NewFDRPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [createdFDR, setCreatedFDR] = useState<FDRInstrument | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadedDocument | null>(null);
  const [extractions, setExtractions] = useState<ExtractionResult[]>([]);
  const [findings, setFindings] = useState<ValidationFinding[]>([]);
  const [extractionError, setExtractionError] = useState<string | null>(null);

  const form = useForm<FDRFormData>({
    resolver: zodResolver(fdrSchema),
    defaultValues: { currency: 'INR' },
  });

  // Step 1: Create FDR
  const createMutation = useMutation({
    mutationFn: async (data: FDRFormData) => {
      const resp = await api.post('/api/fdrs', data);
      return resp.data;
    },
    onSuccess: (data) => {
      setCreatedFDR(data);
      setStep(2);
    },
  });

  // Step 2: Upload document
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('upload_type', 'ORIGINAL');
      const resp = await api.post(`/api/fdrs/${createdFDR!.id}/documents`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return resp.data;
    },
    onSuccess: async (data) => {
      setUploadResult(data);
      setStep(3);
      await fetchExtractions(data.id);
    },
  });

  // Step 3: Fetch extractions
  const fetchExtractions = async (documentId: string) => {
    if (!createdFDR) return;
    setExtractionError(null);
    try {
      const [extractionResponse, fdrResponse] = await Promise.all([
        api.get<ExtractionResult[]>(`/api/documents/${documentId}/extractions`),
        api.get<FDRDetail>(`/api/fdrs/${createdFDR.id}`),
      ]);
      setExtractions(extractionResponse.data);
      setFindings(fdrResponse.data.validation_findings || []);
      setStep(4);
    } catch (error) {
      setExtractionError(getApiError(error));
    }
  };

  // Step 5: Final submit
  const submitMutation = useMutation({
    mutationFn: async () => {
      const resp = await api.patch(`/api/fdrs/${createdFDR!.id}`, { status: 'SUBMITTED' });
      return resp.data;
    },
    onSuccess: () => {
      navigate(`/fdrs/${createdFDR!.id}`);
    },
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const allowed = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
      if (!allowed.includes(file.type)) {
        alert('Only PDF, JPG, JPEG, and PNG files are allowed.');
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        alert('File size must be under 10MB.');
        return;
      }
      setSelectedFile(file);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Submit New FDR</h1>
        <p className="text-muted-foreground">Follow the steps to submit a Fixed Deposit Receipt for verification.</p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center gap-2">
        {STEPS.map((s, i) => (
          <div key={s.id} className="flex items-center gap-2">
            <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium ${
              step === s.id ? 'bg-primary text-primary-foreground' :
              step > s.id ? 'bg-green-100 text-green-800' : 'bg-muted text-muted-foreground'
            }`}>
              <s.icon className="h-4 w-4" />
              <span className="hidden sm:inline">{s.title}</span>
              <span className="sm:hidden">{s.id}</span>
            </div>
            {i < STEPS.length - 1 && <div className="w-8 h-0.5 bg-muted" />}
          </div>
        ))}
      </div>

      <Progress value={(step / STEPS.length) * 100} className="h-2" />

      {/* Step 1: Instrument Details */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Step 1: Instrument Details</CardTitle>
            <CardDescription>Enter the FDR instrument information as shown on the certificate.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={form.handleSubmit((data) => createMutation.mutate(data))} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="bank_name">Bank Name *</Label>
                  <Input id="bank_name" {...form.register('bank_name')} placeholder="e.g., State Bank of India" />
                  {form.formState.errors.bank_name && (
                    <p className="text-sm text-destructive">{form.formState.errors.bank_name.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="branch_name">Branch</Label>
                  <Input id="branch_name" {...form.register('branch_name')} placeholder="e.g., Main Branch, Delhi" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fdr_number">FDR / Instrument Number *</Label>
                  <Input id="fdr_number" {...form.register('fdr_number')} placeholder="e.g., FD-2026-SBI-001234" />
                  {form.formState.errors.fdr_number && (
                    <p className="text-sm text-destructive">{form.formState.errors.fdr_number.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="deposit_amount">Deposit Amount (₹) *</Label>
                  <Input id="deposit_amount" type="number" step="0.01" {...form.register('deposit_amount')} placeholder="e.g., 5000000" />
                  {form.formState.errors.deposit_amount && (
                    <p className="text-sm text-destructive">{form.formState.errors.deposit_amount.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="issue_date">Issue Date *</Label>
                  <Input id="issue_date" type="date" {...form.register('issue_date')} />
                  {form.formState.errors.issue_date && (
                    <p className="text-sm text-destructive">{form.formState.errors.issue_date.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="maturity_date">Maturity Date *</Label>
                  <Input id="maturity_date" type="date" {...form.register('maturity_date')} />
                  {form.formState.errors.maturity_date && (
                    <p className="text-sm text-destructive">{form.formState.errors.maturity_date.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="application_number">Application / Reference Number</Label>
                  <Input id="application_number" {...form.register('application_number')} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="compliance_reference">Compliance Reference</Label>
                  <Input id="compliance_reference" {...form.register('compliance_reference')} />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="notes">Notes</Label>
                <Textarea id="notes" {...form.register('notes')} placeholder="Any additional information..." rows={3} />
              </div>
              <div className="flex justify-end">
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? (
                    <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Creating...</>
                  ) : (
                    <>Next: Upload Document <ArrowRight className="h-4 w-4 ml-2" /></>
                  )}
                </Button>
              </div>
              {createMutation.isError && (
                <p className="text-sm text-destructive">Error: {(createMutation.error as any)?.response?.data?.detail || 'Failed to create FDR'}</p>
              )}
            </form>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Upload Document */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Step 2: Upload FDR Document</CardTitle>
            <CardDescription>Upload the scanned FDR certificate or receipt (PDF, JPG, PNG, max 10MB).</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {createdFDR && (
              <div className="bg-green-50 border border-green-200 p-3 rounded-lg">
                <p className="text-sm text-green-800">
                  <CheckCircle className="h-4 w-4 inline mr-1" />
                  FDR record <strong>{createdFDR.internal_reference}</strong> created successfully.
                </p>
              </div>
            )}
            <div className="border-2 border-dashed border-muted rounded-lg p-8 text-center">
              <Upload className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-sm text-muted-foreground mb-4">Drag & drop your file here, or click to browse</p>
              <Input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={handleFileSelect} className="max-w-xs mx-auto" />
              {selectedFile && (
                <p className="mt-2 text-sm text-green-600">Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</p>
              )}
            </div>
            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep(1)}>
                <ArrowLeft className="h-4 w-4 mr-2" /> Back
              </Button>
              <Button
                onClick={() => selectedFile && uploadMutation.mutate(selectedFile)}
                disabled={!selectedFile || uploadMutation.isPending}
              >
                {uploadMutation.isPending ? (
                  <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Uploading & Processing...</>
                ) : (
                  <>Upload & Extract <ArrowRight className="h-4 w-4 ml-2" /></>
                )}
              </Button>
            </div>
            {uploadMutation.isError && (
              <p className="text-sm text-destructive">Upload failed: {getApiError(uploadMutation.error)}</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Step 3: Extraction Progress */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle>Step 3: Extracting Information</CardTitle>
            <CardDescription>The upload API extracts the document, validates its fields, and checks for duplicate candidates.</CardDescription>
          </CardHeader>
          <CardContent className="text-center py-8">
            {extractionError ? (
              <div className="space-y-4">
                <p className="text-sm text-destructive">The document was uploaded, but the extraction results could not be loaded: {extractionError}</p>
                <Button variant="outline" disabled={!uploadResult} onClick={() => uploadResult && void fetchExtractions(uploadResult.id)}>
                  Retry loading results
                </Button>
              </div>
            ) : (
              <>
                <Loader2 className="h-12 w-12 mx-auto animate-spin text-primary mb-4" />
                <p>{uploadMutation.isPending ? 'Uploading, extracting, and checking for duplicates…' : 'Loading extraction and validation results…'}</p>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Step 4: Review Findings */}
      {step === 4 && (
        <Card>
          <CardHeader>
            <CardTitle>Step 4: Review Findings</CardTitle>
            <CardDescription>Compare extracted information with submitted values. Correct any discrepancies before final submission.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Extraction Results */}
            {extractions.length > 0 && (
              <div>
                <h3 className="font-semibold mb-3">Extracted Fields</h3>
                {extractions[0]?.ai_model_used === 'tesseract-unavailable' && (
                  <p role="alert" className="mb-3 rounded-md border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-900">
                    This looks like a scanned document, but Tesseract OCR is not installed. Upload a text-based PDF or install Tesseract to extract scanned receipts.
                  </p>
                )}
                {extractions[0]?.ai_model_used === 'ocr-dependency-unavailable' && (
                  <p role="alert" className="mb-3 rounded-md border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-900">
                    OCR support is not installed in the backend environment. Install the backend OCR dependencies to process scanned receipts.
                  </p>
                )}
                {extractions[0]?.ai_model_used === 'pdf-rasterizer-unavailable' && (
                  <p role="alert" className="mb-3 rounded-md border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-900">
                    This PDF contains no selectable text and PDF page rendering is unavailable, so scanned text could not be read.
                  </p>
                )}
                {extractions[0]?.ai_model_used === 'pdf-text-extractor-unavailable' && (
                  <p role="alert" className="mb-3 rounded-md border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-900">
                    PDF text extraction is unavailable in the backend environment.
                  </p>
                )}
                <div className="bg-muted/50 rounded-lg p-4">
                  {Object.entries(extractions[0]?.extracted_fields || {}).map(([key, value]) => (
                    <div key={key} className="flex justify-between py-1 border-b border-muted last:border-0">
                      <span className="text-sm font-medium capitalize">{key.replace(/_/g, ' ')}</span>
                      <span className="text-sm">{String(value)}</span>
                    </div>
                  ))}
                </div>
                {extractions[0]?.confidence_scores && (
                  <div className="mt-2">
                    <h4 className="text-sm font-medium text-muted-foreground mb-1">Confidence Scores</h4>
                    <div className="flex gap-2 flex-wrap">
                      {Object.entries(extractions[0].confidence_scores).map(([key, score]) => (
                        <Badge key={key} variant={Number(score) > 0.8 ? 'default' : 'secondary'}>
                          {key}: {(Number(score) * 100).toFixed(0)}%
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            <Separator />

            {/* Validation Findings */}
            {findings.length > 0 && (
              <div>
                <h3 className="font-semibold mb-3">Validation Findings</h3>
                <div className="space-y-2">
                  {findings.map((f) => (
                    <div key={f.id} className={`p-3 rounded-lg border ${
                      f.severity === 'CRITICAL' ? 'bg-red-50 border-red-200' :
                      f.severity === 'WARNING' ? 'bg-yellow-50 border-yellow-200' :
                      'bg-green-50 border-green-200'
                    }`}>
                      <div className="flex items-start gap-2">
                        <Badge variant={f.severity === 'CRITICAL' ? 'destructive' : f.severity === 'WARNING' ? 'secondary' : 'default'}>
                          {f.finding_type}
                        </Badge>
                        <div>
                          <p className="text-sm font-medium">{f.field_name}</p>
                          <p className="text-sm text-muted-foreground">{f.description}</p>
                          {f.submitted_value && f.extracted_value && f.finding_type === 'MISMATCH' && (
                            <div className="mt-1 text-xs">
                              <span className="text-red-600">Submitted: {f.submitted_value}</span>
                              {' → '}
                              <span className="text-blue-600">Extracted: {f.extracted_value}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {findings.length === 0 && extractions.length === 0 && (
              <div className="text-center py-4 text-muted-foreground">
                <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                <p>Document processed. No critical findings detected.</p>
              </div>
            )}

            {/* Document Info */}
            {uploadResult && (
              <div className="bg-muted/50 rounded-lg p-4">
                <h4 className="text-sm font-medium mb-2">Document Information</h4>
                <p className="text-xs text-muted-foreground">File: {uploadResult.original_filename}</p>
                <p className="text-xs text-muted-foreground">SHA-256: {uploadResult.file_hash_sha256}</p>
                <p className="text-xs text-muted-foreground">Size: {(uploadResult.file_size / 1024).toFixed(1)} KB</p>
              </div>
            )}

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep(2)}>
                <ArrowLeft className="h-4 w-4 mr-2" /> Back
              </Button>
              <Button onClick={() => setStep(5)}>
                Proceed to Submit <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 5: Final Submit */}
      {step === 5 && (
        <Card>
          <CardHeader>
            <CardTitle>Step 5: Confirm Submission</CardTitle>
            <CardDescription>Review the summary below and submit the FDR for verification.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {createdFDR && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-muted/50 p-4 rounded-lg">
                <div><span className="text-sm font-medium">Reference:</span> <span className="text-sm">{createdFDR.internal_reference}</span></div>
                <div><span className="text-sm font-medium">Bank:</span> <span className="text-sm">{createdFDR.bank_name}</span></div>
                <div><span className="text-sm font-medium">FDR Number:</span> <span className="text-sm">{createdFDR.fdr_number}</span></div>
                <div><span className="text-sm font-medium">Amount:</span> <span className="text-sm">₹{Number(createdFDR.deposit_amount).toLocaleString('en-IN')}</span></div>
                <div><span className="text-sm font-medium">Issue Date:</span> <span className="text-sm">{createdFDR.issue_date}</span></div>
                <div><span className="text-sm font-medium">Maturity Date:</span> <span className="text-sm">{createdFDR.maturity_date}</span></div>
              </div>
            )}

            {findings.some(f => f.severity === 'CRITICAL') && (
              <div className="bg-yellow-50 border border-yellow-200 p-3 rounded-lg">
                <p className="text-sm text-yellow-800">
                  <AlertTriangle className="h-4 w-4 inline mr-1" />
                  There are critical findings. The FDR will be marked for correction review.
                </p>
              </div>
            )}

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep(4)}>
                <ArrowLeft className="h-4 w-4 mr-2" /> Back to Review
              </Button>
              <Button onClick={() => submitMutation.mutate()} disabled={submitMutation.isPending}>
                {submitMutation.isPending ? (
                  <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Submitting...</>
                ) : (
                  <><Send className="h-4 w-4 mr-2" /> Submit FDR for Verification</>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
