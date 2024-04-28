from math import ceil
from os import scandir
import time

from jpegtran import read_header, round_up_mcu, crop, drop, colorspaces

# examples of the crop+drop functionality
def main():
    with open('./kreidefels_mit_leuchtturm.jpg', 'rb') as fh:
        srcbuf = fh.read()
    
    with open('./eindhovensche_golf.jpg', 'rb') as fh:
        dropbuf = fh.read()
    
    # round image dimensions to DCT/MCU boundaries
    # this is needed to not trim the right/bottom edges,
    # this introduces artifacting on images that are not already aligned,
    # this is reversable, however.
    srcheader = read_header(srcbuf)
    srcbuf = crop(srcbuf, srcheader.height, srcheader.width, round_up=True)
    srcheader = read_header(srcbuf)
    
    dropheader = read_header(dropbuf)
    dropbuf = crop(dropbuf, dropheader.height, dropheader.width, round_up=True)
    dropheader = read_header(dropbuf)
    
    # set width to widest of the 2
    max_w = max([srcheader.width, dropheader.width])
    
    # update src image to final dimensions
    srcbuf = crop(srcbuf, h=srcheader.height+dropheader.height, w=max_w)
    
    # drop image
    finalbuf = drop(srcbuf, dropbuf, h_off=srcheader.height, w_off=500)
    
    with open('./dropped.jpg', 'wb') as fh:
        fh.write(finalbuf)

if __name__ == '__main__':
    main()
