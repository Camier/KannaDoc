import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from './authStore';

describe('authStore', () => {
  beforeEach(() => {
    // Reset store before each test
    useAuthStore.setState({ user: null });
  });

  it('should set user', () => {
    const user = { name: 'Test User', email: 'test@example.com' };
    
    useAuthStore.getState().setUser(user);
    
    expect(useAuthStore.getState().user).toEqual(user);
  });

  it('should clear user', () => {
    const user = { name: 'Test User', email: 'test@example.com' };
    useAuthStore.setState({ user });
    
    useAuthStore.getState().clearUser();
    
    expect(useAuthStore.getState().user).toBeNull();
  });
});
