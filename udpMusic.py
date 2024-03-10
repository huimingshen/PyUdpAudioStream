'''
This file iclude the basic classes used in UDPMusic. 
'''
from configparser import ConfigParser
import time
from Crypto.Cipher import AES
import threading, queue
import ctypes
import subprocess
from enum import Enum
import socket
import pyaudio
import ipaddress
import win32con
import win32api
import ctypes
import vlcDLNA

# run mode enum class
class RunMode(Enum):
    '''
    enum class
    PCM = 1
    AAC = 2
    '''
    PCM = 1
    AAC = 2

# read and rewrite the config file
class ConfigContr:
    '''
    ConfigContr class: read and write the .ini config file

    '''
    def __init__(self,ConfigName):
        ConfigName +='.ini'
        self.ConfigName = ConfigName
        self.cfg = ConfigParser(comment_prefixes='/', allow_no_value=True)
        try:
            open(ConfigName)
        except:
            print("No 'config.ini' file, new one is created")
            file = open(ConfigName,'w')
            file.close()
        self.cfg.read(ConfigName)

    def getDicOfSection(self,SectionName:str):
        sectionDic = dict(self.cfg.items(SectionName))
        return sectionDic
    
    def getSectionName(self):
        return self.cfg.sections()
    
    def writeValue(self,SectionName:str,KeyName:str,KeyValue:str):
        self.cfg.set(SectionName,KeyName,KeyValue)
        self._save_to_file()

    def addSection(self,SectionName:str):
        self.cfg.add_section(SectionName)
        self._save_to_file()
    
    def _save_to_file(self):
        with open(self.ConfigName, 'w') as configfile:
            self.cfg.write(configfile)

# encrypt and decrypt module. encrypt the udp package data
class AESencrypten:
    def _add_to_multiple_of_16(self,data:str):# aes encrpt need the length of str is multiple of 16
        byteData = data.encode(encoding='utf-8') 
        res_len =  len(byteData)%16
        if res_len != 0:
            byteData += b'\x00'*(16-res_len)
        return byteData

    def encrypt(self,key:str, data:str):
        aes = AES.new(self._add_to_multiple_of_16(key), AES.MODE_ECB)
        encrypt_aes_bytes = aes.encrypt(self._add_to_multiple_of_16(data))
        return encrypt_aes_bytes

    def decrypt(self,key:str, data:bytes):
        aes = AES.new(self._add_to_multiple_of_16(key), AES.MODE_ECB)
        #decrypt, and remove added \0
        decrypted_text = str(aes.decrypt(data), encoding='utf-8').replace('\0', '') 
        return decrypted_text

