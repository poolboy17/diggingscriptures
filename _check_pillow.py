try:
    from PIL import Image
    print('Pillow OK')
except ImportError:
    print('NEED_INSTALL')
