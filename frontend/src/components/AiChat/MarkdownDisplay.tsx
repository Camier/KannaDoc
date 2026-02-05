import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { FC, useState } from "react";
import { Message } from "@/types/types";
import rehypeRaw from "rehype-raw"; // 新增：用于解析原始HTML
import { base64Processor } from "@/utils/file";
import { useTranslations } from "next-intl";

interface MarkdownDisplayProps {
  md_text: string;
  message: Message;
  showTokenNumber: boolean;
  isThinking: boolean;
}

// Add new CodeBlock component
const CodeBlock: FC<{
  node?: any;
  className?: string;
  children?: any;
  [key: string]: any;
}> = ({ node, className, children, ...props }) => {
  const t = useTranslations("MarkdownDisplay");
  const match = /language-(\w+)/.exec(className || "");
  const language = match ? match[1] : null;

  const [copied, setCopied] = useState(false);

  // 递归提取文本内容
  const extractText = (child: any): string => {
    if (typeof child === "string") return child;
    if (Array.isArray(child)) return child.map(extractText).join("");
    if (child?.props?.children) return extractText(child.props.children);
    return "";
  };

  const handleCopy = async () => {
    const textToCopy = extractText(children)
      .replace(/\n$/, "")
      .replace(/\\_/g, "_");

    try {
      // 现代浏览器方案
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(textToCopy);
      }
      // 旧浏览器降级方案
      else if (document.queryCommandSupported?.("copy")) {
        const textArea = document.createElement("textarea");
        textArea.value = textToCopy;
        textArea.style.position = "fixed";
        document.body.appendChild(textArea);
        textArea.select();

        // Safari 特殊处理
        if (navigator.userAgent.match(/iphone|ipad|ipod/i)) {
          textArea.contentEditable = "true";
          textArea.readOnly = true;
          const range = document.createRange();
          range.selectNodeContents(textArea);
          const selection = window.getSelection();
          selection?.removeAllRanges();
          selection?.addRange(range);
          textArea.setSelectionRange(0, 999999);
        }

        document.execCommand("copy");
        document.body.removeChild(textArea);
      }
      // 终极降级方案
      else {
        throw new Error("当前浏览器不支持复制功能");
      }

      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      const fallbackText = document.createElement("div");
      fallbackText.contentEditable = "true";
      fallbackText.textContent = textToCopy;
      Object.assign(fallbackText.style, {
        position: "fixed",
        left: "-9999px",
        opacity: "0",
      });
      document.body.appendChild(fallbackText);

      const range = document.createRange();
      range.selectNodeContents(fallbackText);
      const selection = window.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(range);

      alert(t("copyFallback"));
      setTimeout(() => {
        document.body.removeChild(fallbackText);
      }, 100);
    }
  };

  return language ? (
    <div className="relative group my-4 border border-slate-800 rounded-lg bg-slate-950 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-900/50 text-slate-400 text-[10px] font-bold tracking-[0.2em] uppercase">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-slate-700" />
          {language}
        </div>
        <button
          onClick={handleCopy}
          className="cursor-pointer flex items-center gap-1.5 hover:text-indigo-400 transition-colors"
          aria-label="Copy"
        >
          {!copied ? (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="2"
              stroke="currentColor"
              className="size-3.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 0 1-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 0 1 1.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 0 0-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 0 1-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 0 0-3.375-3.375h-1.5a1.125 1.125 0 0 1-1.125-1.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H9.75"
              />
            </svg>
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="2"
              stroke="currentColor"
              className="size-3.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m4.5 12.75 6 6 9-13.5"
              />
            </svg>
          )}

          <span className="">{copied ? t("copied") : t("copy")}</span>
        </button>
      </div>
      <code
        className={`${className} block p-4 font-mono text-[13px] leading-relaxed text-slate-300 overflow-x-auto`}
        {...props}
      >
        {children}
      </code>
    </div>
  ) : (
    <code className="px-1.5 py-0.5 rounded border border-slate-800 bg-slate-900 text-indigo-300 font-mono text-[0.9em]" {...props}>
      {children}
    </code>
  );
};

