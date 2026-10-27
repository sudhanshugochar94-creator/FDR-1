import React, { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Building2, UserRound, UserPlus } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Institution, User } from '@/types';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { toast } from '@/components/ui/toast';

interface InstitutionForm {
  name: string;
  code: string;
  city: string;
  state: string;
  contact_email: string;
}

const emptyForm: InstitutionForm = { name: '', code: '', city: '', state: '', contact_email: '' };

const UserManagementPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [form, setForm] = useState(emptyForm);
  const currentUser = useQuery({
    queryKey: ['current-user'],
    queryFn: async () => (await apiClient.get<User>('/api/auth/me')).data,
  });
  const institutions = useQuery({
    queryKey: ['institutions'],
    queryFn: async () => (await apiClient.get<Institution[]>('/api/institutions')).data,
  });
  const createInstitution = useMutation({
    mutationFn: async (payload: InstitutionForm) => (await apiClient.post<Institution>('/api/institutions', {
      ...payload,
      city: payload.city || null,
      state: payload.state || null,
      contact_email: payload.contact_email || null,
    })).data,
    onSuccess: () => {
      toast.success('Institution created');
      setForm(emptyForm);
      queryClient.invalidateQueries({ queryKey: ['institutions'] });
    },
    onError: () => toast.error('Could not create the institution. Check that its code is unique and try again.'),
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    createInstitution.mutate(form);
  };
  const user = currentUser.data;

  return (
    <div className="space-y-6 pb-10">
      <div><h1 className="text-2xl font-bold tracking-tight">Users & institutions</h1><p className="mt-1 text-sm text-muted-foreground">View your signed-in account and manage the institution directory.</p></div>
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><UserRound className="h-5 w-5 text-primary" />Signed-in account</CardTitle><CardDescription>Account details from the current authenticated session.</CardDescription></CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <div><p className="text-xs text-muted-foreground">Name</p><p className="font-medium">{user?.full_name ?? '—'}</p></div>
          <div><p className="text-xs text-muted-foreground">Email</p><p className="font-medium">{user?.email ?? '—'}</p></div>
          <div><p className="text-xs text-muted-foreground">Role</p><Badge variant="secondary">{user?.role.replace(/_/g, ' ') ?? 'Unknown'}</Badge></div>
          {user?.institution && <div className="sm:col-span-3"><p className="text-xs text-muted-foreground">Institution</p><p className="font-medium">{user.institution.name} <span className="text-sm text-muted-foreground">({user.institution.code})</span></p></div>}
        </CardContent>
      </Card>
      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle className="flex items-center gap-2"><UserPlus className="h-5 w-5 text-primary" />Add institution</CardTitle><CardDescription>Provision an institution directory entry. User creation and role assignment are not exposed by the current API.</CardDescription></CardHeader>
          <CardContent>
            {user?.role !== 'admin' ? <p className="rounded-md bg-muted p-3 text-sm text-muted-foreground">Institution creation is available to administrators only.</p> : <form className="space-y-3" onSubmit={submit}>
              <Input required minLength={2} maxLength={500} aria-label="Institution name" placeholder="Institution name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
              <Input required minLength={2} maxLength={50} aria-label="Institution code" placeholder="Institution code" value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value.toUpperCase() })} />
              <div className="grid grid-cols-2 gap-3"><Input aria-label="City" placeholder="City" value={form.city} onChange={(event) => setForm({ ...form, city: event.target.value })} /><Input aria-label="State" placeholder="State" value={form.state} onChange={(event) => setForm({ ...form, state: event.target.value })} /></div>
              <Input type="email" aria-label="Contact email" placeholder="Contact email (optional)" value={form.contact_email} onChange={(event) => setForm({ ...form, contact_email: event.target.value })} />
              <Button className="w-full" disabled={createInstitution.isPending}>{createInstitution.isPending ? 'Creating…' : 'Create institution'}</Button>
            </form>}
          </CardContent>
        </Card>
        <Card className="lg:col-span-3">
          <CardHeader><CardTitle className="flex items-center gap-2"><Building2 className="h-5 w-5 text-primary" />Institution directory</CardTitle><CardDescription>Institutions visible to compliance administrators and reviewers.</CardDescription></CardHeader>
          <CardContent>
            {institutions.isLoading ? <p className="py-8 text-center text-sm text-muted-foreground">Loading institutions…</p> : institutions.isError ? <div className="space-y-3 py-6 text-center"><p className="text-sm text-destructive">Unable to load the institution directory.</p><Button variant="outline" onClick={() => institutions.refetch()}>Retry</Button></div> : institutions.data?.length ? <div className="space-y-3">{institutions.data.map((institution) => <div key={institution.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-4"><div><p className="font-medium">{institution.name}</p><p className="text-sm text-muted-foreground">{[institution.city, institution.state].filter(Boolean).join(', ') || 'Location not provided'}</p></div><div className="flex items-center gap-2"><Badge variant="outline">{institution.code}</Badge><Badge variant={institution.is_active ? 'secondary' : 'destructive'}>{institution.is_active ? 'Active' : 'Inactive'}</Badge></div></div>)}</div> : <p className="py-8 text-center text-sm text-muted-foreground">No institutions were returned.</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default UserManagementPage;
