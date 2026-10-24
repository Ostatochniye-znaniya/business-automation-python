"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "@/contexts/UserContext";
import { homeFor } from "@/lib/types";
export default function Home() {
  const { userData } = useUser(),
    router = useRouter();
  useEffect(() => {
    if (userData) router.replace(homeFor(userData.role));
  }, [userData, router]);
  return <p className="session-loading">Открываем приложение…</p>;
}
