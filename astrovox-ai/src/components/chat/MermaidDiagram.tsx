import { useEffect, useRef, useState, memo } from "react";

let mermaidPromise: Promise<typeof import("mermaid").default> | null = null;

async function loadMermaid() {
  if (!mermaidPromise) {
    mermaidPromise = import("mermaid").then((mod) => {
      const mermaid = mod.default;
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: "dark",
        fontFamily: "Inter, system-ui, sans-serif",
      });
      return mermaid;
    });
  }
  return mermaidPromise;
}

let idCounter = 0;

function MermaidDiagramImpl({ code }: { code: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setSvg(null);
    (async () => {
      try {
        const mermaid = await loadMermaid();
        const id = `mermaid-${++idCounter}-${Date.now()}`;
        const { svg } = await mermaid.render(id, code);
        if (!cancelled) setSvg(svg);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to render diagram");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [code]);

  if (error) {
    return (
      <div className="my-3 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm">
        <div className="font-medium text-destructive-foreground">Diagram error</div>
        <div className="mt-1 whitespace-pre-wrap text-xs text-muted-foreground">{error}</div>
        <pre className="mt-2 overflow-x-auto rounded bg-background/50 p-2 text-xs">{code}</pre>
      </div>
    );
  }

  if (!svg) {
    return (
      <div className="my-3 flex h-32 items-center justify-center rounded-lg border border-border/60 bg-card/50 text-xs text-muted-foreground">
        Rendering diagram…
      </div>
    );
  }

  return (
    <div
      ref={ref}
      className="my-3 overflow-x-auto rounded-lg border border-border/60 bg-card/40 p-3 [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-full"
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

export const MermaidDiagram = memo(MermaidDiagramImpl);