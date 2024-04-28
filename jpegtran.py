import ctypes
import ctypes.util
import platform

match platform.system():
    case 'Windows':
        jtrandllpath = ctypes.util.find_library('jpegtran.dll')
        j62dllpath = ctypes.util.find_library('jpeg62.dll')
    case 'Linux': ### not tested lol
        from os import getcwd
        import os.path
        jtrandllpath = ctypes.util.find_library('jpegtran.so') or \
                  os.path.join(getcwd(), 'jpegtran.so')
    case _:
        raise Exception(f'unimplemented support for platform {platform.system()}')

if (not jtrandllpath) or (not j62dllpath):
    raise Exception(f'unable to find jpegtran or jpeg62 library')

jpegtran = ctypes.CDLL(jtrandllpath)

components = {1: 'y', 2: 'cb', 3: 'cr'}
class Component(ctypes.Structure):
    _fields_ = [
        ('id', ctypes.c_int),
        ('h_samp_fac', ctypes.c_int),
        ('w_samp_fac', ctypes.c_int),
        ('block_width', ctypes.c_uint),
        ('block_height', ctypes.c_uint),
        ('dct_scaled_size', ctypes.c_int)]
    
    def __str__(self):
        return f'id:{components.get(self.id,"UNK")} hsampfac:{self.h_samp_fac} wsampfac:{self.w_samp_fac} blockw:{self.block_width} blockh:{self.block_height} dctscaledsize:{self.dct_scaled_size}'

colorspaces = {1: 'greyscale', 2: 'RGB', 3: 'YCbCr'}
class JpegHeader(ctypes.Structure):
    _fields_ = [
        ('height', ctypes.c_uint),
        ('width', ctypes.c_uint),
        ('num_components', ctypes.c_uint),
        ('colorspace', ctypes.c_uint),
        ('bitsofprecision', ctypes.c_uint),
        ('components', Component * 4),
        ]
    
    def __str__(self):
        return '\n'.join([
            f'height: {self.height}',
            f'width: {self.width}',
            f'num_components: {self.num_components}',
            f'colorspace: {colorspaces.get(self.colorspace, "unknown colorspace")}',
            f'bitsofprecision: {self.bitsofprecision}',
            f'components:\n' + '\n'.join(['\t' + str(self.components[c]) for c in range(self.num_components)])
            ])

# define read_jpeg_header args and return type
jpegtran.read_jpeg_header.restype = JpegHeader
jpegtran.read_jpeg_header.argtypes = (
    ctypes.POINTER(ctypes.c_ubyte),
    ctypes.c_size_t)

# define main args and return type
jpegtran.main.argtypes = (
    ctypes.c_int, # argv len
    ctypes.POINTER(ctypes.c_char_p), # argv array
    ctypes.POINTER(ctypes.c_ubyte), # src buffer
    ctypes.c_int, # src buffer len
    ctypes.POINTER(ctypes.c_ubyte), # drop buffer
    ctypes.c_int, # drop buffer len
    ctypes.c_bool) # round up partial MCUs
class Jpeg(ctypes.Structure):
    _fields_ = [
        ('bufptr', ctypes.POINTER(ctypes.c_ubyte)),
        ('buflen', ctypes.c_ulong),
        ('returncode', ctypes.c_ulong)]
jpegtran.main.restype = Jpeg

# define free_jpg args and return type
jpegtran.free_jpg.argtypes = (
    ctypes.POINTER(ctypes.c_ubyte),)
jpegtran.free_jpg.restype = ctypes.c_uint;

def read_header(buf: bytes) -> JpegHeader:
    return jpegtran.read_jpeg_header(
        (ctypes.c_ubyte * len(buf)).from_buffer_copy(buf), len(buf))

def crop(buf: bytes, h: int, w: int, h_off: int=0, w_off: int=0, round_up: bool = False) -> bytes:
    argv = [
        b'jpegtran',
        b'-perfect',
        b'-copy', b'all',
        # b'-optimize', # very slow
        b'-crop', f'{w}x{h}+{w_off}+{h_off}'.encode('utf-8'),
        ]

    out = jpegtran.main(
        len(argv), # argv len
        (ctypes.c_char_p * len(argv))(*argv), # argv
        (ctypes.c_ubyte * len(buf)).from_buffer_copy(buf), # src buffer
        len(buf), # src buffer len
        (ctypes.c_ubyte * 0).from_buffer_copy(bytes()), # drop buffer
        0, # drop buffer len
        round_up # round partial MCUs
        )
    
    if out.returncode != 0:
        raise Exception(f'bad jpegtran crop return code {out.returncode}')
    
    rv = bytes(ctypes.cast(out.bufptr, ctypes.POINTER(ctypes.c_ubyte * out.buflen)).contents)
    
    # dealloc jpg buf
    rv2 = jpegtran.free_jpg(
        out.bufptr)
    
    return rv

def drop(srcbuf: bytes, dropbuf: bytes, h_off: int = 0, w_off: int = 0) -> bytes:
    argv = [
        b'jpegtran',
        b'-perfect',
        b'-copy', b'all',
        # b'-optimize', # very slow
        b'-drop', f'+{w_off}+{h_off}'.encode('utf-8'), b'_DUMMY_',
    ]
    
    out = jpegtran.main(
        len(argv), # argv len
        (ctypes.c_char_p * len(argv))(*argv), # argv
        (ctypes.c_ubyte * len(srcbuf)).from_buffer_copy(srcbuf), # src buffer
        len(srcbuf), # src buffer len
        (ctypes.c_ubyte * len(dropbuf)).from_buffer_copy(dropbuf), # drop buffer
        len(dropbuf), # drop buffer len
        False # round partial MCUs
        )
    
    rv = bytes(ctypes.cast(out.bufptr, ctypes.POINTER(ctypes.c_ubyte * out.buflen)).contents)
    
    # dealloc jpg buf
    rv2 = jpegtran.free_jpg(
        out.bufptr)
    
    return rv

def round_up_mcu(x):
    return int(((x + 15) // 16) * 16)
