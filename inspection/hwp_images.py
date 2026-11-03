"""Decode embedded raster pictures in memory; never follow external links."""
import base64,io,struct,warnings,re,xml.etree.ElementTree as ET

MAX_IMAGE_PIXELS=64_000_000
MAX_SOURCE_IMAGE_BYTES=64*1024*1024
MAX_IMAGE_BYTES=8*1024*1024
MAX_IMAGE_EDGE=4096
MAX_TOTAL_IMAGES=256

def descriptor(payload):
    if len(payload)<2:raise ValueError('HWP 그림 정보가 손상됐습니다.')
    flags=struct.unpack_from('<H',payload)[0];kind=flags&15;compression=(flags>>4)&3
    if kind!=1:
        raise ValueError('연결 그림 또는 OLE 자료는 직접 읽을 수 없습니다. 원본을 PDF로 저장해 첨부해 주세요. 한글은 자동 실행하지 않았습니다.')
    if len(payload)<6:raise ValueError('HWP 그림 정보가 잘렸습니다.')
    ident,length=struct.unpack_from('<HH',payload,2)
    if len(payload)<6+length*2 or not ident:raise ValueError('HWP 그림 식별 정보가 손상됐습니다.')
    ext=payload[6:6+length*2].decode('utf-16le').lower()
    if ext not in ('png','jpg','jpeg','jfif','bmp','gif','tif','tiff','webp','svg'):
        raise ValueError('직접 읽기 미지원 그림 형식입니다. 원본을 PDF로 저장해 첨부해 주세요. 한글은 자동 실행하지 않았습니다.')
    if compression==3:raise ValueError('HWP 그림 압축 설정이 올바르지 않습니다.')
    return ident,ext,compression

def svg_png(data):
    compact=data.replace(b'\x00',b'').lower()
    # A normal SVG PUBLIC doctype is discarded by ElementTree, never fetched.
    if b'<!entity' in compact or re.search(br'<!doctype[^>]*\[',compact):raise ValueError('외부 엔터티가 있는 SVG는 읽지 않습니다.')
    try:root=ET.fromstring(data)
    except ET.ParseError:raise ValueError('HWP SVG가 손상됐습니다.') from None
    for node in root.iter():
        tag=node.tag.rsplit('}',1)[-1].lower()
        if tag in ('script','foreignobject','animate','animatetransform','set'):raise ValueError('동적 SVG는 읽지 않습니다.')
        values=list(node.attrib.values())+([node.text] if node.text else [])
        for name,value in node.attrib.items():
            if name.rsplit('}',1)[-1].lower()=='href' and not value.startswith(('#','data:image/png;base64,','data:image/jpeg;base64,')):
                raise ValueError('외부 파일을 참조하는 SVG는 읽지 않습니다.')
            if name.rsplit('}',1)[-1].lower()=='href' and value.startswith('data:'):
                try:embedded=base64.b64decode(value.split(',',1)[1],validate=True)
                except (ValueError,IndexError):raise ValueError('SVG 내부 그림이 손상됐습니다.') from None
                image_url(embedded)
        for value in values:
            if '@import' in value.lower():raise ValueError('외부 스타일을 참조하는 SVG는 읽지 않습니다.')
            for url in re.findall(r'url\(\s*[\"\x27]?(.*?)[\"\x27]?\s*\)',value,re.I):
                if not url.strip('\"\x27 ').startswith('#'):raise ValueError('외부 리소스를 참조하는 SVG는 읽지 않습니다.')
    view=re.split(r'[\s,]+',root.get('viewBox','').strip())
    def length(value):
        m=re.fullmatch(r'\s*(\d+(?:\.\d+)?)(?:px)?\s*',value or '')
        return float(m[1]) if m else None
    width=length(root.get('width'));height=length(root.get('height'))
    if (not width or not height) and len(view)==4:
        try:width,height=float(view[2]),float(view[3])
        except ValueError:pass
    if not width or not height or not 0<width<=100000 or not 0<height<=100000:raise ValueError('SVG 크기를 확인할 수 없습니다.')
    scale=min(1,4096/max(width,height));width=max(1,round(width*scale));height=max(1,round(height*scale))
    from resvg_py import svg_to_bytes
    return svg_to_bytes(svg_string=ET.tostring(root,encoding='unicode'),width=width,height=height,resources_dir=None,log_information=False)

