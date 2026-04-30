import { cn } from "@/lib/utils";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

const codeBlockStyle = {
  background: "#1e1e1e",
  whiteSpace: "pre-wrap" as const,
  wordBreak: "break-word" as const,
  borderRadius: "0.5rem",
  padding: "1rem",
  margin: "0.75rem 0",
  fontSize: "0.875rem",
};

interface CodeProps {
  className?: string;
  children?: React.ReactNode;
  [key: string]: unknown;
}

interface MarkdownComponentProps {
  children?: React.ReactNode;
  href?: string;
  [key: string]: unknown;
}

export const markdownComponents = {
  p: ({ children }: MarkdownComponentProps) => (
    <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>
  ),
  ul: ({ children }: MarkdownComponentProps) => (
    <ul className="list-disc list-outside pl-5 mb-2 space-y-1">
      {children}
    </ul>
  ),
  ol: ({ children }: MarkdownComponentProps) => (
    <ol className="list-decimal list-outside pl-5 mb-2 space-y-1">
      {children}
    </ol>
  ),
  li: ({ children }: MarkdownComponentProps) => (
    <li className="leading-relaxed">{children}</li>
  ),
  strong: ({ children }: MarkdownComponentProps) => (
    <strong className="font-semibold">{children}</strong>
  ),
  code: ({ className, children, ...props }: CodeProps) => {
    const match = /language-(\w+)/.exec(className || "");
    const isInline = !match && !className?.includes("language");

    if (isInline) {
      return (
        <code
          className={cn(
            "px-1.5 py-0.5 rounded text-xs font-mono",
            // Note: isUser context is handled by the parent component via className
            "bg-muted",
          )}
          {...props}
        >
          {children}
        </code>
      );
    }

    return (
      <SyntaxHighlighter
        style={vscDarkPlus as { [key: string]: React.CSSProperties }}
        language={match ? match[1] : "text"}
        PreTag="div"
        customStyle={codeBlockStyle}
      >
        {String(children).replace(/\n$/, "")}
      </SyntaxHighlighter>
    );
  },
  pre: ({ children }: MarkdownComponentProps) => <>{children}</>,
  h1: ({ children }: MarkdownComponentProps) => (
    <h1 className="text-lg font-bold mb-2">{children}</h1>
  ),
  h2: ({ children }: MarkdownComponentProps) => (
    <h2 className="text-base font-semibold mb-2">{children}</h2>
  ),
  h3: ({ children }: MarkdownComponentProps) => (
    <h3 className="text-sm font-semibold mb-1">{children}</h3>
  ),
  blockquote: ({ children }: MarkdownComponentProps) => (
    <blockquote className="border-l-2 pl-3 italic opacity-80 my-2">
      {children}
    </blockquote>
  ),
  a: ({ href, children }: MarkdownComponentProps) => (
    <a
      href={href}
      className="text-primary underline underline-offset-2 hover:opacity-80"
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
    </a>
  ),
};
