"use client";
import { useEffect } from "react";
import { usePathname } from "next/navigation";

export default function NoTransitionOnNav() {
  const pathname = usePathname();

  useEffect(() => {
    const el = document.documentElement;
    el.classList.add("no-transition");
    const raf = requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        el.classList.remove("no-transition");
      });
    });
    return () => cancelAnimationFrame(raf);
  }, [pathname]);

  return null;
}
