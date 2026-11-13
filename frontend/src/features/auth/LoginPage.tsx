import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Mail } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';
import { toApiError } from '@/lib/errors';
import { AuthLayout } from './AuthLayout';
import { PasswordField } from './PasswordField';
import { useAuth } from './auth-context';
import { loginSchema, type LoginValues } from './schemas';

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema), defaultValues: { email: '', password: '' } });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await login(values);
      toast.success('Welcome back.');
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && from.startsWith('/') ? from : '/', { replace: true });
    } catch (error) {
      setFormError(toApiError(error).message);
    }
  });

  return (
    <AuthLayout title="Sign in" subtitle="Welcome back. Sign in to open your workspace.">
      <form onSubmit={onSubmit} noValidate className="space-y-5">
        {formError && (
          <div role="alert" className="rounded-xl border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger">
            {formError}
          </div>
        )}
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          icon={<Mail className="h-[18px] w-[18px]" aria-hidden="true" />}
          error={errors.email?.message}
          {...register('email')}
        />
        <PasswordField label="Password" autoComplete="current-password" placeholder="Your password" error={errors.password?.message} {...register('password')} />
        <Button type="submit" variant="primary" size="lg" loading={isSubmitting} className="w-full justify-center">
          {isSubmitting ? 'Signing in' : 'Sign in'}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-ink-soft">
        New to NOVA DOCS?{' '}
        <Link to="/register" className="font-medium text-brand-mint underline-offset-4 hover:underline">
          Create an account
        </Link>
      </p>
    </AuthLayout>
  );
}
