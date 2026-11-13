import { api } from '@/lib/api-client';
import type { Credentials, TokenResponse, User } from './types';

export const authApi = {
  register: async (credentials: Credentials): Promise<User> =>
    (await api.post<User>('/auth/register', credentials)).data,

  login: async (credentials: Credentials): Promise<TokenResponse> =>
    (await api.post<TokenResponse>('/auth/login', credentials)).data,

  me: async (): Promise<User> => (await api.get<User>('/auth/me')).data,
};
