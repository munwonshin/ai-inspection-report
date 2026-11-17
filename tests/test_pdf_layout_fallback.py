import builtins,unittest
from unittest.mock import Mock,patch
from inspection import pdf_layout


class PdfLayoutFallbackTests(unittest.TestCase):
    def page(self):
        page=Mock();page.extract_text.return_value=' public text ';page.get_contents.return_value=None
        return page

    def test_other_version_does_not_import_internals(self):
        original=builtins.__import__;imports=[]
        def guarded(name,*args,**kw):
            imports.append(name)
            if name.startswith('pypdf._'):raise AssertionError('Internal import before version check')
            return original(name,*args,**kw)
        page=self.page()
        with patch('pypdf.__version__','99.0'),patch('builtins.__import__',side_effect=guarded):
            self.assertEqual(pdf_layout.layout_text_and_operations(page,{}),('public text',[]))

    def test_missing_internal_module_uses_public_api(self):
        original=builtins.__import__
        def guarded(name,*args,**kw):
            if name=='pypdf._font':raise ImportError('synthetic incompatibility')
            return original(name,*args,**kw)
        page=self.page()
        with patch('pypdf.__version__','6.10.0'),patch('builtins.__import__',side_effect=guarded):
            self.assertEqual(pdf_layout.layout_text_and_operations(page,{}),('public text',[]))

    def test_changed_signature_clears_partial_cache(self):
        page=self.page();cache={'partial':1}
        with patch('inspection.pdf_layout.pinned_layout',side_effect=TypeError('signature changed')):
            self.assertEqual(pdf_layout.layout_text_and_operations(page,cache),('public text',[]))
        self.assertEqual(cache,{})

    def test_old_public_signature_and_operations(self):
        page=self.page();page.extract_text.side_effect=[TypeError('no layout keyword'),' plain ']
        page.get_contents.return_value=Mock(operations=[('safe','op')])
        with patch('pypdf.__version__','older'):
            self.assertEqual(pdf_layout.layout_text_and_operations(page,{}),('plain',[('safe','op')]))
