import unittest,struct,io,tempfile,json,base64
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from test_hwp_direct import compound,rec,text
from inspection import documents,hwp_direct as h,hwp_images as hi,metadata,api

def descriptor(ext='png',ident=1):return struct.pack('<HHH',1,ident,len(ext))+ext.encode('utf-16le')
def picture(ident=1):
    p=bytearray(78);struct.pack_into('<H',p,71,ident)
    return rec(71,1,b' osg')+rec(76,2,b'cip$cip$')+rec(85,3,p)
def raster(fmt='PNG'):
    out=io.BytesIO();Image.new('RGB',(96,64),'blue').save(out,format=fmt);return out.getvalue()

class HwpImagesTests(unittest.TestCase):
    def prepared(self,data):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'synthetic.hwp';p.write_bytes(data)
            with patch('inspection.hwp_input.convert_pdf',side_effect=AssertionError('Conversion forbidden')),patch('win32com.client.DispatchEx',side_effect=AssertionError('Hancom forbidden')):
                result=documents.prepare_hwp(p)
            self.assertEqual(p.read_bytes(),data);self.assertEqual(len(list(Path(folder).iterdir())),1)
            return result
    def test_png_bmp_jpeg_svg_reach_metadata_and_draft_without_pdf(self):
        for ext,raw in [('png',raster()),('bmp',raster('BMP')),('jpg',raster('JPEG')),('svg',b'<svg xmlns="http://www.w3.org/2000/svg" width="96" height="64"><rect width="96" height="64" fill="blue"/></svg>')]:
            with self.subTest(ext=ext):
                data=compound([text('가상 계획서')+picture()],1,descriptors=[descriptor(ext)],assets={'BIN0001.'+ext:raw})
                r=self.prepared(data);self.assertEqual(len(r.visual_pdf),2)
                self.assertEqual(r.visual_pdf[1]['type'],'input_image');self.assertIn('[HWP 그림 1]',r.api_text)
                response={'project':{'value':'가상 계획서','source':'plan','evidence':'가상 계획서','page':1,'reason':''}}
                with patch('inspection.api.request',return_value=(json.dumps(response),{})) as request:
                    metadata.extract('fake',r.original_bytes,1,('project',))
                    self.assertEqual(request.call_args.args[1]['input'][0]['content'][-1]['type'],'input_image')
                payload=api.build_payload(r.api_text,'가상 회의록',{},'초안',pdf_bytes=r.visual_pdf)
                self.assertEqual(payload['input'][0]['content'][-1]['type'],'input_image')
    def test_unused_images_not_sent_and_repeated_images_deduplicated(self):
        r=self.prepared(compound([text('가상')+picture()+picture(2)],descriptors=[descriptor(),descriptor(ident=2),descriptor(ident=3)],assets={'BIN0001.png':raster(),'BIN0002.png':raster(),'BIN0003.png':raster()}))
        self.assertEqual(len(r.visual_pdf),2);self.assertEqual(r.local_text.count('[HWP 그림 1]'),2)
    def test_equation_kept_as_original_text(self):
        eq='x = {a} over {b}'
        result=h.section_text(rec(71,1,b'deqe')+rec(88,2,struct.pack('<IH',0,len(eq))+eq.encode('utf-16le')))
        self.assertIn(eq,result)
    def test_background_image_not_omitted(self):
        border=bytes(32)+struct.pack('<I',2)+bytes(4)+struct.pack('<H',1)
        r=self.prepared(compound([text('가상')],descriptors=[descriptor()],assets={'BIN0001.png':raster()},docinfo_extra=rec(20,1,border)))
        self.assertIn('배경 그림',r.local_text);self.assertEqual(len(r.visual_pdf),2)
    def test_no_automatic_hancom_on_unsupported_content(self):
        with self.assertRaisesRegex(ValueError,'자동 실행하지 않았'):
            self.prepared(compound([text('가상')+rec(76,2,b'cer$cer$')]))
    def test_external_links_and_svg_resources_refused(self):
        with self.assertRaises(ValueError):hi.descriptor(struct.pack('<H',0)+bytes(20))
        for svg in (b'<svg width="10" height="10"><image href="file:///C:/private.png"/></svg>',b'<!DOCTYPE svg [<!ENTITY test SYSTEM "file:///secret">]><svg/>',b'<svg width="10" height="10"><style>@import "https://example.com/style";</style></svg>'):
            with self.assertRaises(ValueError):hi.svg_png(svg)
    def test_picture_crop_and_bad_reference_not_silently_ignored(self):
        p=bytearray(78);struct.pack_into('<8i',p,12,0,0,100,0,100,100,0,100);struct.pack_into('<4i',p,44,25,0,75,100);struct.pack_into('<H',p,71,1)
        ident,crop=hi.picture_reference(p);url=hi.image_url(raster(),crop)
        img=Image.open(io.BytesIO(base64.b64decode(url.split(',',1)[1])));self.assertEqual(img.size,(48,64))
        with self.assertRaisesRegex(ValueError,'참조'):
            self.prepared(compound([picture(2)],descriptors=[descriptor()],assets={'BIN0001.png':raster()}))
    def test_multiframe_and_image_limits(self):
        out=io.BytesIO();Image.new('RGB',(20,20),'red').save(out,format='GIF',save_all=True,append_images=[Image.new('RGB',(20,20),'blue')])
        with self.assertRaises(ValueError):hi.image_url(out.getvalue())
        with patch.object(hi,'MAX_IMAGE_PIXELS',100):
            with self.assertRaises(ValueError):hi.image_url(raster())
