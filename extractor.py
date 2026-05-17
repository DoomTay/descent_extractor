import os
import re
import sys
import io
from PIL import Image

output_raw = True
output_textures = True
output_palettes = True
output_backgrounds = True
output_models = False
output_sounds = True
output_briefings = True
output_surfaces = False
output_font = True
output_maps = False

BM_FLAG_TRANSPARENT = 1
BM_FLAG_SUPER_TRANSPARENT = 2
BM_FLAG_NO_LIGHTING = 4
BM_FLAG_RLE = 8
BM_FLAG_PAGED_OUT = 16
BM_FLAG_RLE_BIG = 32
BM_FLAG_ABM = 64
BM_FLAG_LARGE = 128

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

textures = []
sounds = []

# Save palette
if output_palettes or output_textures:
    for row in filter(lambda hfile: hfile['type'] == "256", hog_files):
        palette_data = io.BytesIO(row['data'])
    
        converted_data = bytearray()
        temp_palette = []


        for i in range(256):
            byte_r = int.from_bytes(palette_data.read(1)) * 4
            byte_g = int.from_bytes(palette_data.read(1)) * 4
            byte_b = int.from_bytes(palette_data.read(1)) * 4
            
            print(f"Palette entry values: {byte_r}, {byte_g}, {byte_b}")
            
            temp_palette.extend([byte_r, byte_g, byte_b, 255])
        
        temp_palette[254*4 + 3] = 0
        temp_palette[255*4 + 3] = 0
        
        converted_data.extend(temp_palette)

        for l in range(34):
            for i in range(256):
                idx = int.from_bytes(palette_data.read(1))
                
                base = idx * 4
                converted_data.extend([
                    temp_palette[base + 0],
                    temp_palette[base + 1],
                    temp_palette[base + 2],
                    temp_palette[base + 3],
                ])
                
                

        row['image_data'] = converted_data
        
        if output_palettes:
            image = Image.frombytes("RGBA", (16, 16 * 35), bytes(converted_data))
            image.save('./converted/palettes/' + row['file_name'] + '.png', format="png")

        if row['file_name'] == "palette.256":
            palette = temp_palette

# Save sounds and textures
if output_sounds or output_textures:
    f = os.open("./input/DESCENT.PIG", os.O_RDONLY | getattr(os, 'O_BINARY', 0))
    info = os.fstat(f)
    
    file_offset = 0
    
    # In V1.4 onward, an offset was added for texture/sound data
    file_offset = int.from_bytes(os.read(f, 4), byteorder=sys.byteorder)
    os.lseek(f, file_offset, 0)
    
    num_textures = int.from_bytes(os.read(f, 4), byteorder=sys.byteorder)
    file_offset += 4
    num_sounds = int.from_bytes(os.read(f, 4), byteorder=sys.byteorder)
    file_offset += 4
    
    print(f"num_textures: {num_textures}")
    print(f"num_sounds: {num_sounds}")
    
    for i in range(num_textures):
        texture_name = os.read(f, 8).decode("latin1")
        texture_name = texture_name.split('\x00', 1)[0]
        file_offset += 8
        frame = int.from_bytes(os.read(f, 1))
        file_offset += 1
        texture_frame = frame & 0x3F
        texture_abmFlag = bool(frame & BM_FLAG_ABM)
        texture_largeFlag = bool(frame & BM_FLAG_LARGE)
        texture_xsize = int.from_bytes(os.read(f, 1))
        if(texture_largeFlag):
            texture_xsize += 256
        file_offset += 1
        texture_ysize = int.from_bytes(os.read(f, 1))
        file_offset += 1
        texture_flag = int.from_bytes(os.read(f, 1))
        file_offset += 1
        texture_ave_color = int.from_bytes(os.read(f, 1))
        file_offset += 1
        texture_offset = int.from_bytes(os.read(f, 4), byteorder=sys.byteorder)
        file_offset += 4
        
        texture = {
            "texture_name": texture_name,
            "frame": texture_frame,
            "abmFlag": texture_abmFlag,
            "xsize": texture_xsize,
            "ysize": texture_ysize,
            "flag": texture_flag,
            "ave_color": texture_ave_color,
            "offset": texture_offset
        }
        
        print(f"texture {texture}")
        textures.append(texture)
        
    for i in range(num_sounds):
        sound_name = os.read(f, 8).decode("latin1")
        sound_name = sound_name.split('\x00', 1)[0]
        file_offset += 8
        sound_nSamples = int.from_bytes(os.read(f, 4), byteorder=sys.byteorder)
        file_offset += 4
        sound_data_length = int.from_bytes(os.read(f, 4), byteorder=sys.byteorder)
        file_offset += 4
        sound_offset = int.from_bytes(os.read(f, 4), byteorder=sys.byteorder)
        file_offset += 4
        
        sound = {
            "name": sound_name,
            "nSamples": sound_nSamples,
            "data_length": sound_data_length,
            "offset": sound_offset
        }
        
        print(f"sound {sound}")
        sounds.append(sound)
            
    texture_data_stream = os.read(f,sounds[0]['offset'])
    file_offset += len(texture_data_stream)
    sound_data_stream = os.read(f,(info.st_size - file_offset))