# class realise the data sending of music
class MusicSender:
    encodeLib = None
    configDic = None
    runMode = None
    host_ip = None
    chunkSize = None
    udpMusicPort = 5200
    udpCommandPort = 5201
    threadingStopFlag_sendMusic = False #control the loop of sendMusic 
    threadingStopFlag_sendcommand = False #control the loop of sendcommand
    AES_encrypten = AESencrypten()
    AESKEY = "encryptenkey"

    # initial relative module
    def __init__(self):
        self._initConfig()
        self._initEncodeLib()
    
    # load music decode/encode lib
    def _initEncodeLib(self):
        self.encodeLib = ctypes.cdll.LoadLibrary("aacLib\\AacEncode\\AacEncode.dll")
        self.encodeLib.aacEncode.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t]
        self.encodeLib.getData.restype = ctypes.POINTER(ctypes.c_ubyte) 
    
    # get setting infos from config file
    def _initConfig(self):
        config = ConfigContr('config')
        self.configDic = config.getDicOfSection('sender')
        self.runMode = (int)(self.configDic.get('runmode'))
        self.host_ip = self.configDic.get('host')
        self.chunkSize = int(self.configDic.get('chunk'))

    # a blocking function for recording and sending music
    def sendMusic(self):
        self.sendCommand_once(RunMode(self.runMode).name)
        self.threadingStopFlag_sendMusic = False
        CHUNK = self.chunkSize
        FORMAT = pyaudio.paInt16
        CHANNELS = 2
        RATE = 44100
        server_socket_music = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        server_socket_music.connect((self.host_ip, self.udpMusicPort))
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        inputDevIndx=None
        for i in range(0, numdevices):
            devName = str(p.get_device_info_by_host_api_device_index(0, i).get('name'))
            if "CABLE Output" in devName: #choose the output port of VAC
                inputDevIndx=i
        if inputDevIndx == None:
            print("\nERR: cannot find corresponding input device(CABLE Output)") 
            return
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True,input_device_index=inputDevIndx)
        if RunMode(self.runMode) ==RunMode.PCM:
            while not self.threadingStopFlag_sendMusic:
                data = stream.read(CHUNK)
                server_socket_music.send(data)
        elif RunMode(self.runMode) ==RunMode.AAC:
            self.encodeLib.encode_initial()
            frame_size = 512
            data_len = 2048 # read 512*4 = 2048 bits data
            while not self.threadingStopFlag_sendMusic:
                data = stream.read(frame_size)  
                ubuffer = (ctypes.c_ubyte * data_len).from_buffer(bytearray(data))
                self.encodeLib.aacEncode(ubuffer, data_len)
                if self.encodeLib.getBytesNumber()!=0:
                    aacData_ptr = self.encodeLib.getData()
                    aacData = ctypes.string_at(aacData_ptr,self.encodeLib.getBytesNumber())
                    server_socket_music.send(aacData)
                    self.encodeLib.free_arr(aacData_ptr)#free the pointer
            # self.encodeLib.encode_close() # if release all Buffer,the musicsender cannot be restart.
            
        else:
            print("runMode number error")
        stream.close()
        p.terminate()
        server_socket_music.close()
        self.sendCommand_once('stop')
        print('musicsender already finished')

    # a bolcking function for control command sending
    def sendCommand_blocking(self):
        self.threadingStopFlag_sendcommand = False
        server_socket_command = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        server_socket_command.connect((self.host_ip, self.udpCommandPort))
        while not self.threadingStopFlag_sendcommand:
            code = input("input code: ")
            if code == "esc":
                self.threadingStopFlag_sendcommand=True
                break
            else:
                server_socket_command.send(self.AES_encrypten.encrypt(self.AESKEY,code))

    # send control command once
    def sendCommand_once(self,code):
        server_socket_command = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        server_socket_command.connect((self.host_ip, self.udpCommandPort))
        server_socket_command.send(self.AES_encrypten.encrypt(self.AESKEY,code))
        server_socket_command.close()

    ### SenderReceiverCommunication part######
    # get the local Bradcast adress
    def getBroadcastAdress(self,localIP:str,maskstr:str):
        ipstrArr = localIP.split(".")
        iptokens = list(map(int, ipstrArr))
        maskstrArr = maskstr.split(".")
        masktokens = list(map(int, maskstrArr))
        broadlist = []
        for i in range(len(iptokens)):
            ip = iptokens[i]
            mask = masktokens[i]
            broad = ip & mask | (~mask & 255)
            broadlist.append(broad)
        return '.'.join(map(str, broadlist))

    # get the ip adress of receiver
    def getReceiverIp(self,tiemout:int=2):
        localListenPort = 5202
        localSubnetMask = "255.255.255.0"
        socket_getReceiverIp = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        socket_getReceiverIp.bind(('',localListenPort))
        local_ip_address = socket.gethostbyname(socket.gethostname())
        broadcastAdr = self.getBroadcastAdress(local_ip_address,localSubnetMask)
        socket_getReceiverIp.sendto(self.AES_encrypten.encrypt(self.AESKEY,"search device"),(broadcastAdr, self.udpCommandPort))
        ip_list = []
        while True:
            socket_getReceiverIp.settimeout(tiemout)
            try:
                code,host_ip= socket_getReceiverIp.recvfrom(1024)
                code = self.AES_encrypten.decrypt(self.AESKEY,code)
                if code =="search device callback":
                    ip_list.append(str(host_ip[0]))
            except socket.timeout:
                print("search time over")
                break    
        socket_getReceiverIp.close()
        return ip_list

    # get defualt speacker
    def getDefualtSpeaker(self):
        p = pyaudio.PyAudio()
        defualt_speaker = p.get_default_output_device_info().get('name')
        print('the current defalt speaker is: ',defualt_speaker)
        return defualt_speaker
    
    # get the used ip
    def getUsedHostIp(self):
        return self.host_ip

    # get the used runmode
    def getUsedRunMode(self):
        return RunMode(self.runMode)
    
    def getUsedChunkSize(self):
        return self.chunkSize
    
    # set defualt speacker
    def setDefaultSpeaker(self,speakerName):
        try:
            si = subprocess.STARTUPINFO() # hide the exe running window
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(['setSpeaker.exe','-s',speakerName],startupinfo=si)
            # subprocess.run(['setSpeaker.exe','-s',speakerName])
        except:
            print("set default speaker failled")
            return False
        return True

    # set the runmode
    def setRunMode(self,runMode:RunMode):
        if runMode ==RunMode.AAC:
            config = ConfigContr('config')
            config.writeValue('sender','runmode',str(RunMode.AAC.value))
            self.stop()
            self._initConfig()
        elif runMode ==RunMode.PCM:
            config = ConfigContr('config')
            config.writeValue('sender','runmode',str(RunMode.PCM.value))
            self.stop()
            self._initConfig()
        else:
            return False
        return True
    
    # set the chunk size
    def setChunkSize(self,size:int):
        '''
        Chunk size is the music frame size, which also decides the size of each udp
        Package. Chunk size only useful in RunMode:PCM. 
        '''
        config = ConfigContr('config')
        config.writeValue('sender','chunk',str(size))
        self.stop()
        self._initConfig()
        

    # set ip adress for receiver 
    def setHostIpAdress(self,hostIP:str):
        '''
        input receiver IP like: 192.168.0.1
        '''
        try:
            ip_object = ipaddress.ip_address(hostIP)
            print(f"The IP address '{ip_object}' is valid.")
            config = ConfigContr('config')
            config.writeValue('sender','host',hostIP)
            self.stop()
            self._initConfig()
        except ValueError:
            print(f"The IP address '{hostIP}' is not valid")
            return False
        return True

    def run(self): 
        '''
        it is a blocking function, also a example for how to 
        use those functions in MusicSender Class
        '''
        ipAvailable =False

        if self.host_ip =='':
            print("searching....")
            IPlist = self.getReceiverIp()
            if len(IPlist)>=1:
                self.host_ip = IPlist[0]
                ipAvailable=True
        else:
            ipAvailable=True

        if ipAvailable:
            print("receiver ip is: "+self.host_ip)

            self.setDefaultSpeaker('CABLE Input')  #set CABLE Input as default device

            t1 = threading.Thread(target=self.sendMusic, args=())
            t1.setDaemon(True)
            t1.start()
            print("program is running. input code 'j' to increase client sound, input code 'k' to decrease client sound. code: 'esc' close the send program, code: 'stop' close the client programm.")
            self.sendCommand_blocking()
        else:
            print("cannot get the ip of reveiver device")
            input("press enter to close")

    def stop(self):
        self.threadingStopFlag_sendMusic = True 
        self.threadingStopFlag_sendcommand = True 

