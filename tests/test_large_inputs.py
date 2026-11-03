import unittest,io,base64,tempfile
from pathlib import Path
from unittest.mock import patch,MagicMock
from PIL import Image,ImageDraw
from pypdf import PdfWriter,PdfReader
from inspection import hwp_images as hi,documents

def decode(url):return Image.open(io.BytesIO(base64.b64decode(url.split(',',1)[1])))

class LargeInputTests(unittest.TestCase):
    def test_large_resolution_preserves_full_frame_and_aspect(self):
        image=Image.new('RGB',(6756,4216),'white');draw=ImageDraw.Draw(image)
        draw.rectangle((0,0,500,500),fill='red');draw.rectangle((6256,3716,6755,4215),fill='blue')
        data=io.BytesIO();image.save(data,format='PNG')
        output=decode(hi.image_url(data.getvalue()))
        self.assertEqual(max(output.size),hi.MAX_IMAGE_EDGE)
        self.assertAlmostEqual(output.width/output.height,6756/4216,places=3)
        self.assertEqual(output.getpixel((2,2)),(255,0,0));self.assertEqual(output.getpixel((output.width-3,output.height-3)),(0,0,255))
    def test_source_larger_than_old_byte_limit_is_normalized(self):
        data=io.BytesIO();Image.new('RGB',(2100,1400),'green').save(data,format='BMP')
        self.assertGreater(len(data.getvalue()),8*1024*1024)
        output=decode(hi.image_url(data.getvalue()))
        self.assertEqual(output.size,(2100,1400));self.assertEqual(output.getpixel((100,100)),(0,128,0))
    def test_reencoded_transfer_size_bounded_without_cutting_frame(self):
        import random
        data=io.BytesIO();image=Image.frombytes('RGB',(700,500),random.Random(42).randbytes(700*500*3));image.save(data,format='PNG')
        with patch.object(hi,'MAX_IMAGE_BYTES',400000):url=hi.image_url(data.getvalue())
        encoded=base64.b64decode(url.split(',',1)[1]);self.assertLessEqual(len(encoded),400000)
        self.assertEqual(decode(url).size,(700,500))
    def test_resize_preserves_transparency(self):
        image=Image.new('RGBA',(4200,200),(0,0,0,0));ImageDraw.Draw(image).rectangle((2000,0,4199,199),fill=(10,40,90,255))
        data=io.BytesIO();image.save(data,format='PNG');output=decode(hi.image_url(data.getvalue()))
        self.assertEqual(output.mode,'RGBA');self.assertEqual(output.getpixel((0,0))[3],0);self.assertEqual(output.getpixel((output.width-2,1))[3],255)
    def test_multiframe_error_distinguished_from_resource_limit(self):
        data=io.BytesIO();Image.new('RGB',(10,10),'red').save(data,format='GIF',save_all=True,append_images=[Image.new('RGB',(10,10),'blue')])
        with self.assertRaisesRegex(ValueError,'여러 장'):hi.image_url(data.getvalue())
        image=io.BytesIO();Image.new('RGB',(20,20),'white').save(image,format='PNG')
        with patch.object(hi,'MAX_IMAGE_PIXELS',100):
            with self.assertRaisesRegex(ValueError,'해상도'):hi.image_url(image.getvalue())
    def make_pdf(self,folder,pages):
        path=Path(folder)/'synthetic.pdf';writer=PdfWriter()
        for _ in range(pages):writer.add_blank_page(width=300,height=400)
        with path.open('wb') as out:writer.write(out)
        return path
    def native(self,count,visual):
        native=MagicMock();native.__enter__.return_value.visual_text.side_effect=['가상 그림 설명 충분한 본문 '*4 if i<visual else None for i in range(count)]
        return native
    def test_visual_dominant_pdf_keeps_original_all_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            path=self.make_pdf(folder,10);original=path.read_bytes()
            with patch('inspection.documents.NativeVisualReader',return_value=self.native(10,9)),patch('inspection.documents.layout_text_and_operations',return_value=('가상 마지막 쪽 본문 '*4,[])),patch('pypdf.PdfWriter') as writer:
                result=documents.prepare_pdf(path);writer.assert_not_called()
            self.assertEqual(result.visual_pdf,original);self.assertEqual(result.visual_pages,tuple(range(1,11)))
            self.assertIn('가상 마지막 쪽 본문',result.local_text);self.assertIn('10→10',result.api_text)
            self.assertEqual(list(Path(folder).iterdir()),[path]);self.assertEqual(path.read_bytes(),original)
    def test_subset_resource_copy_failure_preserves_original_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            path=self.make_pdf(folder,5);writer=MagicMock();writer.write.side_effect=ValueError('synthetic resource clone failure')
            with patch('inspection.documents.NativeVisualReader',return_value=self.native(5,1)),patch('inspection.documents.layout_text_and_operations',return_value=('가상 텍스트 '*10,[])),patch('pypdf.PdfWriter',return_value=writer):
                result=documents.prepare_pdf(path)
            self.assertEqual(result.visual_pdf,path.read_bytes());self.assertEqual(result.visual_pages,(1,2,3,4,5));self.assertIn('5→5',result.api_text)
    def test_invalid_pdf_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'incomplete.pdf';path.write_bytes(b'%PDF-1.7\ntruncated')
            with self.assertRaisesRegex(ValueError,'PDF 구조'):documents.prepare_pdf(path)
