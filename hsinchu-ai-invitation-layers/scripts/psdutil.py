import struct
from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer
from psd_tools.constants import Compression, Resource
from psd_tools.psd.image_resources import ImageResource

def new_psd(composite_rgb, dpi=300):
    psd = PSDImage.frompil(composite_rgb, compression=Compression.RLE)
    res = struct.pack('>IhhIhh', dpi << 16, 1, 2, dpi << 16, 1, 2)   # ppi, unit=cm display
    psd._record.image_resources[Resource.RESOLUTION_INFO] = ImageResource(key=Resource.RESOLUTION_INFO, data=res)
    return psd

def add_group(parent, name, slug):
    from psd_tools.api.layers import Group
    g = Group.new(parent, slug)
    g.name = name
    g._record.name = slug
    return g

def add_layer(parent, img, name, slug, top=0, left=0, visible=True, compression=Compression.RLE):
    """Append a pixel layer keeping RGBA alpha as real layer transparency (not a mask)."""
    psd = parent._psd if hasattr(parent, '_psd') and parent._psd is not None else parent
    rec, chans = PixelLayer._build_layer_record_and_channels(
        img, slug, left, top, compression,
        version=psd._record.header.version, depth=psd._record.header.depth)
    layer = PixelLayer(parent, rec, chans)
    parent.append(layer)
    layer.name = name            # writes the Unicode ('luni') name
    layer._record.name = slug    # ASCII legacy name instead of '?'
    layer.visible = visible
    return layer
