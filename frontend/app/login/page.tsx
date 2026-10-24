"use client";
import { useEffect, useState } from "react";
import Button from "@/components/button/Button";
import { Notice } from "@/components/Page";
import { request } from "@/lib/api";
import { homeFor, roles, User } from "@/lib/types";
export default function Login() {
  const [users, setUsers] = useState<User[]>([]),
    [selected, setSelected] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    request<User[]>("/auth/dev-users")
      .then((rows) => {
        setUsers(rows);
        setSelected(String(rows[0]?.id || ""));
      })
      .catch(() =>
        setError(
          "Локальный вход отключён. Университетская авторизация пока не подключена.",
        ),
      );
  }, []);
  async function login() {
    setBusy(true);
    try {
      const user = await request<User>("/auth/dev-login", "POST", {
        user_id: Number(selected),
      });
      window.location.assign("/csh" + homeFor(user.role));
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-card">
      <img src="/csh/mpu_logo_l.png" width="220" alt="Московский Политех" />
      <h1>Проверка остаточных знаний</h1>
      <p>Локальный стенд. Выберите сотрудника для входа.</p>
      <Notice text={error} error />
      {users.length > 0 && (
        <>
          <label className="native-field">
            Сотрудник
            <select
            aria-label="Сотрудник"
              value={selected}
              onChange={(event) => setSelected(event.target.value)}
            >
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name} — {roles[user.role]}
                </option>
              ))}
            </select>
          </label>
          <Button
            title="Войти"
            color="btn-blue"
            disabled={busy || !selected}
            onClick={login}
          />
        </>
      )}
    </main>
  );
}
