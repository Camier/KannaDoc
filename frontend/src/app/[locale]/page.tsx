"use client";
import { useAuthStore } from "@/stores/authStore";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { LocaleSelect } from "@/components/LocaleSwitcher";

const Homepage = () => {
  const t = useTranslations("HomePage");
  const { user } = useAuthStore();
  const router = useRouter(); // 获取 router 实例
  const [userLoaded, setUserLoaded] = useState(false);

  useEffect(() => {
    // When the component mounts or user state changes, set userLoaded to true
    setUserLoaded(true);
  }, [user]);

  if (!userLoaded) {
    return null; // Optionally, you could return a loading indicator here
  }

  return (
    <div className="flex w-full h-screen items-center justify-center gap-[3%]">
      {/* 左侧内容区域 */}
      <div className="relative w-[85%] h-[85%] flex flex-col gap-8 items-center justify-center shadow-lg rounded-3xl">
        {/* logo */}
        <div className="w-[80%] h-[80%] flex items-center justify-center">
          <Image
            src="/pictures/logo.png"
            alt="Image 1"
            width={250}
            height={250}
            className="object-cover rounded-3xl"
          />
        </div>

        {/* Welcome 标题 */}
        <div className="w-full flex flex-col items-center justify-center gap-4">
          <h2 className={` font-light text-xl text-gray-900 mb-4`}>
            {t("title")}
          </h2>
          {/* "Agent Workflow Engine – Design, Automate, and Scale with AI-Driven Precision." */}
          <div className="w-full flex flex-col items-center justify-center gap-2">
            <h2 className={`text-gray-500`}>
              {t.rich("subtitle1", {
                brand: (chunks) => (
                  <span className="text-indigo-500">{chunks}</span>
                ),
              })}
            </h2>
            <h2 className={`text text-gray-700`}>{t("subtitle2")}</h2>
          </div>
        </div>

        {/* 登录按钮 */}

        {user === null ? (
          <div
            onClick={() => {
              router.push("/sign-in");
            }}
            className={`text-lg bg-indigo-500 hover:bg-indigo-600 text-white py-2 pl-5 pr-4 rounded-full cursor-pointer flex items-center justify-center`}
          >
            <div>{t("joinButton")}</div>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="size-5 flex items-center justify-center"
            >
              <path
                fillRule="evenodd"
                d="M5.22 14.78a.75.75 0 0 0 1.06 0l7.22-7.22v5.69a.75.75 0 0 0 1.5 0v-7.5a.75.75 0 0 0-.75-.75h-7.5a.75.75 0 0 0 0 1.5h5.69l-7.22 7.22a.75.75 0 0 0 0 1.06Z"
                clipRule="evenodd"
              />
            </svg>
          </div>
        ) : (
          <div className="flex items-center justify-center gap-[5%] w-[50%]">
            <div
              onClick={() => {
                window.location.href = "/work-flow";
              }}
              className={`text-lg bg-indigo-500 hover:bg-indigo-600 text-white py-2 pl-6 pr-5 rounded-full cursor-pointer flex items-center justify-center`}
            >
              <div>{t("startButton")}</div>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="size-5 flex items-center justify-center"
              >
                <path
                  fillRule="evenodd"
                  d="M5.22 14.78a.75.75 0 0 0 1.06 0l7.22-7.22v5.69a.75.75 0 0 0 1.5 0v-7.5a.75.75 0 0 0-.75-.75h-7.5a.75.75 0 0 0 0 1.5h5.69l-7.22 7.22a.75.75 0 0 0 0 1.06Z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
          </div>
        )}

        <div className="flex-col items-center justify-center font-light">
          <h4
            className={`flex items-center justify-center text-sm font-sans text-gray-900 mb-4`}
          >
            {t("forgetTokenization")}
          </h4>
          <h4
            className={`flex items-center justify-center text-xs font-sans text-gray-900 mb-3`}
          >
            {t("contactPrefix")}
            <span className="text-indigo-700 ml-1 mr-1">
              {" "}
              liweixmu@foxmail.com{" "}
            </span>
            <span>|</span>
            <Link
              href="https://github.com/liweiphys"
              className="text-indigo-700 ml-1"
            >
              {t("githubLink")}
            </Link>
          </h4>
        </div>
        <div className="absolute top-6 right-6 text-sm">
          <div className="px-3 text-indigo-500 hover:text-indigo-700 flex items-center cursor-pointer">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="1.5"
              stroke="currentColor"
              className="size-5 mr-1"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12.75 3.03v.568c0 .334.148.65.405.864l1.068.89c.442.369.535 1.01.216 1.49l-.51.766a2.25 2.25 0 0 1-1.161.886l-.143.048a1.107 1.107 0 0 0-.57 1.664c.369.555.169 1.307-.427 1.605L9 13.125l.423 1.059a.956.956 0 0 1-1.652.928l-.679-.906a1.125 1.125 0 0 0-1.906.172L4.5 15.75l-.612.153M12.75 3.031a9 9 0 0 0-8.862 12.872M12.75 3.031a9 9 0 0 1 6.69 14.036m0 0-.177-.529A2.25 2.25 0 0 0 17.128 15H16.5l-.324-.324a1.453 1.453 0 0 0-2.328.377l-.036.073a1.586 1.586 0 0 1-.982.816l-.99.282c-.55.157-.894.702-.8 1.267l.073.438c.08.474.49.821.97.821.846 0 1.598.542 1.865 1.345l.215.643m5.276-3.67a9.012 9.012 0 0 1-5.276 3.67m0 0a9 9 0 0 1-10.275-4.835M15.75 9c0 .896-.393 1.7-1.016 2.25"
              />
            </svg>

            <LocaleSelect />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Homepage;
