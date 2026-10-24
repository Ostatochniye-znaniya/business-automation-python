"use client";
import { useState } from "react";
import Page, { Notice } from "@/components/Page";
import { useAction } from "@/lib/hooks";
import { request } from "@/lib/api";
import { roles } from "@/lib/types";
export default function GuestPage() {
  const [role, setRole] = useState("TEACHER"),
    [reason, setReason] = useState("");
  const action = useAction();
  return (
    <Page title="Запрос доступа">
      <p>Рабочая роль ещё не назначена. Отправьте заявку ЛПР.</p>
      <Notice text={action.notice} error={action.failed} />
      <form
        className="form-grid"
        onSubmit={(event) => {
          event.preventDefault();
          action.run(() =>
            request("/administration/access-requests", "POST", {
              requested_role: role,
              reason,
            }),
          );
        }}
      >
        <label>
          Роль
          <select
            value={role}
            onChange={(event) => setRole(event.target.value)}
          >
            {Object.entries(roles)
              .filter(([value]) => !["GUEST", "ADMIN"].includes(value))
              .map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
          </select>
        </label>
        <label>
          Основание
          <textarea
            required
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>
        <button className="btn btn-blue" disabled={action.busy}>
          Отправить заявку
        </button>
      </form>
    </Page>
  );
}
