import { z } from 'zod';

// Limits mirror the backend: password 8-128 characters on register, 1-128 on login.
const email = z.string().trim().min(1, 'Enter your email address.').pipe(z.email('Enter a valid email address.'));

export const loginSchema = z.object({
  email,
  password: z.string().min(1, 'Enter your password.').max(128, 'Password is too long.'),
});

export const registerSchema = z
  .object({
    email,
    password: z.string().min(8, 'Use at least 8 characters.').max(128, 'Use at most 128 characters.'),
    confirmPassword: z.string().min(1, 'Confirm your password.'),
  })
  .refine((v) => v.password === v.confirmPassword, {
    path: ['confirmPassword'],
    message: 'Passwords do not match.',
  });

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
