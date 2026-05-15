import os
import re
import sys
import io
from PIL import Image

output_raw = False
output_textures = False
output_palettes = False
output_backgrounds = True
output_models = False
output_sounds = False
output_briefings = False
output_surfaces = False
output_font = True
output_maps = False

hog_files = []

f = os.open("./input/DESCENT.HOG", os.O_RDONLY | getattr(os, 'O_BINARY', 0))
info = os.fstat(f)
sig = os.read(f, 3).decode("latin1")

# print("File Info :", info)

if sig != "DHF":
    print("HOG file not DHF")
    exit(1)

file_offset = 3
while file_offset < info.st_size:
    # get filename and strip 0x00 and 0x16
    file_name = os.read(f, 13).decode('latin1')
    file_offset += 13

    # cut off everything after the null byte
    file_name = file_name.split('\x00', 1)[0]

    # get extension without dot
    file_type = os.path.splitext(file_name)[1][-3:]

    # f is at 16 now (3+13), read 4 bytes for a 32bit integer filesize
    file_size = os.read(f, 4);
    file_size = int.from_bytes(file_size, byteorder=sys.byteorder)
    file_offset += 4

    # file_offset += 4  The extracter node.js script pushes the offset further after every read.
    # in our python script, the read advances the filepointer, so the fileoffset is purely for the loop.

    file_data = os.read(f, file_size)
    file_offset += file_size

    print(file_name)

    file = {
        "file_name": file_name,
        "type": file_type,
        "file_size": file_size,
        "data": file_data
    }

    hog_files.append(file)

    if output_raw:
        of = open('./output/' + file_name, 'wb')
        of.write(file_data)
        of.close()


# Save PCX
if output_backgrounds:
    for row in filter(lambda hfile: hfile['type'] == "pcx", hog_files):
        image = Image.open(io.BytesIO(row['data']))
        image.save('./converted/backgrounds/' + row['file_name'][:-3] + 'png', format="png")

print("Done")
