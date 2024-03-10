#include<neaacdec.h> //faac lib
#include <stdio.h>
#include <iostream>



//set macro for python. ensure the name of function don't change in compiling
#define PYTHON_API extern "C" __declspec(dllexport)

unsigned long outputDataSize;
NeAACDecHandle decoder = 0;
size_t size = 0;
NeAACDecFrameInfo frame_info;
unsigned long samplerate;
unsigned char channels;
unsigned char* pcm_data = NULL;
bool initial_status;

/*fetch one ADTS frame*/
int get_ADTS_frame(unsigned char* buffer, size_t buf_size)
{
	size_t size = 0;
	if (!buffer )
	{
		return -1;
	}
	while (1)
	{
		if (buf_size < 7)
		{
			return -1;
		}
		if ((buffer[0] == 0xff) && ((buffer[1] & 0xf0) == 0xf0))
		{
			size |= ((buffer[3] & 0x03) << 11); //high 2 bit
			size |= buffer[4] << 3; //middle 8 bit
			size |= ((buffer[5] & 0xe0) >> 5); //low 3bit
			break;
		}
		--buf_size;
		++buffer;
	}
	if (buf_size < size)
	{
		return -1;
	}
	return 0;
}

PYTHON_API unsigned long getOutputDataSize() {
	return outputDataSize;
}

PYTHON_API void AacDecodeInitial() {
	decoder = NeAACDecOpen(); //open decoder
	NeAACDecConfigurationPtr conf = NeAACDecGetCurrentConfiguration(decoder);
	conf->defObjectType = LC;
	conf->defSampleRate = 44100;
	conf->outputFormat = FAAD_FMT_16BIT;
	conf->dontUpSampleImplicitSBR = 1;
	NeAACDecSetConfiguration(decoder, conf);
	initial_status = false;
}

PYTHON_API unsigned char* AacDecode(const unsigned char* inputData, int iputDataSize) {

	unsigned char* inputDataBuffer = new unsigned char[iputDataSize];
	memcpy(inputDataBuffer, inputData, iputDataSize);
	/*for (int i = 0;i < iputDataSize;i++) {
		std::cout << static_cast<unsigned>(inputDataBuffer[i]) << ' ';
	}*/



	if (get_ADTS_frame(inputDataBuffer, iputDataSize) < 0)
	{	
		printf(" data error");
		goto end;
	}

	
	//initialize decoder
	if (!initial_status) {
		char err = NeAACDecInit(decoder, inputDataBuffer, iputDataSize, &samplerate, &channels);
		if (err != 0) {
			// Handle error
			fprintf(stderr, "NeAACDecInit error: %d\n", err);
			goto end;
		}
		printf("samplerate %d, channels %d\n", samplerate, channels);
		initial_status = true;
	}
	


	//decode ADTS frame
	pcm_data = (unsigned char*)NeAACDecDecode(decoder, &frame_info, inputDataBuffer, (unsigned long)iputDataSize);
	if (frame_info.error > 0)
	{
		printf("%s\n", NeAACDecGetErrorMessage(frame_info.error));
	}
	else if (pcm_data && frame_info.samples > 0)
	{
		/*printf("frame info: bytesconsumed %d, channels %d, header_type %d,object_type %d, samples %d,  samplerate %d\n",
			frame_info.bytesconsumed,
			frame_info.channels, frame_info.header_type,
			frame_info.object_type, frame_info.samples,
			frame_info.samplerate);*/

		outputDataSize = frame_info.samples * frame_info.channels;
		delete[] inputDataBuffer;
		inputDataBuffer = NULL;
		return pcm_data;
	}


end:
	//std::cout << "funktion skiped " << std::endl;
	outputDataSize = 0;
	delete[] inputDataBuffer;
	inputDataBuffer = NULL;
	return NULL;
	
}

PYTHON_API void AccEncodeClose() {
	NeAACDecClose(decoder);
}