def image_url(data,crop=None,extension=''):
    from PIL import Image
    if len(data)>MAX_SOURCE_IMAGE_BYTES:raise ValueError('HWP 내부 그림 데이터가 안전한 처리 범위를 초과합니다.')
    if extension=='svg':
        if len(data)>MAX_IMAGE_BYTES:raise ValueError('HWP의 SVG 그림 데이터가 너무 큽니다.')
        data=svg_png(data)
    with warnings.catch_warnings():
        warnings.simplefilter('error',Image.DecompressionBombWarning)
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ('PNG','JPEG','BMP','GIF','TIFF','WEBP'):raise ValueError('지원하지 않는 그림 형식입니다.')
                if getattr(image,'n_frames',1)!=1:raise ValueError('여러 장으로 구성된 내부 그림입니다. 단일 그림 또는 PDF 사본으로 첨부해 주세요.')
                if image.width*image.height>MAX_IMAGE_PIXELS:raise ValueError('HWP 내부 그림의 해상도가 안전한 처리 한도를 초과합니다.')
                image.load()
                changed=False
                if crop is not None:
                    x0,y0,x1,y1=crop
                    if not 0<=x0<x1<=1 or not 0<=y0<y1<=1:raise ValueError('HWP 그림 잘림 범위를 확인할 수 없습니다. PDF로 첨부해 주세요.')
                    image=image.crop((round(image.width*x0),round(image.height*y0),round(image.width*x1),round(image.height*y1)))
                    changed=True
                if max(image.size)>MAX_IMAGE_EDGE:
                    image.thumbnail((MAX_IMAGE_EDGE,MAX_IMAGE_EDGE),Image.Resampling.LANCZOS,reducing_gap=3.0)
                    changed=True
                if not changed and len(data)<=MAX_IMAGE_BYTES and image.format in ('PNG','JPEG'):
                    mime='image/png' if image.format=='PNG' else 'image/jpeg'
                    return 'data:'+mime+';base64,'+base64.b64encode(data).decode('ascii')
                output=io.BytesIO();image.save(output,format='PNG');data=output.getvalue();mime='image/png'
                if len(data)>MAX_IMAGE_BYTES:
                    # Keep the entire picture. Flatten transparency on white before JPEG.
                    rgb=Image.new('RGB',image.size,'white')
                    if 'A' in image.getbands() or 'transparency' in image.info:
                        rgba=image.convert('RGBA');rgb.paste(rgba,mask=rgba.getchannel('A'))
                    else:rgb.paste(image.convert('RGB'))
                    for quality in (92,85):
                        output=io.BytesIO();rgb.save(output,format='JPEG',quality=quality);data=output.getvalue()
                        if len(data)<=MAX_IMAGE_BYTES:break
                    mime='image/jpeg'
                if len(data)>MAX_IMAGE_BYTES:raise ValueError('내부 그림 최적화 후에도 전송 크기 한도를 초과합니다. PDF 사본으로 첨부해 주세요.')
                return 'data:'+mime+';base64,'+base64.b64encode(data).decode('ascii')
        except ValueError:raise
        except Exception:raise ValueError('HWP 그림을 안전하게 읽지 못했습니다. PDF로 첨부해 주세요.') from None

def picture_reference(payload):
    if len(payload)<73:raise ValueError('HWP 그림 개체가 손상됐습니다.')
    ident=struct.unpack_from('<H',payload,71)[0]
    # HWP picture rectangle is in original image coordinates; cropping uses the same units.
    points=struct.unpack_from('<8i',payload,12);xs=points[::2];ys=points[1::2]
    left,top,right,bottom=struct.unpack_from('<4i',payload,44)
    crop=None
    if any((left,top,right,bottom)):
        width=max(xs)-min(xs);height=max(ys)-min(ys)
        if len(payload)>=90 and struct.unpack_from('<I',payload,78)[0]==0:
            width,height=struct.unpack_from('<II',payload,82)
        elif len(payload)>78:raise ValueError('HWP 그림 효과의 잘림 좌표를 확인할 수 없습니다. PDF로 첨부해 주세요.')
        if width<=0 or height<=0:raise ValueError('HWP 그림 좌표를 확인할 수 없습니다. PDF로 첨부해 주세요.')
        crop=(left/width,top/height,right/width,bottom/height)
        if crop==(0,0,1,1):crop=None
    return ident,crop
