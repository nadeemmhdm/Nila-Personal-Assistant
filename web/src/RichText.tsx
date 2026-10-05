import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Convert only ++underline++ text, never enable arbitrary model-generated HTML.
function underline() {
  return (tree: any) => {
    function walk(node: any) {
      if (!node.children || ["code", "inlineCode"].includes(node.type)) return;
      node.children = node.children.flatMap((child: any) => {
        if (child.type !== "text") {
          walk(child);
          return [child];
        }
        const parts = child.value.split(/\+\+([^+\n]+)\+\+/g);
        return parts.map((value: string, i: number) =>
          i % 2
            ? {
                type: "emphasis",
                data: { hName: "u" },
                children: [{ type: "text", value }],
              }
            : { type: "text", value },
        );
      });
    }
    walk(tree);
  };
}
export function RichText({ text }: { text: string }) {
  return (
    <Markdown
      skipHtml
      remarkPlugins={[remarkGfm, underline]}
      components={{
        img: () => <em>[External image omitted]</em>,
        a: ({ children, href }) => (
          <a href={href} target="_blank" rel="noopener noreferrer">
            {children}
          </a>
        ),
      }}
    >
      {text}
    </Markdown>
  );
}
