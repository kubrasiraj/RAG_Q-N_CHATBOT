import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import { Mail } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';
import { toApiError } from '@/lib/errors';
import { AuthLayout } from './AuthLayout';
import { PasswordField } from './PasswordField';
import { useAuth } from './auth-context';
import { registerSchema, type RegisterValues } from './schemas';

export function RegisterPage() {
  const { register: registerAccount } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: '', password: '', confirmPassword: '' },
  });

  const onSubmit = handleSubmit(async ({ email, password }) => {
    setFormError(null);
    try {
      await registerAccount({ email, password });
      toast.success('Account created. Welcome to NOVA DOCS.');
      navigate('/', { replace: true });
    } catch (error) {
      setFormError(toApiError(error).message);
    }
  });

  return (
    <AuthLayout title="Create your account" subtitle="Start asking questions about your documents.">
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
        <PasswordField label="Password" autoComplete="new-password" placeholder="At least 8 characters" hint="8 to 128 characters." error={errors.password?.message} {...register('password')} />
        <PasswordField label="Confirm password" autoComplete="new-password" placeholder="Repeat your password" error={errors.confirmPassword?.message} {...register('confirmPassword')} />
        <Button type="submit" variant="primary" size="lg" loading={isSubmitting} className="w-full justify-center">
          {isSubmitting ? 'Creating account' : 'Create account'}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-ink-soft">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-brand-mint underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