const MarkdownDisplay: React.FC<MarkdownDisplayProps> = ({
  md_text,
  message,
  showTokenNumber,
  isThinking,
}) => {
  const t = useTranslations("MarkdownDisplay");
  const [hideThinking, setHideThinking] = useState(false);

  return (
    <div
      className={`flex flex-col gap-2 w-fit max-w-full ${
        message.from === "user" ? "ml-auto" : "mr-auto"
      }`}
    >
      <div
        className={`${
          message.from === "user"
            ? "bg-indigo-200 shadow-lg px-5 py-3 text-gray-800 rounded-3xl "
            : "text-gray-900 dark:text-gray-100 "
        } prose dark:prose-invert max-w-full ${
          isThinking
            ? "border-l-2 border-gray-200 dark:border-gray-700 p-4 bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-3xl text-sm mb-4"
            : "text-base"
        }`}
      >
        {isThinking && (
          <div
            className="flex items-center justify-start gap-1 cursor-pointer text-gray-800 dark:text-gray-200"
            onClick={() => setHideThinking((prev) => !prev)}
          >
            <div className="font-medium">{t("deepThinking")}</div>
            <svg
              className={`ml-1 w-4 h-4 transition-transform ${
                hideThinking ? "" : "rotate-180"
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={3}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>
        )}
        {!hideThinking &&
          (message.from === "ai" && !isThinking ? (
            <ReactMarkdown
              remarkPlugins={[remarkMath, remarkGfm]} // 必须 math 在前
              rehypePlugins={[
                //rehypeRaw, //防止注入攻击，暂不启用
                [
                  rehypeKatex,
                  {
                    output: "mathml",
                    strict: false, // 关闭严格模式
                    macros: {
                      "\\text": "\\textrm", // 修复 text 命令
                      "\\|": "\\Vert", // 定义双竖线宏
                    },
                  },
                ],
                rehypeHighlight,
              ]}
              components={{
                code: CodeBlock,
                a({ node, href, children, ...props }) {
                  return (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300"
                    >
                      {children}
                    </a>
                  );
                },
                // 添加图片处理组件
                // 修改img组件处理逻辑
                img({ node, src, alt, title, style, width, height, ...props }) {
                  if (!src) {
                    return null;
                  } else {
                    const newsrc = base64Processor.decode(src as string);
                    return (
                      <img
                        src={newsrc}
                        alt={alt}
                        title={title}
                        className="mx-auto object-contain"
                        style={{
                          maxWidth: "min(100%, 800px)",
                          marginLeft: "auto",
                          marginRight: "auto",
                        }}
                        loading="lazy"
                        decoding="async"
                        // 传递原生属性
                        {...props}
                      />
                    );
                  }
                },
              }}
            >
              {base64Processor.encode(
                md_text
                  .trimStart()
                  .replace(/\\\[/g, "$$$$") // 匹配 \\[ → $$
                  .replace(/\\\]/g, "$$$$") // 匹配 \\] → $$
                  // 行内公式替换
                  .replace(/\\\(/g, "$") // 匹配 \\( → $
                  .replace(/\\\)/g, "$") // 匹配 \\) → $
              )}
            </ReactMarkdown>
          ) : (
            <div
              className={`whitespace-pre-wrap ${
                isThinking ? "mt-3 text-gray-600" : ""
              }`}
            >
              {md_text.trimStart()}
            </div>
          ))}
      </div>
      {message.token_number !== undefined &&
        message.token_number.total_token > 0 &&
        showTokenNumber && (
          <div
            className={`text-gray-600 flex gap-4 ${
              isThinking ? "border-l-2 pl-2 border-gray-200 text-xs" : "text-sm"
            }`}
          >
            <span>{t("totalTokenUsage")}{message.token_number?.total_token}</span>
            <span>
              {t("completionTokenUsage")}{message.token_number?.completion_tokens}
            </span>
            <span>
              {t("promptTokenUsage")}{message.token_number?.prompt_tokens}
            </span>
          </div>
        )}
    </div>
  );
};
export default MarkdownDisplay;
