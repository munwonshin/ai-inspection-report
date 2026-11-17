"""Single-pass adapter for pinned pypdf 6.10.0 layout extraction.

Uses the same layout stages and defaults as PageObject._layout_mode_text.
Font objects are read-only during these stages; cache lifetime is one document.
No global monkeypatches, cross-document cache, disk cache or text truncation.
"""
from collections import OrderedDict


def layout_text_and_operations(page, font_cache):
    from pypdf import __version__
    if __version__ != '6.10.0':
        return public_layout(page)
    try:
        from pypdf._font import Font
        from pypdf._text_extraction import _layout_mode
        from pypdf.generic import ContentStream
        for name in ('text_show_operations','y_coordinate_groups','fixed_char_width','fixed_width_page'):
            if not callable(getattr(_layout_mode,name,None)):return public_layout(page)
        if not callable(getattr(Font,'from_font_resource',None)):return public_layout(page)
    except (ImportError,AttributeError):
        return public_layout(page)
    try:return pinned_layout(page,font_cache,Font,_layout_mode,ContentStream)
    except (ImportError,AttributeError,TypeError):
        # Incompatible internals must not make an otherwise readable PDF fail.
        font_cache.clear()
        return public_layout(page)


def public_layout(page):
    try:text=page.extract_text(extraction_mode='layout') or ''
    except TypeError:text=page.extract_text() or ''
    stream=page.get_contents()
    return text.strip(),stream.operations if stream is not None else []


def pinned_layout(page,font_cache,Font,_layout_mode,ContentStream):
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
