import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Convert only ++underline++ text, never enable arbitrary model-generated HTML.
function underline() {
  return (tree: any) => {
    function walk(node: any) {
      if (!node.children || ["code", "inlineCode"].includes(node.type)) return;
      const tokens:any[]=[];
      for(const child of node.children){
        if(child.type!=="text"){walk(child);tokens.push(child);continue}
        child.value.split(/(\+\+)/g).forEach((value:string)=>{if(value)tokens.push(value==='++'?{type:'underlineDelimiter'}:{type:'text',value})});
      }
      const result:any[]=[];
      for(let i=0;i<tokens.length;i++){
        if(tokens[i].type!=='underlineDelimiter'){result.push(tokens[i]);continue}
        const end=tokens.findIndex((x:any,j:number)=>j>i&&x.type==='underlineDelimiter');
        if(end>i+1){result.push({type:'emphasis',data:{hName:'u'},children:tokens.slice(i+1,end)});i=end}
        else result.push({type:'text',value:'++'});
      }
      node.children=result;
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
