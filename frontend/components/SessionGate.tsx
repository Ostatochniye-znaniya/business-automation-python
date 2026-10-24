"use client";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useUser } from "@/contexts/UserContext";
import { homeFor } from "@/lib/types";
import AppShell from "./AppShell";

export default function SessionGate({
  children,
}: {
  children: React.ReactNode;
}) {
  const { userData, loading } = useUser();
  const path = usePathname(),
    router = useRouter();
  const publicPage = path === "/login";
  useEffect(() => {
    if (loading || publicPage) return;
    if (!userData) {
      router.replace("/login");
      return;
    }
    const prefixes: Record<string, string[]> = {
      lpr: ["ADMIN", "LPR"],
      dof: ["DEPARTMENT_HEAD"],
      hod: ["CHAIR_HEAD", "DEPARTMENT_RESPONSIBLE", "ADMIN", "LPR"],
      rod: ["DEPARTMENT_RESPONSIBLE", "ADMIN", "LPR"],
      teacher: ["TEACHER"],
      "access-rights": ["ADMIN", "LPR"],
      guest: ["GUEST"],
    };
    const allowed = prefixes[path.split("/")[1]];
    if (allowed && !allowed.includes(userData.role))
      router.replace(homeFor(userData.role));
  }, [userData, loading, publicPage, path, router]);
  if (!publicPage && (loading || !userData))
    return <p className="session-loading">Загрузка…</p>;
  return publicPage ? children : <AppShell>{children}</AppShell>;
}
