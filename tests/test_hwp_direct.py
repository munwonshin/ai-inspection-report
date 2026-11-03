import unittest,struct,zlib,tempfile,json
from pathlib import Path
from unittest.mock import patch
from inspection import hwp_direct as h,documents,metadata

def rec(tag,level,payload):
    size=len(payload)
    return struct.pack('<I',tag|(level<<10)|(min(size,4095)<<20))+(struct.pack('<I',size) if size>=4095 else b'')+payload

def text(s):return rec(67,1,(s+'\r').encode('utf-16le'))

def compound(sections,flags=0,binary=False,descriptors=(),assets=None,docinfo_extra=b''):
    import pythoncom
    pythoncom.CoInitialize()
    try:
        mem=pythoncom.CreateILockBytesOnHGlobal()
        st=pythoncom.StgCreateDocfileOnILockBytes(mem,4114,0)
        def write(parent,name,data):
            stream=parent.CreateStream(name,4114);stream.Write(data);stream.Commit(0)
        def encode(data):
            if not flags&1:return data
            c=zlib.compressobj(wbits=-15);return c.compress(data)+c.flush()
        header=bytearray(256);header[:18]=b'HWP Document File\x00';struct.pack_into('<II',header,32,0x05010000,flags)
        write(st,'FileHeader',bytes(header));write(st,'DocInfo',encode(rec(16,0,struct.pack('<H',len(sections))+bytes(24))+b''.join(rec(18,1,p) for p in descriptors)+docinfo_extra))
        body=st.CreateStorage('BodyText',4114,0)
        for i,s in enumerate(sections):write(body,'Section'+str(i),encode(s))
        body.Commit(0)
        if binary or assets:
            bins=st.CreateStorage('BinData',4114,0)
            for name,data in (assets or {}).items():write(bins,name,encode(data))
            bins.Commit(0)
        st.Commit(0);size=mem.Stat(1)[2];return mem.ReadAt(0,size)
    finally:pythoncom.CoUninitialize()

class DirectHwpTests(unittest.TestCase):
    def test_compressed_and_plain_whole_document_no_preview(self):
        for flag in (0,1):
            with self.subTest(flag=flag):
                result,count=h.read_snapshot(compound([text('첫 구역 과제'),text('마지막 구역 책임자 가상인')],flag))
                self.assertEqual(count,2);self.assertIn('마지막 구역 책임자 가상인',result)
    def test_table_addresses_and_merge_preserved(self):
        ctrl=rec(71,1,b' lbt')
        table=rec(77,2,struct.pack('<IHH',0,2,3)+bytes(20))
        cell=rec(72,2,bytes(8)+struct.pack('<HHHH',1,0,2,1)+bytes(18))
        result=h.section_text(ctrl+table+cell+rec(67,4,'가상 주관기관'.encode('utf-16le')))
        self.assertIn('2행 3열',result);self.assertIn('행 1, 열 2, 행병합 1, 열병합 2',result);self.assertIn('가상 주관기관',result)
    def test_controls_do_not_leak_binary_and_unicode_preserved(self):
        control=struct.pack('<H',11)+b'abcdef123456'+struct.pack('<H',11)
        self.assertEqual(h.paragraph('가상😀'.encode('utf-16le')+control+' 끝'.encode('utf-16le')),'가상😀 끝')
    def test_visual_unknown_and_binary_never_silently_discarded(self):
        for raw in (rec(85,2,b'image'),rec(999,2,b'unknown'),rec(71,1,b' osg')):
            with self.assertRaises(h.NeedsRendering):h.section_text(raw)
        self.assertIn('가상',h.read_snapshot(compound([text('가상')],binary=True))[0])
    def test_protected_files_not_rendered_or_bypassed(self):
        for bit in (1,2,4,8,10,13):
            with self.assertRaisesRegex(ValueError,'보안 HWP'):h.read_snapshot(compound([text('가상')],1<<bit))
    def test_corrupt_record_and_decompression_budget(self):
        for raw in (b'\x01',struct.pack('<I',67|(100<<20)),struct.pack('<I',67|(4095<<20))):
            with self.assertRaises(ValueError):list(h.records(raw))
        with self.assertRaises(ValueError):h.expand(zlib.compress(b'a'*1000)[2:-4],True,20)
    def test_hancom_trailer_validated_and_extended_records(self):
        raw=b'a'*5000;c=zlib.compressobj(wbits=-15);compressed=c.compress(raw)+c.flush()
        tail=struct.pack('<II',zlib.crc32(raw),len(raw))
        self.assertEqual(h.expand(compressed+tail,True),raw)
        with self.assertRaises(ValueError):h.expand(compressed+bytes(8),True)
        self.assertEqual(next(h.records(rec(67,1,raw)))[2],raw)
    def test_no_com_application_pdf_worker_or_temp_on_direct_path(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'가상.hwp';data=compound([text('가상 과제 전체')]);path.write_bytes(data)
            with patch('inspection.hwp_input.convert_pdf') as convert,patch('win32com.client.DispatchEx') as dispatch:
                result=documents.prepare_hwp(path)
                self.assertTrue(result.original_bytes.startswith(h.MARKER));self.assertIsNone(result.visual_pdf)
                convert.assert_not_called();dispatch.assert_not_called()
            self.assertEqual(list(Path(folder).iterdir()),[path]);self.assertEqual(path.read_bytes(),data)
    def test_no_fallback_for_unsupported_or_corruption(self):
        with patch.object(h,'prepare',side_effect=h.NeedsRendering),patch('inspection.hwp_input.convert_pdf',return_value='fallback') as convert:
            with self.assertRaises(h.NeedsRendering):documents.prepare_hwp('sample.hwp')
            convert.assert_not_called()
        with patch.object(h,'prepare',side_effect=ValueError('corrupt')),patch('inspection.hwp_input.convert_pdf') as convert:
            with self.assertRaises(ValueError):documents.prepare_hwp('sample.hwp')
            convert.assert_not_called()
    def test_metadata_uses_whole_text_and_section_evidence(self):
        raw=h.MARKER+'[HWP 구역 1]\n앞\n[HWP 구역 2]\n과제명 가상 후반 과제'.encode()
        response={'project':{'value':'가상 후반 과제','evidence':'과제명 가상 후반 과제','source':'plan','page':2,'reason':''}}
        with patch('inspection.api.request',return_value=(json.dumps(response),{})) as request:
            values,_=metadata.extract('fake',raw,2,('project',))
            self.assertEqual(values['project'],'가상 후반 과제')
            p=request.call_args.args[1];self.assertEqual(p['input'][0]['content'][0]['type'],'input_text')
            self.assertIn('HWP 구역 2',p['input'][0]['content'][0]['text']);self.assertIn('구역은 페이지가 아니다',p['instructions'])
