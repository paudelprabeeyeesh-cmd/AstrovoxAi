import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { MermaidDiagram } from "./MermaidDiagram";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          /* noop */
        }
      }}
      className="absolute right-2 top-2 inline-flex items-center gap-1 rounded-md border border-border bg-card/80 px-2 py-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
      aria-label="Copy code"
    >
      {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export function Markdown({ content }: { content: string }) {
  return (
    <div className="prose-astro">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          code(props) {
            const { children, className, node, ...rest } = props as {
              children?: React.ReactNode;
              className?: string;
              node?: unknown;
            };
            void node;
            const match = /language-(\w+)/.exec(className || "");
            const codeText = String(children ?? "").replace(/\n$/, "");
            const isBlock = match || codeText.includes("\n");
            if (!isBlock) {
              return (
                <code className={className} {...rest}>
                  {children}
                </code>
              );
            }
            if (match?.[1] === "mermaid") {
              return <MermaidDiagram code={codeText} />;
            }
            return (
              <div className="relative my-3">
                <CopyButton text={codeText} />
                <SyntaxHighlighter
                  language={match?.[1] ?? "text"}
                  style={oneDark}
                  PreTag="div"
                  customStyle={{
                    margin: 0,
                    padding: "1rem",
                    background: "oklch(0.18 0.02 270)",
                    fontSize: "0.85rem",
                    borderRadius: "0.85rem",
                  }}
                >
                  {codeText}
                </SyntaxHighlighter>
              </div>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}