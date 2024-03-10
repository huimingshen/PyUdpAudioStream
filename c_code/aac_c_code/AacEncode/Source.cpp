#include<stdio.h>
#include <fdk-aac/aacenc_lib.h> // Fraunhofer FDK AAC encode library
#include <stdint.h>
#include <stdlib.h>
#include<iostream>
   
//set macro for python. ensure the name of function don't change in compiling
#define PYTHON_API extern "C" __declspec(dllexport)

HANDLE_AACENCODER encoder;
AACENC_BufDesc in_buf = { 0 }, out_buf = { 0 };
AACENC_InArgs in_args = { 0 ,0 };
AACENC_OutArgs out_args = { 0 };
unsigned char buffer1[2048], buffer2[2048];
int readBytes=2048;
int in_identifier = IN_AUDIO_DATA;
int in_elem_size = 2;
void* in_ptr = buffer1;
int out_identifier = OUT_BITSTREAM_DATA;
int out_size = 2048;
int out_elem_size = 1;
void* out_ptr = buffer2;
int j = 0;


PYTHON_API void encode_initial() {
	// initialize encoder
	if (aacEncOpen(&encoder, 0, 2) != AACENC_OK) {
		printf("encoder open error!\n");
		return;
	}
	if (aacEncoder_SetParam(encoder, AACENC_SAMPLERATE, 44100) != AACENC_OK) {
		printf("set samplerate error!\n");
		return;
	}
	if (aacEncoder_SetParam(encoder, AACENC_BITRATE, 128 * 1024) != AACENC_OK) {
		printf("set bitrate error!\n");
		return;
	}
	/*if (aacEncoder_SetParam(encoder, AACENC_SBR_MODE, 0) != AACENC_OK) {
		printf("set sbr_mode error!\n");
		return;
	}*/
	if (aacEncoder_SetParam(encoder, AACENC_AOT, AOT_AAC_LC) != AACENC_OK) {
		printf("set aot error!\n");
		return;
	}
	if (aacEncoder_SetParam(encoder, AACENC_CHANNELMODE, MODE_2) != AACENC_OK) {
		printf("set channelmode error!\n");
		return;
	}
	if (aacEncoder_SetParam(encoder, AACENC_CHANNELORDER, 1) != AACENC_OK) {
		printf("set channelorder error!\n");
		return;
	}
	if (aacEncoder_SetParam(encoder, AACENC_BITRATEMODE, 0) != AACENC_OK) {
		printf("set bitratemode error!\n");
		return;
	}
	if (aacEncoder_SetParam(encoder, AACENC_TRANSMUX, 2) != AACENC_OK) {
		printf("set transmux error!\n");
		return;
	}
	in_args.numInSamples = readBytes / 2;
	in_buf.numBufs = 1;
	in_buf.bufs = (void**)&in_ptr;
	in_buf.bufferIdentifiers = &in_identifier;
	in_buf.bufSizes = &readBytes;
	in_buf.bufElSizes = &in_elem_size;
	out_buf.numBufs = 1;
	out_buf.bufs = (void**)&out_ptr;
	out_buf.bufferIdentifiers = &out_identifier;
	out_buf.bufSizes = &out_size;
	out_buf.bufElSizes = &out_elem_size;
}

PYTHON_API void aacEncode(const unsigned char* chunk, size_t buffer_size = 2048) {
	memcpy(buffer1, chunk, buffer_size);
	//encoding
	if ((aacEncEncode((encoder), &in_buf, &out_buf, &in_args, &out_args)) != AACENC_OK) {
		printf("encode error!\n");
	}
}

PYTHON_API int getBytesNumber() {
	return out_args.numOutBytes;
}


PYTHON_API unsigned char* getData() {
	
	if (out_args.numOutBytes > 0){
	    //return dara
		//std::cout << "size after encode: " << out_args.numOutBytes << std::endl;
		unsigned char* new_buffer = new unsigned char[out_args.numOutBytes];
	    memcpy(new_buffer, buffer2, out_args.numOutBytes);
		/*for (int i = 0;i < out_args.numOutBytes;i++) {
			std::cout << static_cast<unsigned>(new_buffer[i]) << ' ';
		}*/
		//std::cout << static_cast<unsigned>(new_buffer[-1]) <<"|" << static_cast<unsigned>(new_buffer[-2]) << std::endl;
		return new_buffer;
	}

	/*memcpy(new_buffer, buffer1, buffer_size);*/
	//return buffer2;
	return NULL;

}

PYTHON_API void free_arr(void* pointer) {
	delete[] pointer;
	pointer = NULL;
}

PYTHON_API void encode_close() {
	
	printf("encode finished!\n");
	aacEncClose((HANDLE_AACENCODER*)(&encoder));
	delete[] buffer1;
	delete[] buffer2;
}

