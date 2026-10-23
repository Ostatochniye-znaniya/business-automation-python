export interface User {
  id: number;
  full_name: string;
  email: string | null;
  external_id: string | null;
  role: string;
  department_id: number | null;
  position: string | null;
  is_active: boolean;
}
export interface Period {
  id: number;
  name: string;
  academic_year: string;
  semester: number;
  start_date: string;
  end_date: string;
  status: string;
  paper_reports_required: boolean;
}
export interface Department {
  id: number;
  name: string;
  parent_id: number | null;
  type: string;
  short_name: string | null;
}
export interface Group {
  id: number;
  name: string;
  department_id: number | null;
  study_program_id: number | null;
  admission_year: number | null;
  external_id: string | null;
}
export interface Discipline {
  id: number;
  name: string;
  department_id: number | null;
}
export interface KnowledgeTest {
  id: number;
  period_id: number;
  group_id: number;
  discipline_id: number;
  teacher_id: number | null;
  scheduled_at: string | null;
  room: string | null;
  status: string;
  agreement_status: string;
  agreement_comment: string | null;
}
export interface ReportRow {
  knowledge_test_id: number;
  report_id: number | null;
  period_id: number;
  period_name: string;
  group_id: number;
  group_name: string;
  faculty_id: number | null;
  faculty_name: string | null;
  department_id: number | null;
  department_name: string | null;
  discipline_id: number;
  discipline_name: string;
  teacher_name: string | null;
  previous_teacher_name: string | null;
  electronic_status: string;
  electronic_comment: string | null;
  paper_status: string;
  paper_comment: string | null;
  paper_reports_required: boolean;
  final_status: string;
  has_file: boolean;
  total_students: number;
  participated_students: number;
  participation_percentage: number;
  at_least_half_participated: boolean;
}
export const roles: Record<string, string> = {
  ADMIN: "Администратор",
  LPR: "ЛПР",
  DEPARTMENT_HEAD: "Декан / директор института",
  DEPARTMENT_RESPONSIBLE: "Ответственный факультета",
  CHAIR_HEAD: "Заведующий кафедрой",
  TEACHER: "Преподаватель",
  GUEST: "Гость",
};
export const statuses: Record<string, string> = {
  MISSING: "Не сдан",
  DRAFT: "Черновик",
  SUBMITTED: "Требует проверки",
  APPROVED: "Одобрен",
  REJECTED: "На доработке",
  NOT_REQUIRED: "Не требуется",
  COMPLETE: "Всё сдано",
  PENDING: "Не всё сдано",
  PROPOSED: "Ожидает согласования",
  AGREED: "Согласовано",
  PLANNED: "Запланировано",
  IN_PROGRESS: "Идёт проверка",
  COMPLETED: "Завершено",
  CANCELLED: "Отменено",
};
export const isManager = (user: User | null) =>
  !!user && ["ADMIN", "LPR"].includes(user.role);
export function homeFor(role: string) {
  return (
    (
      {
        ADMIN: "/lpr/statistics",
        LPR: "/lpr/statistics",
        DEPARTMENT_HEAD: "/dof/documents",
        DEPARTMENT_RESPONSIBLE: "/rod/schedule",
        CHAIR_HEAD: "/hod/groups",
        TEACHER: "/teacher/dates",
      } as Record<string, string>
    )[role] || "/guest"
  );
}
