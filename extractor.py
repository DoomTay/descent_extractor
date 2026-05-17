import os
import re
import sys
import io
import json
import wave
from PIL import Image

output_raw = True
output_textures = False
output_palettes = False
output_backgrounds = False
output_models = False
output_sounds = True
output_briefings = False
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
        sound_length = int.from_bytes(os.read(f, 4), byteorder=sys.byteorder)
        file_offset += 4
        sound_data_length = int.from_bytes(os.read(f, 4), byteorder=sys.byteorder)
        file_offset += 4
        sound_offset = int.from_bytes(os.read(f, 4), byteorder=sys.byteorder)
        file_offset += 4
        
        sound = {
            "name": sound_name,
            "length": sound_length,
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

if output_surfaces:
    for row in filter(lambda hfile: hfile['type'] == "bbm", hog_files):
        print(f"converting {row['file_name']}")

        main_offset = 0
        chunkID = row["data"][main_offset:main_offset + 4].decode('latin1')
        main_offset += 4
        if chunkID != "FORM":
            print("Expected FORM chunkID")
        lenChunk = int.from_bytes(row["data"][main_offset:main_offset + 4], byteorder="big")
        main_offset += 4
        formatID = row["data"][main_offset:main_offset + 4].decode('latin1')
        main_offset += 4
        if formatID != "PBM ":
            print("Expected PBM formatID")
        content = row["data"][main_offset:main_offset + lenChunk - 4]
        main_offset += lenChunk - 4
        if lenChunk % 2:
            main_offset += 1

        offset = 0
        bmhd = {}
        pal = None
        x = 0
        y = 0
        while offset < len(content):
            chunkID = content[offset:offset + 4].decode('latin1')
            offset += 4
            lenChunk = int.from_bytes(row["data"][offset:offset + 4], byteorder="big")
            offset += 4

            match chunkID:
                case "BMHD":
                    bmhd["width"] = int.from_bytes(content[offset:offset + 2], byteorder="big")
                    offset += 2
                    bmhd["height"] = int.from_bytes(content[offset:offset + 2], byteorder="big")
                    offset += 2
                    bmhd["xOrigin"] = int.from_bytes(content[offset:offset + 2], byteorder="big")
                    offset += 2
                    bmhd["yOrigin"] = int.from_bytes(content[offset:offset + 2], byteorder="big")
                    offset += 2
                    bmhd["numPlanes"] = content[offset]
                    offset += 1
                    bmhd["mask"] = content[offset]
                    offset += 1
                    bmhd["compression"] = content[offset]
                    offset += 1
                    bmhd["pad1"] = content[offset]
                    offset += 1
                    bmhd["transClr"] = int.from_bytes(content[offset:offset + 2], byteorder="big")
                    offset += 2
                    bmhd["xAspect"] = content[offset]
                    offset += 1
                    bmhd["yAspect"] = content[offset]
                    offset += 1
                    bmhd["pageWidth"] = int.from_bytes(content[offset:offset + 2], byteorder="big")
                    offset += 2
                    bmhd["pageHeight"] = int.from_bytes(content[offset:offset + 2], byteorder="big")
                    offset += 2
        
                    # Validate only what we support
                    if (bmhd["numPlanes"] != 8 or bmhd["mask"] != 2 or bmhd["compression"] != 0):
                        print("Unsupported BMHD format")
                        break
                case "CMAP":
                    pal = content[offset:offset + 256 * 3]
                    offset += 256 * 3
                case "GRAB":
                    offset += 4
                case "CRNG":
                    offset += 8
                case "TINY":
                    width = int.from_bytes(content[offset:offset + 2], byteorder="big")
                    offset += 2
                    height = int.from_bytes(content[offset:offset + 2], byteorder="big")
                    offset += 2
                    offset += width * height
                case "BODY":
                    png_data = bytearray(bmhd["width"] * bmhd["height"] * 4)
                    
                    for i in range(bmhd["width"] * bmhd["height"]):
                        idx = content[offset]
                        offset += 1
                        
                        png_data[i * 4 + 0] = pal[idx * 3 + 0]
                        png_data[i * 4 + 1] = pal[idx * 3 + 1]
                        png_data[i * 4 + 2] = pal[idx * 3 + 2]
                        png_data[i * 4 + 3] = 0 if idx == bmhd["transClr"] else 255
                    
                    image = Image.frombytes("RGBA", (bmhd["width"], bmhd["height"]), bytes(png_data))
                    image.save('./converted/surfaces/' + row['file_name'][:-4] + '.png', format="png")
                    
                    break
                case _:
                    print(f"Unhandled sub chunk: {chunkID}")
                    break

        chunkID = row["data"][main_offset:main_offset + 4].decode('latin1')
        main_offset += 4

FT_COLOR = 1
FT_PROPORTIONAL = 2
FT_KERNED = 4
    
if output_font:
    for row in filter(lambda hfile: hfile['type'] == "fnt", hog_files):
        print(f'converting {row["file_name"]}')

        offset = 0

        sig = row["data"][offset:offset + 4].decode('latin1')
        offset += 4
        if sig != "PSFN":
            raise ValueError('Expected "PSFN" signature')

        data_size = int.from_bytes(row["data"][offset:offset + 4], byteorder="little")
        offset += 4

        fnt = {}
        fnt['ft_w'] = int.from_bytes(row["data"][offset:offset + 2], byteorder="little")
        offset += 2
        fnt['ft_h'] = int.from_bytes(row["data"][offset:offset + 2], byteorder="little")
        offset += 2
        fnt['ft_flags'] = int.from_bytes(row["data"][offset:offset + 2], byteorder="little")
        offset += 2
        fnt['ft_baseline'] = int.from_bytes(row["data"][offset:offset + 2], byteorder="little")
        offset += 2
        fnt['ft_minchar'] = row["data"][offset]
        offset += 1
        fnt['ft_maxchar'] = row["data"][offset]
        offset += 1
        fnt['ft_bytewidth'] = int.from_bytes(row["data"][offset:offset + 2], byteorder="little")
        offset += 2
        fnt['ft_data'] = int.from_bytes(row["data"][offset:offset + 4], byteorder="little") + 8
        data = row['data'][fnt['ft_data']:]
        offset += 4
        fnt['ft_chars'] = int.from_bytes(row["data"][offset:offset + 4], byteorder="little")
        offset += 4
        fnt['ft_widths'] = int.from_bytes(row["data"][offset:offset + 4], byteorder="little") + 8
        widths_data = row['data'][fnt['ft_widths']:]
        offset += 4
        fnt['ft_kerndata'] = int.from_bytes(row["data"][offset:offset + 4], byteorder="little") + 8
        kern_data = row['data'][fnt['ft_kerndata']:]
        offset += 4
        
        fnt['widths'] = []
        if fnt['ft_flags'] & FT_PROPORTIONAL:
            for i in range(fnt['ft_maxchar'] - fnt['ft_minchar'] + 1):
                fnt['widths'].append(int.from_bytes(widths_data[i * 2:(i * 2) + 2], byteorder="little"))
        
        fnt['kerns'] = []
        if fnt['ft_flags'] & FT_KERNED:
            kernOffset = 0
            nextByte = kern_data[kernOffset]
            kernOffset += 1
            while nextByte != 0xFF:
                secondChar = kern_data[kernOffset]
                kernOffset += 1
                newWidth = kern_data[kernOffset]
                kernOffset += 1
                fnt['kerns'].append({
                    'firstChar': nextByte,
                    'secondChar': secondChar,
                    'newWidth': newWidth
                })
                nextByte = kern_data[kernOffset]
                kernOffset += 1

        # Font definition file
        of = open('./converted/fonts/' + row['file_name'][:-4] + '.json', 'w', encoding='utf-8')
        of.write(json.dumps(fnt))
        of.close()

        # Font palette
        palette = []
        if fnt['ft_flags'] & FT_COLOR:
            palOffset = len(row['data']) - 256 * 3
            
            for i in range(256):
                byte_r = row['data'][palOffset + i * 3 + 0] * 4
                byte_g = row['data'][palOffset + i * 3 + 1] * 4
                byte_b = row['data'][palOffset + i * 3 + 2] * 4
                
                palette.extend([byte_r, byte_g, byte_b, 255])
                
            palette[255*4 + 3] = 0
            
            image = Image.frombytes("RGBA", (16, 16), bytes(palette))
            image.save('./converted/fonts/' + row['file_name'] + '.256.png', format="png")

        # Font texture
        if palette:
            texW = sum(fnt["widths"])
            png_data = bytearray(texW * fnt['ft_h'] * 4)
            dataOffset = 0
            xOffset = 0

            for c in range(fnt['ft_minchar'],fnt['ft_maxchar'] + 1):
                cid = c - fnt['ft_minchar']
                w = fnt['widths'][cid]
                for y in range(fnt['ft_h']):
                    for x in range(w):
                        col = data[dataOffset]
                        dataOffset += 1
                        k = y * texW + xOffset + x
                        
                        png_data[k * 4 + 0] = palette[col * 4 + 0]
                        png_data[k * 4 + 1] = palette[col * 4 + 1]
                        png_data[k * 4 + 2] = palette[col * 4 + 2]
                        png_data[k * 4 + 3] = palette[col * 4 + 3]
                        
                xOffset += w
                            
            image = Image.frombytes("RGBA", (texW, fnt['ft_h']), bytes(png_data))
            image.save('./converted/fonts/' + row['file_name'] + '.png', format="png")
            
        else:
            texW = sum(fnt["widths"])
            png_data = bytearray(texW * fnt['ft_h'] * 4)
            dataOffset = 0
            xOffset = 0
            byte = 0
            bit = 0

            for c in range(fnt['ft_minchar'],fnt['ft_maxchar']):
                cid = c - fnt['ft_minchar']
                w = fnt['widths'][cid]
                for y in range(fnt['ft_h']):
                    for x in range(w):
                        if (bit == 0):
                            byte = data[dataOffset]
                            dataOffset += 1
                        col = byte & (0x80 >> bit)
                        bit = (bit + 1) % 8
                        k = y * texW + xOffset + x
                        if col:
                            png_data[k * 4 + 0] = 255
                            png_data[k * 4 + 1] = 255
                            png_data[k * 4 + 2] = 255
                            png_data[k * 4 + 3] = 255
                        else:
                            png_data[k * 4 + 0] = 0
                            png_data[k * 4 + 1] = 0
                            png_data[k * 4 + 2] = 0
                            png_data[k * 4 + 3] = 0
                    bit = 0
                xOffset += w
            
            image = Image.frombytes("RGBA", (texW, fnt['ft_h']), bytes(png_data))
            image.save('./converted/fonts/' + row['file_name'] + '.png', format="png")
            
if output_sounds:
    sounds_blob = io.BytesIO(sound_data_stream)
    
    for sound in sounds:
        
        true_offset = sound["offset"] - sounds[0]["offset"]
        
        sounds_blob.seek(true_offset)
        
        # SOSCODEC header stuff. Probably wasn't parsed right
        # header_stuff = sounds_blob.read(8)
        
        sound_data = sounds_blob.read(sound["data_length"])
                
        if output_raw:
            of = open('./output/' + sound["name"] + '.snd', 'wb')
            of.write(sound_data)
            of.close()
                        
        # Not sure we'll need this yet
        converted_data = bytearray()
        scan_pos = 0
        
        print(sound)
        
        with wave.open('./converted/sounds/' + sound["name"] + '.wav', 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(1)
            wav.setframerate(11025)
            
            # wav.writeframesraw(sound_data)
            
            for byte in sound_data:                
                s = (byte & 0xF) * 16
                if s < 128: s = 127 - s
                wav.writeframes(bytes([s]))

                s = ((byte >> 4) & 0xF) * 16
                if s < 128: s = 127 - s
                wav.writeframes(bytes([s]))
                
print("Done")
