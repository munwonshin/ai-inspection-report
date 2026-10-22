"""Read SSE events and safely preview incomplete structured JSON in memory."""
import json

def events(response):
    lines=[]
    for raw in response:
        line=raw.decode('utf-8').rstrip('\r\n')
        if not line:
            if lines:
                data='\n'.join(lines);lines=[]
                if data!='[DONE]':yield json.loads(data)
        elif line.startswith('data:'):lines.append(line[5:].lstrip(' '))
    if lines and '\n'.join(lines)!='[DONE]':yield json.loads('\n'.join(lines))

def string_prefix(text,start):
    """Decode only complete characters, including escaped UTF-16 pairs."""
    out=[];i=start
    escapes={'n':'\n','r':'\r','t':'\t','b':'\b','f':'\f','"':'"','\\':'\\','/':'/'}
    while i<len(text):
        c=text[i];i+=1
        if c=='"':return ''.join(out),i,True
        if c=='\\':
            if i>=len(text):break
            c=text[i];i+=1
            if c=='u':
                if i+4>len(text):break
                try:v=int(text[i:i+4],16)
                except ValueError:break
                i+=4
                if 0xD800<=v<=0xDBFF:
                    if i+6>len(text) or text[i:i+2]!='\\u':break
                    try:low=int(text[i+2:i+6],16)
                    except ValueError:break
                    if not 0xDC00<=low<=0xDFFF:break
                    i+=6;v=0x10000+((v-0xD800)<<10)+low-0xDC00
                if 0xDC00<=v<=0xDFFF:break
                out.append(chr(v))
            elif c in escapes:out.append(escapes[c])
            else:break
        else:out.append(c)
    return ''.join(out),i,False

def preview(text):
    # Only top-level body fields are visible; evidence/JSON syntax stay hidden.
    result={};depth=0;i=0
    while i<len(text):
        c=text[i]
        if c in '{[':depth+=1;i+=1
        elif c in '}]':depth-=1;i+=1
        elif c=='"':
            key,end,closed=string_prefix(text,i+1);i=end
            if not closed:break
            j=i
            while j<len(text) and text[j].isspace():j+=1
            if depth==1 and j<len(text) and text[j]==':':
                j+=1
                while j<len(text) and text[j].isspace():j+=1
                if key in {'findings','actions'} and j<len(text) and text[j]=='"':
                    value,i,closed=string_prefix(text,j+1);result[key]=value
                    if not closed:break
        else:i+=1
    labels={'findings':'현장 점검·확인 사항','actions':'향후 조치요청 사항'}
    return '\n\n'.join(labels[k]+'\n'+result[k] for k in labels if result.get(k))
