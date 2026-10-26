"use client";
import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LucideIcon, Maximize2 } from "lucide-react";
import { useUser } from "@/contexts/UserContext";

interface LinkOption {
  label: string;
  href: string;
  icon?: LucideIcon;
}

interface NavbarProps {
  title: string;
  linkOptions?: LinkOption[];
  avatarUrl?: string;
}

const Navbar: React.FC<NavbarProps> = ({ linkOptions, avatarUrl }) => {
  const { userData, userStatus } = useUser();
  const pathname = usePathname();

  const toggleTheme = () => {
    const isDark = document.documentElement.classList.toggle("dark");
    localStorage.setItem("theme", isDark ? "dark" : "light");
  };

  const toggleCollapse = () => {
    const next = document.documentElement.classList.toggle("sidebar-collapsed");
    localStorage.setItem("sidebarCollapsed", String(next));
  };

  const userFullName = userData?.full_name || userData?.email || "";

  const displayRole = userStatus?.verbose || "";
  const displayAvatarUrl = avatarUrl || "/csh/default_avatar.png";

  return (
    <>
      <div className="navbar-container">
        <a
          href="https://mospolytech.ru/"
          target="_blank"
          rel="noopener noreferrer"
          className="navbar-logo-link"
        >
          <img className="theme-aware-logo" alt="МПУ Логотип" />
        </a>

        <div className="navbar-divider"></div>
        <Link
          href={linkOptions?.[0]?.href ?? "/"}
          className="navbar-logo-link navbar-logo-link--left"
        >
          <img className="navbar-title-logo" alt="Проверка остаточных знаний" />
        </Link>
        <div className="navbar-divider"></div>

        <a
          href="https://e.mospolytech.ru/"
          target="_blank"
          rel="noopener noreferrer"
          className="navbar-avatar"
        >
          <img
            src={displayAvatarUrl}
            alt="Avatar"
            width={80}
            height={80}
            style={{ borderRadius: "50%", objectFit: "cover" }}
          />
        </a>

        <div className="navbar-text-container">
          <p className="navbar-user-name" suppressHydrationWarning>
            {userFullName}
          </p>
          <p className="navbar-user-role" suppressHydrationWarning>
            {displayRole}
          </p>
        </div>

        <div className="navbar-divider"></div>

        <div className="navbar-link-container">
          {linkOptions &&
            linkOptions.map((option, index) => {
              const isActive = pathname === option.href;
              const Icon = option.icon;
              return (
                <Link
                  key={index}
                  href={option.href}
                  className={`navbar-inner-container ${isActive ? "navbar-inner-active" : ""}`}
                >
                  {isActive && <span className="navbar-active-dot"></span>}
                  {Icon && (
                    <span className="navbar-icon-wrap">
                      <Icon size={18} />
                    </span>
                  )}
                  <span
                    className={
                      isActive
                        ? "navbar-path navbar-active-path"
                        : "navbar-path navbar-deactive-path"
                    }
                  >
                    {option.label}
                  </span>
                </Link>
              );
            })}
        </div>

        <div
          className="navbar-theme-toggle"
          style={{ marginTop: "auto" }}
          onClick={toggleTheme}
        >
          <span className="navbar-path navbar-deactive-path navbar-theme-label">
            Тёмная тема
          </span>
          <div className="navbar-theme-switch">
            <div className="navbar-theme-switch-thumb"></div>
          </div>
        </div>
      </div>

      <button
        className="sidebar-collapse-fab"
        onClick={toggleCollapse}
        title="Свернуть / Развернуть"
      >
        <Maximize2 size={20} />
      </button>
    </>
  );
};

export default Navbar;
