import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  fetchMe,
  login as apiLogin,
  logout as apiLogout,
  refreshAccessToken,
  registerSessionHandlers,
  verifyMfaLogin,
  type LoginResponse,
  type SecondFactor,
  type UserPublic,
} from "../lib/api";
import { memoryInvalidate } from "../lib/queryMemory";

export type LoginOutcome =
  | { kind: "signed_in" }
  | { kind: "mfa_required"; mfaToken: string }
  | { kind: "enrollment_required"; enrollmentToken: string };

type AuthContextValue = {
  user: UserPublic | null;
  accessToken: string | null;
  isLoading: boolean;
  /** Password step. May require a second step before a session exists. */
  login: (email: string, password: string) => Promise<LoginOutcome>;
  /** Second step: TOTP code or single-use recovery code. */
  completeMfa: (mfaToken: string, factor: SecondFactor) => Promise<void>;
  /** Install a session returned by an endpoint (e.g. MFA enrollment). */
  applySession: (token: string, user: UserPublic) => void;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

let bootstrapPromise: Promise<{ token: string; user: UserPublic }> | null = null;

async function bootstrapSession(): Promise<{ token: string; user: UserPublic }> {
  if (!bootstrapPromise) {
    bootstrapPromise = (async () => {
      const refreshed = await refreshAccessToken();
      const user = refreshed.user ?? (await fetchMe(refreshed.access_token));
      return { token: refreshed.access_token, user };
    })().catch((error) => {
      bootstrapPromise = null;
      throw error;
    });
  }
  return bootstrapPromise;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setIsLoading(true);
      try {
        const session = await bootstrapSession();
        if (cancelled) return;
        setAccessToken(session.token);
        setUser(session.user);
      } catch {
        if (cancelled) return;
        setUser(null);
        setAccessToken(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    registerSessionHandlers({
      onRefreshed: (token, refreshedUser) => {
        bootstrapPromise = null;
        setAccessToken(token);
        if (refreshedUser) setUser(refreshedUser);
      },
      onExpired: () => {
        bootstrapPromise = null;
        memoryInvalidate();
        setUser(null);
        setAccessToken(null);
      },
    });
    return () => registerSessionHandlers(null);
  }, []);

  const applySession = useCallback((token: string, nextUser: UserPublic) => {
    bootstrapPromise = Promise.resolve({ token, user: nextUser });
    memoryInvalidate();
    setAccessToken(token);
    setUser(nextUser);
  }, []);

  const installFromResponse = useCallback(
    (result: LoginResponse): boolean => {
      if (result.access_token && result.user) {
        applySession(result.access_token, result.user);
        return true;
      }
      return false;
    },
    [applySession],
  );

  const login = useCallback(
    async (email: string, password: string): Promise<LoginOutcome> => {
      const result = await apiLogin(email, password);
      if (result.mfa_required && result.mfa_token) {
        return { kind: "mfa_required", mfaToken: result.mfa_token };
      }
      if (result.enrollment_token) {
        return { kind: "enrollment_required", enrollmentToken: result.enrollment_token };
      }
      if (!installFromResponse(result)) {
        throw new Error("Sign-in did not return a session. Please try again.");
      }
      return { kind: "signed_in" };
    },
    [installFromResponse],
  );

  const completeMfa = useCallback(
    async (mfaToken: string, factor: SecondFactor) => {
      const result = await verifyMfaLogin(mfaToken, factor);
      if (!installFromResponse(result)) {
        throw new Error("Verification did not return a session. Please sign in again.");
      }
    },
    [installFromResponse],
  );

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch {
      // The server-side revoke failed (e.g. network); still end the local session.
    } finally {
      bootstrapPromise = null;
      memoryInvalidate();
      setUser(null);
      setAccessToken(null);
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      accessToken,
      isLoading,
      login,
      completeMfa,
      applySession,
      logout,
    }),
    [user, accessToken, isLoading, login, completeMfa, applySession, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
