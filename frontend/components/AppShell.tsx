"use client";
import {
  PieChart,
  FileText,
  Users,
  BookOpen,
  Settings,
  CalendarDays,
  GraduationCap,
} from "lucide-react";
import Navbar from "./navbar/Navbar";
import { useUser } from "@/contexts/UserContext";
const lpr = [
  { label: "Статистика", href: "/lpr/statistics", icon: PieChart },
  { label: "Приказы", href: "/lpr/order", icon: FileText },
  { label: "Списки рекомендуемых групп", href: "/lpr/list", icon: Users },
  { label: "Отчёты", href: "/lpr/report", icon: BookOpen },
  { label: "Права доступа", href: "/access-rights", icon: Settings },
  { label: "Периоды и справочники", href: "/lpr/settings", icon: CalendarDays },
];
const hod = [
  { label: "Статистика", href: "/hod/statistics", icon: PieChart },
  { label: "Выбор групп", href: "/hod/groups", icon: Users },
  { label: "Выбор дисциплин", href: "/hod/disciplines", icon: BookOpen },
  { label: "Выбор преподавателей", href: "/hod/teachers", icon: GraduationCap },
];
export default function AppShell({ children }: { children: React.ReactNode }) {
  const { userData } = useUser();
  const links =
    userData?.role === "TEACHER"
      ? [
          {
            label: "Согласование дат",
            href: "/teacher/dates",
            icon: CalendarDays,
          },
          { label: "Отчёты", href: "/teacher/report", icon: FileText },
        ]
      : userData?.role === "DEPARTMENT_HEAD"
        ? [
            {
              label: "Рассмотрение документов",
              href: "/dof/documents",
              icon: FileText,
            },
          ]
        : userData?.role === "DEPARTMENT_RESPONSIBLE"
          ? [
              {
                label: "Составление графика",
                href: "/rod/schedule",
                icon: CalendarDays,
              },
              {
                label: "Выбор групп и дисциплин",
                href: "/hod/groups",
                icon: BookOpen,
              },
            ]
          : userData?.role === "CHAIR_HEAD"
            ? hod
            : userData?.role === "GUEST"
              ? []
              : lpr;
  return (
    <div className="bg-container">
      <Navbar title="Проверка остаточных знаний" linkOptions={links} />
      {children}
    </div>
  );
}
