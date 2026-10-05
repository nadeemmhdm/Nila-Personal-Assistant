"""Child-process parser with a timeout enforced by its parent. No network or model calls."""
import io,json,sys

def main():
    try:
        if sys.platform!='win32':
            import resource
            resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
        from pypdf import PdfReader
        raw=sys.stdin.buffer.read(5*1024*1024+1)
        if len(raw)>5*1024*1024:raise ValueError('Size')
        reader=PdfReader(io.BytesIO(raw),strict=True)
        if reader.is_encrypted or len(reader.pages)>100:raise ValueError('Encrypted or too many pages')
        pages=[];total=0
        for p in reader.pages:
            value=p.extract_text() or '';total+=len(value)
            if total>500000:raise ValueError('Too much text')
            pages.append(value)
        sys.stdout.buffer.write(json.dumps(pages,ensure_ascii=False).encode())
    except Exception:raise SystemExit(1)
