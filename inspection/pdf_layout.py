"""Single-pass adapter for pinned pypdf 6.10.0 layout extraction.

Uses the same layout stages and defaults as PageObject._layout_mode_text.
Font objects are read-only during these stages; cache lifetime is one document.
No global monkeypatches, cross-document cache, disk cache or text truncation.
"""
from collections import OrderedDict


def layout_text_and_operations(page, font_cache):
    from pypdf import __version__
    from pypdf._font import Font
    from pypdf._text_extraction import _layout_mode
    from pypdf.generic import ContentStream
    if __version__ != '6.10.0':
        # Keep the public API as a correctness fallback after dependency changes.
        text=(page.extract_text(extraction_mode='layout') or '').strip()
        stream=page.get_contents()
        return text,stream.operations if stream is not None else []
    fonts={};node=page
    # Match pypdf's resource inheritance and alias overwrite order exactly.
    while node is not None:
        try:resources=node['/Resources']
        except KeyError:resources={}
        if '/Font' in resources and page.pdf is not None:
            for name in resources['/Font']:
                resource=resources['/Font'][name]
                key=id(resource)
                if key not in font_cache:
                    font_cache[key]=Font.from_font_resource(resource)
                    if len(font_cache)>64:font_cache.popitem(last=False)
                else:font_cache.move_to_end(key)
                fonts[name]=font_cache[key]
        try:node=node['/Parent'].get_object()
        except KeyError:node=None
    operations=ContentStream(page['/Contents'].get_object(),page.pdf,'bytes').operations
    groups=_layout_mode.text_show_operations(iter(operations),fonts,True,None)
    if not groups:return '',operations
    rows=_layout_mode.y_coordinate_groups(groups,None)
    width=_layout_mode.fixed_char_width(groups,1.25)
    return _layout_mode.fixed_width_page(rows,width,True,1).strip(),operations


def document_font_cache():
    return OrderedDict()
