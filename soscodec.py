codec_index_table = [-1,-1,-1,-1, 2, 4, 6, 8, -1,-1,-1,-1, 2, 4, 6, 8]

codec_step_table = [7, 8, 9, 10, 11, 12, 13, 14, 16,  17,  19,  21,  23,  25,  28, 31,  34,  37,  41,  45,  50,  55, 60,  66,  73,  80,  88,  97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963,1060,1166,1282,1411,1552, 1707,1878, 2066,2272,2499,2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,7132,7845,8630,9493,10442,11487,12635,13899,15289,16818,18500,20350,22385,24623,27086,29794,32767]

compression_info = {
    "source": 0,
    "dest": 0,
    "comp_size": 0,
    "sample_index": 0,
    "predicted": 0,
    "difference": 0,
    "code_buffer": 0,
    "code": 0,
    "step": 0,
    "index": 0,
    "bit_size": 0
}

codec_bytes_processed = 0
codec_byte_index = 0

def sos_codec_init_stream():
    compression_info["index"] = 0
    compression_info["step"] = 7
    compression_info["predicted"] = 0
    compression_info["sample_index"] = 0
    compression_info["source"] = 0
    compression_info["dest"] = 0

def sos_codec_decompress_data(audio_bytes):
    global codec_bytes_processed, codec_byte_index, compression_info

    def decomp_main_loop():
        nonlocal eax
        if (compression_info["sample_index"] & 1) == 0:
            decomp_fetch_token()
        else:
            eax = compression_info["code_buffer"] & 0xffff
            eax = (eax >> 4) & 0xf
            
            ax = eax & 0xffff
            compression_info["code"] = ax
                        
            decomp_calc_difference()
            
    def decomp_fetch_token():
        nonlocal esi, eax, audio_bytes
        eax = 0
        al = audio_bytes[esi] & 0xff
        eax = al
        ax = eax & 0xffff
        compression_info["code_buffer"] = ax
        esi += 1
        eax &= 0x000f
        ax = eax & 0xffff
        compression_info["code"] = ax
        
        decomp_calc_difference()
        
        
    def decomp_calc_difference():
        nonlocal eax,ecx
        compression_info["difference"] = 0
        ecx = compression_info["step"] & 0xffff
        
        if (eax & 4) == 0:
            decomp_no_4()
        else:
            compression_info["difference"] += ecx
            decomp_no_4()
            
    def decomp_no_4():
        nonlocal eax,ecx,edx
        if (eax & 2) == 0:
            decomp_no_2()
        else:
            edx = ecx
            edx = edx >> 1
            compression_info["difference"] += edx
            decomp_no_2()
            
    def decomp_no_2():
        nonlocal eax,ecx,edx
        if (eax & 1) == 0:
            decomp_no_1()
        else:
            edx = ecx
            edx = edx >> 2
            compression_info["difference"] += edx
            decomp_no_1()
            
    def decomp_no_1():
        nonlocal eax, ecx, edx
        edx = ecx
        edx = edx >> 3
        compression_info["difference"] += edx
        
        if (compression_info["code"] & 8) == 0:
            decomp_no_8()
        else:
            compression_info["difference"] = -compression_info["difference"]
            decomp_no_8()
            
    def decomp_no_8():    
        nonlocal eax
        eax = compression_info["predicted"]
        eax += compression_info["difference"]
        
        # was 0x7fff
        if(eax <= 32767):
            decomp_no_overflow()
        else:
            eax = 32767
            decomp_no_overflow()
            
    def decomp_no_overflow():
        nonlocal eax
        # was 0xffff8000
        if(eax >= -32768):
            decomp_no_underflow()
        else:
            eax = -32768
            decomp_no_underflow()
            
    def decomp_no_underflow():
        nonlocal edi, converted_bytes, eax, ecx
        compression_info["predicted"] = eax
                
        ax = eax & 0xFFFF
        ah = (ax >> 8) & 0xff
        ah ^= 0x80
        al = ah
        
        converted_bytes[edi] = al
        edi += 1
        
        ecx = compression_info["code"]
        eax = codec_index_table[ecx]
        ax = eax & 0xFFFF
        compression_info["index"] += ax
        
        compression_info["index"] = compression_info["index"] & 0xFFFF
       
        if compression_info["index"] < 0x8000:
            decomp_check_overflow()
        else:
            compression_info["index"] = 0
            decomp_adjust_step()
            
    def decomp_check_overflow():
        compression_info["index"] = compression_info["index"] & 0xFFFF
        
        if compression_info["index"] <= 88:
            decomp_adjust_step()
        else:
            compression_info["index"] = 88
            decomp_adjust_step()
        
    def decomp_adjust_step():
        global codec_byte_index,codec_step_table
        nonlocal esi, edi, eax, ecx
        ecx = compression_info["index"] & 0xffff
        eax = codec_step_table[ecx] & 0xffff
        
        ax = eax & 0xFFFF
        
        compression_info["sample_index"] += 1
        compression_info["step"] = ax
        
        codec_byte_index -= 1
        if codec_byte_index == 0:
            compression_info["source"] = esi
            compression_info["dest"] = edi
            
            eax = codec_bytes_processed
            
    
    sos_codec_init_stream()
    
    eax = compression_info
    edx = len(audio_bytes)
    
    ebx = 0
    ecx = 0
    
    ebx = eax
    
    eax = edx
    
    codec_bytes_processed = eax
    codec_byte_index = eax * 2
    
    esi = compression_info["source"]
    edi = compression_info["dest"]
    
    converted_bytes = bytearray(edx * 2)
    
    while codec_byte_index > 0:
        decomp_main_loop()
    
    return converted_bytes