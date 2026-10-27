import React, { useState } from 'react';
import axios from 'axios';
import { Eye, EyeOff, Shield, Lock, Mail, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const [email, setEmail] = useState('reviewer@fdrportal.demo');
  const [password, setPassword] = useState('Reviewer@123');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setErrorMessage('Please enter both email and password.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      await login(email, password);
    } catch (err: unknown) {
      if (axios.isAxiosError<{ detail?: string; error?: { message?: string } }>(err)) {
        setErrorMessage(
          err.response?.data?.detail ||
            err.response?.data?.error?.message ||
            'Unable to sign in. Check your credentials and confirm the backend is running.'
        );
      } else {
        setErrorMessage(err instanceof Error ? err.message : 'Authentication failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickFill = (roleEmail: string, rolePassword: string) => {
    setEmail(roleEmail);
    setPassword(rolePassword);
    setErrorMessage(null);
  };

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 px-4 py-12 text-foreground sm:px-6 lg:px-8">
      {/* Background Decorative Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b15_1px,transparent_1px),linear-gradient(to_bottom,#1e293b15_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />

      {/* Main Login Container */}
      <div className="relative z-10 w-full max-w-md">
        {/* Government Emblem / Portal Header */}
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-600 shadow-xl shadow-blue-500/25 ring-8 ring-blue-500/10">
            <Shield className="h-9 w-9 text-white" />
          </div>
          <h1 className="mt-4 text-2xl font-bold tracking-tight text-white sm:text-3xl">
            FDR Intelligence Portal
          </h1>
          <p className="mt-1 text-sm text-blue-200/80">
            Regulatory Compliance & Fixed Deposit Receipt Verification System
          </p>
        </div>

        {/* Login Card */}
        <Card className="border-border/40 bg-card/95 shadow-2xl backdrop-blur-md">
          <CardHeader className="space-y-1 pb-4">
            <CardTitle className="text-xl font-semibold tracking-tight text-center">
              Regulatory Portal Access
            </CardTitle>
            <CardDescription className="text-center text-xs">
              Authenticate using your authorized organizational credentials
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {errorMessage && (
              <div className="flex items-center space-x-2 rounded-md bg-destructive/10 p-3 text-xs text-destructive border border-destructive/20">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-xs font-semibold">
                  Official Email Address
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="officer@regulator.gov"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="pl-9 text-sm"
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-xs font-semibold">
                    Password / Passkey
                  </Label>
                  <a
                    href="#forgot"
                    onClick={(e) => {
                      e.preventDefault();
                      alert('Password recovery: Contact the System Administrator.');
                    }}
                    className="text-xs text-primary hover:underline"
                  >
                    Forgot password?
                  </a>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="pl-9 pr-10 text-sm"
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <Button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5"
                disabled={isLoading}
              >
                {isLoading ? (
                  <span className="flex items-center space-x-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    <span>Verifying Credentials...</span>
                  </span>
                ) : (
                  'Sign In to Secure Portal'
                )}
              </Button>
            </form>

            {/* Quick Demo Role Selection */}
            <div className="pt-2">
              <div className="relative my-3">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-border" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground font-semibold text-[10px]">
                    Quick Demo Credentials
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="text-xs py-1 h-auto flex flex-col items-center text-center justify-center border-slate-300 dark:border-slate-700"
                  onClick={() => handleQuickFill('reviewer@fdrportal.demo', 'Reviewer@123')}
                >
                  <span className="font-semibold text-[11px]">Reviewer</span>
                  <span className="text-[9px] text-muted-foreground">Compliance</span>
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="text-xs py-1 h-auto flex flex-col items-center text-center justify-center border-slate-300 dark:border-slate-700"
                  onClick={() => handleQuickFill('inst1@fdrportal.demo', 'Institute1@123')}
                >
                  <span className="font-semibold text-[11px]">Institution</span>
                  <span className="text-[9px] text-muted-foreground">Applicant</span>
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="text-xs py-1 h-auto flex flex-col items-center text-center justify-center border-slate-300 dark:border-slate-700"
                  onClick={() => handleQuickFill('admin@fdrportal.demo', 'Admin@123')}
                >
                  <span className="font-semibold text-[11px]">Admin</span>
                  <span className="text-[9px] text-muted-foreground">Superuser</span>
                </Button>
              </div>
            </div>
          </CardContent>

          <CardFooter className="flex flex-col space-y-2 border-t border-border/50 bg-muted/20 py-3 text-center text-[11px] text-muted-foreground">
            <div className="flex items-center justify-center space-x-1.5 text-emerald-600 dark:text-emerald-400 font-medium">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Demo Environment Active • 256-Bit SSL Encrypted</span>
            </div>
            <p>
              Unauthorized access to this regulatory repository is strictly prohibited under the Information Technology Act.
            </p>
          </CardFooter>
        </Card>

        {/* Legal notice */}
        <div className="mt-6 text-center text-xs text-slate-400">
          Fixed Deposit Receipt Intelligence & Compliance Portal © {new Date().getFullYear()}
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
