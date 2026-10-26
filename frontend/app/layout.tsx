import type { Metadata } from "next";
import "./globals.css";
import "./unified.css";
import { UserProvider } from "@/contexts/UserContext";
import SessionGate from "@/components/SessionGate";

export const metadata: Metadata = {
  title: "Остаточные знания",
  description: "Проверка остаточных знаний — Московский Политех",
  icons: { icon: "/csh/favicon.svg" },
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `try{if(localStorage.getItem('theme')==='dark')document.documentElement.classList.add('dark');if(localStorage.getItem('sidebarCollapsed')==='true')document.documentElement.classList.add('sidebar-collapsed')}catch{}`,
          }}
        />
      </head>
      <body>
        <div className="bg-gradient" />
        <UserProvider>
          <SessionGate>{children}</SessionGate>
        </UserProvider>
      </body>
    </html>
  );
}