def get_palette_color(idx):
    return (palette[idx * 4 + 0], palette[idx * 4 + 1], palette[idx * 4 + 2], palette[idx * 4 + 3])

if output_textures:    
    t = 0
    texture_blob = io.BytesIO(texture_data_stream)
    
    for texture in textures:
        raw_data = io.BytesIO()
        converted_data = bytearray()
        scan_pos = 0
        
        print(f"converting texture {texture}")
        ++t
        
        offset_in_stream = texture['offset']
        
        if texture_blob.tell() != offset_in_stream:
           raise ValueError(f"Current offset is {texture_blob.tell()} when it should be {offset_in_stream}")
        
        texture_blob.seek(offset_in_stream)
        
        is_compressed = bool(texture['flag'] & (BM_FLAG_RLE | BM_FLAG_RLE_BIG))
        
        if not is_compressed:
            for i in range(texture['xsize'] * texture['ysize']):
                current_byte = texture_blob.read(1)
                current_byte_int = int.from_bytes(current_byte, byteorder="little")
                
                idx_r,idx_g,idx_b,idx_a = get_palette_color(current_byte_int)
                
                raw_data.write(current_byte)
                
                converted_data.extend([idx_r,idx_g,idx_b,idx_a])
                
                scan_pos += 1
        elif texture['flag'] & BM_FLAG_RLE:
            size_int = texture_blob.read(4)
            raw_data.write(size_int)
                        
            texture_total_size = int.from_bytes(size_int, byteorder="little")
            texture['line_sizes'] = []
            
            for line in range(texture['ysize']):
                line_size_int = texture_blob.read(1)
                raw_data.write(line_size_int)
                
                texture['line_sizes'].append(int.from_bytes(line_size_int, byteorder="little"))
            
            data_size = sum(texture['line_sizes'])
                        
            if data_size != (texture_total_size - texture['ysize'] - 4):
                raise ValueError(f"Issue with {texture['texture_name']}: summed data size is {data_size} while parsed header indicates {texture_total_size - texture['ysize'] - 4}")
            
            for line_size in texture['line_sizes']:
                raw_bytes = texture_blob.read(line_size)
                
                raw_data.write(raw_bytes)
                
                i = 0
            
                while i < line_size:
                    control_byte = raw_bytes[i]
                    i += 1                    
                    if control_byte == 0xE0:
                        break
                    
                    if (control_byte & 0xE0) == 0xE0:
                        repeat = control_byte & 0x1F
                        if repeat:
                            byte = raw_bytes[i]
                            i += 1
                            
                            idx_r,idx_g,idx_b,idx_a = get_palette_color(byte)
                            
                            converted_data.extend([idx_r, idx_g, idx_b, idx_a] * repeat)
                            
                            scan_pos += repeat
                    else:
                        idx_r,idx_g,idx_b,idx_a = get_palette_color(control_byte)
                        
                        converted_data.extend([idx_r, idx_g, idx_b, idx_a])
                        
                        scan_pos += 1
            
        elif texture['flag'] & BM_FLAG_RLE_BIG:
            raise ValueError(f"Data for texture {texture['texture_name']} is compressed with BM_FLAG_RLE_BIG set, which is not supported at the moment")
            
        
        if output_raw:
            of = open('./output/' + texture['texture_name'] + "_" + str(texture['frame']) + ".bin", 'wb')
            of.write(raw_data.getvalue())
            of.close()
            
        
        expected_pixel_count = texture['xsize'] * texture['ysize']
        
        if scan_pos != expected_pixel_count:
            raise ValueError(f"Pixel count for {texture['texture_name']} was {scan_pos}, should be {expected_pixel_count}")
            
        image = Image.frombytes("RGBA", (texture['xsize'], texture['ysize']), bytes(converted_data))
        image.save('./converted/textures/' + texture['texture_name'] + "_" + str(texture['frame']) + '.png', format="png")
        
if output_briefings:
    for row in filter(lambda hfile: hfile['type'] == "txb", hog_files):
        print(f'converting {row["file_name"]}')
        
        output = ''
        for b in row["data"]:
            
            c = b  # get byte value
            
            if (c != 0x0a):
                c = (((c & 0x3f) << 2) + ((c & 0xc0) >> 6)) ^ 0xa7;
            output += chr(c)
        
        of = open('./converted/texts/' + row['file_name'][:-4] + '.txt', 'w', encoding='utf-8')
        of.write(output)
        of.close()

print("Done")
