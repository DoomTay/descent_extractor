codec_index_table = [-1,-1,-1,-1, 2, 4, 6, 8, -1,-1,-1,-1, 2, 4, 6, 8]

codec_step_table = [7, 8, 9, 10, 11, 12, 13, 14, 16,  17,  19,  21,  23,  25,  28, 31,  34,  37,  41,  45,  50,  55, 60,  66,  73,  80,  88,  97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963,1060,1166,1282,1411,1552, 1707,1878, 2066,2272,2499,2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,7132,7845,8630,9493,10442,11487,12635,13899,15289,16818,18500,20350,22385,24623,27086,29794,32767]

compression_info = {
    "source": 0,
    "dest": 0,
    "sample_index": 0,
    "predicted": 0,
    "difference": 0,
    "code_buffer": 0,
    "code": 0,
    "step": 0,
    "index": 0
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
        if (compression_info["sample_index"] & 1) == 0:
            decomp_fetch_token()
        else:
            new_buffer = compression_info["code_buffer"] & 0xffff
            new_buffer = (new_buffer >> 4) & 0xf
            
            compression_info["code"] = new_buffer & 0xffff
            
            decomp_calc_difference()
            
    def decomp_fetch_token():
        nonlocal source_index, audio_bytes
        compressed_byte = audio_bytes[source_index] & 0xff
        compression_info["code_buffer"] = compressed_byte & 0xffff
        source_index += 1
        token = compressed_byte & 0x000f
        compression_info["code"] = token & 0xffff
        
        decomp_calc_difference()
        
    def decomp_calc_difference():
        compression_info["difference"] = 0
        step = compression_info["step"] & 0xffff

        if (compression_info["code"] & 4) != 0: compression_info["difference"] += step
        if (compression_info["code"] & 2) != 0: compression_info["difference"] += step >> 1
        if (compression_info["code"] & 1) != 0: compression_info["difference"] += step >> 2

        compression_info["difference"] += step >> 3

        if (compression_info["code"] & 8) != 0: compression_info["difference"] = -compression_info["difference"]

        clamp_predicted()

    def clamp_predicted():
        compression_info["predicted"] += compression_info["difference"]

        compression_info["predicted"] = max(-32768, min(compression_info["predicted"], 32767))

        decomp_no_underflow()

    def decomp_no_underflow():
        nonlocal dest_index, converted_bytes

        predicted_high_byte = compression_info["predicted"] & 0xFFFF
        
        converted_bytes[dest_index] = ((predicted_high_byte >> 8) & 0xff) ^ 0x80
        dest_index += 1
        
        code_index = compression_info["code"]
        lookup_value = codec_index_table[code_index] & 0xFFFF
        compression_info["index"] += lookup_value
        
        compression_info["index"] = compression_info["index"] & 0xFFFF
        
        if compression_info["index"] < 0x8000:
            compression_info["index"] = compression_info["index"] & 0xFFFF
            if compression_info["index"] > 88: compression_info["index"] = 88
        else: compression_info["index"] = 0
            
        decomp_adjust_step()
        
    def decomp_adjust_step():
        global codec_byte_index,codec_step_table
        nonlocal source_index, dest_index
        new_index = compression_info["index"] & 0xffff
        new_step = codec_step_table[new_index] & 0xffff
        
        compression_info["sample_index"] += 1
        compression_info["step"] = new_step & 0xFFFF
        
        codec_byte_index -= 1
        if codec_byte_index == 0:
            compression_info["source"] = source_index
            compression_info["dest"] = dest_index
            
            new_step = codec_bytes_processed
            
    
    sos_codec_init_stream()
    
    compressed_length = len(audio_bytes)
    
    codec_bytes_processed = compressed_length
    codec_byte_index = compressed_length * 2

    source_index = compression_info["source"]
    dest_index = compression_info["dest"]

    converted_bytes = bytearray(compressed_length * 2)

    while codec_byte_index > 0:
        decomp_main_loop()
    
    return converted_bytes