# the class for receiver
class MusicReceiver:
    AES_encrypten = AESencrypten()
    Player = vlcDLNA.VLCRenderer()
    DLNAserver = vlcDLNA.DLNAService(Player)
    AES_KEY = "encryptenkey" # the key of en/descrpt
    threadStopFlag_getAudio=False #threading stop flag
    threadStopFlag_musicStream=False
    threadStopFlag_commandCtr=False
    configDic = None
    runMode = None
    Chunk = None
    queueMaxsize_pcm = None 
    queuethresholdvalue_pcm = None
    queueMaxsize_aac = None 
    queuethresholdvalue_aac = None
    _load_config_from_file_callback = None
    
    # initialize
    def __init__(self) -> None:
        self._load_decode_lib()
        self._load_config_from_file()
        self._set_queue_size()

    # load decode lib
    def _load_decode_lib(self):
        self.decodeLib = ctypes.cdll.LoadLibrary("aacLib\\AacDecode\\AccDecode.so")
        self.decodeLib.AacDecode.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
        self.decodeLib.AacDecode.restype = ctypes.POINTER(ctypes.c_ubyte)
        self.decodeLib.getOutputDataSize.restype = ctypes.c_ulong

    # set the size of receiver queue
    def _set_queue_size(self):
        if self.runMode==(RunMode.AAC.value):
            queueMaxsize = self.queueMaxsize_aac
        elif self.runMode==(RunMode.PCM.value):
            queueMaxsize = self.queueMaxsize_pcm
        self.data_queue = queue.Queue(queueMaxsize)

    # load setting info from file
    def _load_config_from_file(self):
        config = ConfigContr('config')
        self.configDic = config.getDicOfSection('receiver')
        self.runMode = int(self.configDic.get('runmode'))
        self.Chunk = int(self.configDic.get('chunk'))
        self.queueMaxsize_pcm = int(self.configDic.get('queuesize_pcm'))
        self.queuethresholdvalue_pcm = int(self.configDic.get('queuethresholdvalue_pcm'))
        self.queueMaxsize_aac = int(self.configDic.get('queuesize_aac'))
        self.queuethresholdvalue_aac = int(self.configDic.get('queuethresholdvalue_aac'))
        if self._load_config_from_file_callback is not None:
            self._load_config_from_file_callback()

    # upd socket to receive data
    def getUDPAudioData(self):
        self.threadStopFlag_getAudio = False
        port = 5200
        BUFF_SIZE = 65536
        client_socket_music = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        client_socket_music.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,BUFF_SIZE)
        client_socket_music.bind(('', port))
        while not self.threadStopFlag_getAudio:
            frame,_= client_socket_music.recvfrom(BUFF_SIZE)
            self.data_queue.put(frame)
            # print('Queue size...',self.data_queue.qsize())
        client_socket_music.close()

    # clean the data queue
    def clearQueue(self,q:queue.Queue):
        thresholdValue = 5
        if q.qsize()>thresholdValue:
            for i in range(1,q.qsize()-thresholdValue):
                q.get()

    # increase speaker volume
    def volumeUp(self):
        win32api.keybd_event(win32con.VK_VOLUME_UP, 0)

    # decrease speaker volume
    def volumeDown(self):
        win32api.keybd_event(win32con.VK_VOLUME_DOWN, 0)

    # play the music data
    def audioStream(self):
        self.threadStopFlag_musicStream =False
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(2),
                        channels=2,
                        rate=44100,
                        output=True,
                        frames_per_buffer=self.Chunk)	
        StartStatus = False
        self.clearQueue(self.data_queue)
        if RunMode(self.runMode) ==RunMode.PCM:
            while not self.threadStopFlag_musicStream:
                if(self.data_queue.qsize()>self.queuethresholdvalue_pcm):
                    StartStatus=True
                if(self.data_queue.qsize()==0):
                    StartStatus=False
                    # print(self.data_queue.get())
                    time.sleep(0.2)
                if StartStatus:
                    frame = self.data_queue.get()
                    stream.write(frame)
        elif RunMode(self.runMode) ==RunMode.AAC:
            self.decodeLib.AacDecodeInitial()
            while not self.threadStopFlag_musicStream:
                if(self.data_queue.qsize()>self.queuethresholdvalue_aac):
                    StartStatus=True
                if(self.data_queue.qsize()==0):
                    StartStatus=False
                    time.sleep(0.2)
                if StartStatus:
                    aac_data = self.data_queue.get()
                    b_len = len(aac_data)
                    ubuffer2 = (ctypes.c_ubyte * b_len).from_buffer(bytearray(aac_data))
                    adr = self.decodeLib.AacDecode(ubuffer2,b_len)
                    if(self.decodeLib.getOutputDataSize()!=0): 
                        pcmData=ctypes.string_at(adr,self.decodeLib.getOutputDataSize())
                        stream.write(pcmData)
            self.decodeLib.AccEncodeClose()
        stream.close()

    # set the chunk size and write it in config file
    def setChunk(self,size:int):
        self.udpMusicReceiverStop()
        config = ConfigContr('config')
        config.writeValue('receiver','chunk',str(size))
        self._load_config_from_file()
        self._set_queue_size()

    # set the queue maxsize in aac mode and write it in config file
    def setQueueMaxsizeAAC(self,size:int):
        self.udpMusicReceiverStop()
        config = ConfigContr('config')
        config.writeValue('receiver','queuesize_aac',str(size))
        self._load_config_from_file()
        self._set_queue_size()
    
    # set the queue maxsize in pcm mode and write it in config file
    def setQueueMaxsizePCM(self,size:int):
        self.udpMusicReceiverStop()
        config = ConfigContr('config')
        config.writeValue('receiver','queuesize_pcm',str(size))
        self._load_config_from_file()
        self._set_queue_size()
    
    # set the startplay threshold in aac mode and write it in config file
    def setThresholdAAC(self,size:int):
        self.udpMusicReceiverStop()
        config = ConfigContr('config')
        config.writeValue('receiver','queuethresholdvalue_aac',str(size))
        self._load_config_from_file()
        self._set_queue_size()
    
    # set the startplay threshold in pcm mode and write it in config file
    def setThresholdPCM(self,size:int):
        self.udpMusicReceiverStop()
        config = ConfigContr('config')
        config.writeValue('receiver','queuethresholdvalue_pcm',str(size))
        self._load_config_from_file()
        self._set_queue_size()
    
    # set the run mode and write it in config file
    def setRunMode(self,runMode:RunMode):
        self.udpMusicReceiverStop()
        config = ConfigContr('config')
        if runMode ==RunMode.AAC:
            config.writeValue('receiver','runmode',str(RunMode.AAC.value))
        elif runMode ==RunMode.PCM:
            config.writeValue('receiver','runmode',str(RunMode.PCM.value))
        else:
            return False
        self._load_config_from_file()
        self._set_queue_size()
        return True

    # change the runmode to pcm
    def setRunmode2pcm(self):
        self.setRunMode(RunMode.PCM)
        time.sleep(1)
        self.udpMusicReceiverRun()

    # change the runmode to aac
    def setRunmode2aac(self):
        self.setRunMode(RunMode.AAC)
        time.sleep(1)
        self.udpMusicReceiverRun()
            

    def getChunk(self):
        return self.Chunk
    
    def getQueueMaxsizeAAC(self):
        return self.queueMaxsize_aac
    
    def getQueueMaxsizePCM(self):
        return self.queueMaxsize_pcm
    
    def getThresholdAAC(self):
        return self.queuethresholdvalue_aac
    
    def getThresholdPCM(self):
        return self.queuethresholdvalue_pcm
    
    def getUsedRunMode(self):
        return RunMode(self.runMode)

    # receive command code and react for the command code
    def commandCommunication(self):
        command_table = {
        "j":self.volumeUp,
        "k":self.volumeDown,
        "stop":self.udpMusicReceiverStop,
        "AAC":self.setRunmode2aac,
        "PCM":self.setRunmode2pcm,
        "search device": lambda : client_socket_comand.sendto(
            self.AES_encrypten.encrypt(self.AES_KEY,"search device callback"),(host_ip[0], 5202))
        }
        self.threadStopFlag_commandCtr=False
        # open the udp socket to receive comand code. 
        client_socket_comand = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        client_socket_comand.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,1024)
        client_socket_comand.bind(('', 5201)) # receiving port 5201
        while not self.threadStopFlag_commandCtr:
            code,host_ip= client_socket_comand.recvfrom(1024)
            try:
                code = self.AES_encrypten.decrypt(self.AES_KEY,code)
                print(code)
                if code in command_table.keys():
                    command_table[code]()
            except Exception as e:
                print("Received Code No Valid ",repr(e))



    def udpMusicReceiverRun(self,*args):
        T1 = threading.Thread(target=self.getUDPAudioData,daemon=True)
        T2 = threading.Thread(target=self.audioStream,daemon=True)
        T1.start()
        T2.start()
        return T1.is_alive, T2.is_alive

    def udpMusicReceiverStop(self,*args):
        self.threadStopFlag_getAudio=True
        self.threadStopFlag_musicStream=True

    
    def DLNAseverStop(self,*args):
        self.DLNAserver.stop()



    def DLNAseverRun(self,*args):
        
        T1 = threading.Thread(target=self.DLNAserver.run,daemon=True)
        T1.start()
        return T1.is_alive
        
    
    def commandSeverRun(self):
        T1 = threading.Thread(target=self.commandCommunication,daemon=True)
        T1.start()
        return T1.is_alive



        



    

        

        
if __name__ == '__main__':
    # sender1 = MusicSender()
    # defaultSpeaker_pre = sender1.getDefualtSpeaker()
    # sender1.run()
    # sender1.setDefaultSpeaker(defaultSpeaker_pre)
    pass