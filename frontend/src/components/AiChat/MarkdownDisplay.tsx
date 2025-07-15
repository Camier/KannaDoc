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

      alert("无法自动复制，请按 Ctrl+C 复制选中内容");
      setTimeout(() => {
        document.body.removeChild(fallbackText);
      }, 100);
    }
  };

  return language ? (
    <div className="relative group">
      <div className="flex items-center justify-between mx-3 mt-2 mb-1  text-gray-500 text-xs font-medium tracking-wide">
        <div className="uppercase ">
          {language}
        </div>
        <button
          onClick={handleCopy}
          className="cursor-pointer flex items-center gap-1 hover:text-gray-800"
          aria-label="Copy"
        >
          {!copied ? (
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
                d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z"
              />
            </svg>
          ) : (
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
                d="M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0 1 18 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3 1.5 1.5 3-3.75"
              />
            </svg>
          )}

          {copied ? (
            <span className="text-xs">Copied!</span>
          ) : (
            <span className="text-xs">Copy</span>
          )}
        </button>
      </div>
      <code
        className={`${className} block p-4 rounded-3xl overflow-x-auto`}
        {...props}
      >
        {children}
      </code>
      {/* </pre> */}
    </div>
  ) : (
    <code className="px-1 py-0.5 rounded-3xl" {...props}>
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
  const [copiedAll, setCopiedAll] = useState(false);
  const [hideThinking, setHideThinking] = useState(false);

  // 复制全部内容的处理函数
  const handleCopyAll = async () => {
    // 直接使用原始的md_text（base64编码之前的内容）
    try {
      await navigator.clipboard.writeText(md_text);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    } catch (err) {
      // 降级方案：使用textarea
      const textArea = document.createElement("textarea");
      textArea.value = md_text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    }
  };

  return (
    <div className="flex flex-col w-full gap-2">
      <div
        className={`${
          message.from === "user"
            ? "bg-indigo-300 shadow-lg px-5 py-3 text-gray-800 rounded-3xl "
            : ""
        } prose dark:prose-invert max-w-full ${
          isThinking
            ? "border-l-2 border-gray-200 p-4 bg-gray-100 text-gray-800 rounded-3xl text-sm mb-4"
            : "text-base"
        }`}
      >
        {isThinking && (
          <div
            className="flex items-center justify-start gap-1 cursor-pointer"
            onClick={() => setHideThinking((prev) => !prev)}
          >
            <div className="font-semibold text-gray-800">💡 Deep Thinking</div>
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
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>
        )}
        {!hideThinking &&
          (message.from === "ai" ? (
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
                      className="text-indigo-600 hover:text-indigo-800"
                    >
                      {children}
                    </a>
                  );
                },
                // 添加图片处理组件
                // 修改img组件处理逻辑
                img({ node, src, alt, title, style, width, height, ...props }) {
                  if (!src) {
                    return;
                  } else {
                    const newsrc = base64Processor.decode(src);
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
                  .replace(/\\\[/g, "$$$$") // 匹配 \\[ → $$
                  .replace(/\\\]/g, "$$$$") // 匹配 \\] → $$
                  // 行内公式替换
                  .replace(/\\\(/g, "$") // 匹配 \\( → $
                  .replace(/\\\)/g, "$") // 匹配 \\) → $
              )}
            </ReactMarkdown>
          ) : (
            <div className="whitespace-pre-wrap">{md_text}</div>
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
            <span>Total token usage: {message.token_number?.total_token}</span>
            <span>
              Completion token usage: {message.token_number?.completion_tokens}
            </span>
            <span>
              Prompt token usage: {message.token_number?.prompt_tokens}
            </span>
          </div>
        )}
      {/* 复制全部按钮 - 只在非思考状态下显示 */}
      {!isThinking && (
        <div
          className={`flex justify-start ${
            message.from === "user" ? "ml-auto pr-4" : "mr-auto"
          }`}
        >
          <button
            onClick={handleCopyAll}
            className="cursor-pointer flex items-center gap-0.5 text-gray-600 hover:text-gray-800 transition-colors"
            aria-label="Copy all content"
          >
            {copiedAll ? (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className="w-5 h-5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0 1 18 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3 1.5 1.5 3-3.75"
                />
              </svg>
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className="w-5 h-5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z"
                />
              </svg>
            )}
            <span className="text-sm">{copiedAll ? "Copied!" : "Copy"}</span>
          </button>
        </div>
      )}
    </div>
  );
};
export default MarkdownDisplay;
