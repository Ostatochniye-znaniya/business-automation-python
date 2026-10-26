"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { request } from "@/lib/api";
import { roles, User } from "@/lib/types";

const Context = createContext<{
  userData: User | null;
  userStatus: { verbose: string } | null;
  loading: boolean;
}>({ userData: null, userStatus: null, loading: true });
export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null),
    [loading, setLoading] = useState(true);
  const path = usePathname();
  useEffect(() => {
    const controller = new AbortController();
    request<User>("/auth/me", "GET", undefined, controller.signal)
      .then((value) => {
        setUser(value);
        setLoading(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setUser(null);
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [path]);
  return (
    <Context.Provider
      value={{
        userData: user,
        userStatus: user ? { verbose: roles[user.role] } : null,
        loading,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export const useUser = () => useContext(Context);
