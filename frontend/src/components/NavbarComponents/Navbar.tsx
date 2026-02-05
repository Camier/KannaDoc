"use client";
import UserMenuExpand from "./UserMenuExpand";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useEffect } from "react";
import { useUIStore } from "@/stores/uiStore";
import Image from "next/image";

const Navbar = () => {
  const t = useTranslations("Navbar");
  const pathname = usePathname(); // 直接获取当前路径（如 "/about"）
  const { isSidebarVisible, toggleSidebar } = useUIStore();
  const navbarButtonStyle = `transform transition-all duration-300 h-8 flex items-center justify-center gap-1 cursor-pointer
   border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800
  `;

  // Sidebar visibility is only relevant for specific pages
  const showToggle = ["/ai-chat", "/work-flow", "/knowledge-base"].some(path => pathname.includes(path));

  return (
    <div className="z-10 fixed left-[2%] w-[96%] pl-[2%] pr-[15%] bg-slate-950/90 border border-slate-800 h-[5%] my-1 rounded-xl flex justify-between items-center shadow-2xl backdrop-blur-md">
      <div className="flex items-center gap-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 ml-2 group">
          <Image
            src="/pictures/logo.png"
            alt="Logo"
            width={28}
            height={28}
            className="rounded group-hover:scale-110 transition-transform duration-300 contrast-125 brightness-110"
          />
        </Link>

        <div className="h-4 w-px bg-slate-800 mx-1" />

        {showToggle && (
          <div 
            onClick={toggleSidebar}
            className={navbarButtonStyle + " rounded-lg p-1.5"}
            title={isSidebarVisible ? "Hide Sidebar" : "Show Sidebar"}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="1.5"
              stroke="currentColor"
              className="size-5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d={isSidebarVisible 
                  ? "M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12" 
                  : "M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"}
              />
            </svg>
          </div>
        )}
        
        <div className={navbarButtonStyle + `${pathname === "/" || pathname === "/en" || pathname === "/zh-CN" ? "bg-slate-800 text-white" : ""} rounded-lg px-4`}>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="1.5"
            stroke="currentColor"
            className="size-4.5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25"
            />
          </svg>

          <Link href="/" className="font-medium text-xs uppercase tracking-wider">
            {t("home")}
          </Link>
        </div>
      </div>

      <div
        className={
          navbarButtonStyle +
          `${pathname.includes("/ai-chat") ? "bg-slate-800 text-white border border-slate-700" : ""
          }  rounded-lg px-4`
        }
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth="1.5"
          stroke="currentColor"
          className="size-4.5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M8.625 9.75a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.184-4.183a1.14 1.14 0 0 1 .778-.332 48.294 48.294 0 0 0 5.83-.498c1.585-.233 2.708-1.626 2.708-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z"
          />
        </svg>

        <Link href="/ai-chat" className="font-medium text-xs uppercase tracking-wider">
          {t("aiChat")}
        </Link>
      </div>

      <div
        className={
          navbarButtonStyle +
          `${pathname.includes("/work-flow") ? "bg-slate-800 text-white border border-slate-700" : ""
          }  rounded-lg px-4`
        }
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth="1.5"
          stroke="currentColor"
          className="size-4.5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="m6.75 7.5 3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0 0 21 18V6a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 6v12a2.25 2.25 0 0 0 2.25 2.25Z"
          />
        </svg>

        <Link href="/work-flow" className="font-medium text-xs uppercase tracking-wider">
          {t("workFlow")}
        </Link>
      </div>

      <div
        className={
          navbarButtonStyle +
          `${pathname.includes("/knowledge-base") ? "bg-slate-800 text-white border border-slate-700" : ""
          } rounded-lg px-4`
        }
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth="1.5"
          stroke="currentColor"
          className="size-4.5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
          />
        </svg>
        <Link href="/knowledge-base" className="font-medium text-xs uppercase tracking-wider">
          {t("knowledgeBase")}
        </Link>
      </div>

      <UserMenuExpand />
    </div>
  );
};

export default Navbar;
