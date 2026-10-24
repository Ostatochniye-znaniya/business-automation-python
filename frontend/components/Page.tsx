"use client";
import Button from "./button/Button";
import { request } from "@/lib/api";
export default function Page({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <main className="main-container">
      <header className="page-header">
        <h1>{title}</h1>
        <Button
          title="Сменить пользователя"
          color="btn-blue"
          onClick={async () => {
            await request("/auth/logout", "POST");
            window.location.assign("/csh/login");
          }}
        />
      </header>
      <div className="page-body">{children}</div>
    </main>
  );
}
export function Notice({
  text,
  error = false,
}: {
  text: string;
  error?: boolean;
}) {
  return text ? (
    <p
      role={error ? "alert" : "status"}
      className={`notice ${error ? "error" : ""}`}
    >
      {text}
    </p>
  ) : null;
}
