from kivy.config import Config
Config.set('kivy', 'exit_on_escape', '0')

# Config.set('graphics', 'width', '800')
# Config.set('graphics', 'height', '600')
import kivymd.icon_definitions
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivy.uix.screenmanager import ScreenManager,NoTransition
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogIcon,
    MDDialogHeadlineText,
    MDDialogSupportingText,
    MDDialogButtonContainer,
    MDDialogContentContainer,
)
from kivymd.uix.textfield import (
    MDTextField,
    MDTextFieldLeadingIcon,
    MDTextFieldHintText,
    MDTextFieldHelperText,
    MDTextFieldTrailingIcon,
    MDTextFieldMaxLengthText,
)
from kivymd.uix.divider import MDDivider
from kivy.lang import Builder
from kivy.uix.widget import Widget
from kivymd.uix.menu import MDDropdownMenu
from kivy.metrics import dp
from kivy.clock import Clock
from udpMusic import MusicSender, RunMode,MusicReceiver
import threading
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import mainthread
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
import logging
logging.disable(logging.ERROR)



class MainScreen(MDScreen):
    pass


class SenderScreen(MDScreen):
    _power_on = False
    _musicSender = MusicSender()
    _host_IP = None
    _encode_mode = None
    _chunk_size = None
    _input_text=''
    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.refresh_host_ip()  
        self.refresh_encode_mode()
        self.refresh_chunk_size()
        # self._thread_musicsender = threading.Thread(target=self._musicSender.sendMusic,args=())
        self._thread_musicsender = threading.Thread(target=self._musicSender.sendMusic,args=())
        Clock.schedule_interval(lambda dt: self._running_detect(),1)

    def _running_detect(self):
        status_now = self._thread_musicsender.is_alive()
        if status_now != self._power_on:
            self._power_on = status_now
            self._renewPowerButtionColor()
        else:
            pass
    
    def _renewPowerButtionColor(self):
        if  self._power_on:
            self.ids.power_button.md_bg_color="green"
        else:
            self.ids.power_button.md_bg_color="brown"


    def _opendialog(self,tagName:str,value_old,comfirm_callback,tipText=''):
        self.dialog = MDDialog(
            # ----------------------------Icon-----------------------------
            # MDDialogIcon(
            #     icon="refresh",
            # ),
            # -----------------------Headline text-------------------------
            MDDialogHeadlineText(
                text= tagName+" Setting",
            ),
            # -----------------------Supporting text-----------------------
            MDDialogSupportingText(
                text="Write a new value, and click the accept button to save. "+tipText,
            ),
            # -----------------------Custom content------------------------
            MDDialogContentContainer(
                self._dialog_inputtext_module(tagName,value_old),
                orientation="vertical",
                
            ),
            # DialogContent(),
            # ---------------------Button container------------------------
            MDDialogButtonContainer(
                Widget(),
                MDButton(
                    MDButtonText(text="Cancel",id='test1'),
                    style="text",
                    # on_press=self.close_dateinput_dialog()
                    on_press = lambda _: self.dialog.dismiss() 
                ),
                MDButton(
                    MDButtonText(text="Accept"),
                    style="text",
                    on_press = comfirm_callback
                ),
                spacing="8dp",
            ),
            # -------------------------------------------------------------
            size_hint=(0.5,None)
        ) 
        self.dialog.open()

    def _dialog_inputtext_module(self,tagName,value_old):
        a= MDTextField(
                    MDTextFieldHintText(
                        text=tagName,
                    ),
                    # MDTextFieldMaxLengthText(
                    #     max_text_length=10,
                    # ),
                    mode="outlined",
                    size_hint_x=None,
                    width="240dp",
                    pos_hint={"center_x": 0.5, "center_y": 0.5},
                )
        a.text = value_old
        a.set_text=self._dialog_callback_inputText
        return a

    def _dialog_callback_inputText(self,*args):
        self._input_text = args[1]

    def set_chunk_dialog(self):
        self._opendialog('Chunk',str(self._chunk_size),self.set_chunk_dialog_callback,
                        ' tip: chunk is int, between 0 and 1000. only valid in PCM Mode')
    
    def set_chunk_dialog_callback(self,*args):
        try :
            chunk = int(self._input_text)
        except:
            print('just number allowed in input')
            return
        if chunk>0 and chunk<1000:
            self._musicSender.setChunkSize(chunk)
            self.refresh_chunk_size()
            self.dialog.dismiss()
        else:
            print('invalid input: chunk ')

    def set_encodeMode_dialog(self):
        self._opendialog('Run Mode',str(self._encode_mode),self.set_encodeMode_dialog_callback,
                        ' tip: Mode is AAC or PCM ')
        
    def set_encodeMode_dialog_callback(self,*args):
        mode = self._input_text
        if mode == 'AAC' or mode == 'PCM':
            # print(RunMode[mode])
            self._musicSender.setRunMode(RunMode[mode])
            self.refresh_encode_mode()
            self.dialog.dismiss()
        else:
            print('invalid input: encode mode ')

    def set_hostIP_dialog(self):
        self._opendialog('Host IP',str(self._host_IP),self.set_hostIP_dialog_callback,
                        ' tip: ipv4')
        
    def set_hostIP_dialog_callback(self,*args):
        IP = self._input_text
        if self._musicSender.setHostIpAdress(IP):
            self.refresh_host_ip()
            self.dialog.dismiss()
        else:
            print('invalid input: host IP')
        

    def refresh_host_ip(self):
        self._host_IP = self._musicSender.getUsedHostIp()
        if self._host_IP is None: 
            print("err: _host_IP, no valid input") 
            return 
        self.ids.host_ip.text = self._host_IP

    def refresh_encode_mode(self):
        self._encode_mode = self._musicSender.getUsedRunMode().name
        if self._encode_mode is None: 
            print("err: _encode_mode, no valid input") 
            return 
        self.ids.encode_mode.text = self._encode_mode
    
    def refresh_chunk_size(self):
        self._chunk_size = self._musicSender.getUsedChunkSize()
        if self._chunk_size is None: 
            print("err: _chunk_size, no valid input") 
            return 
        self.ids.chunk_size.text = str(self._chunk_size)

    
    def receiverSearchMenu(self):
        ip_List = self._musicSender.getReceiverIp(1)
        menu_items = [
            {
                "text": i,
                "on_release": lambda x=i: self.menu_callback(x),
                "height": dp(40),
            } for i in ip_List
        ]
        self.menu = MDDropdownMenu(
            caller=self.ids.search_button, 
            items=menu_items,                     
        )
        self.menu.size_hint_x = 0.2
        self.menu.open()

    def menu_callback(self, text_item):
        self._musicSender.setHostIpAdress(text_item)
        self.refresh_host_ip()
        self.menu.dismiss()

    def powerSwitch(self):
        if self._power_on:
            self._musicSender.stop()
            self._musicSender.setDefaultSpeaker(self._previous_defualt_speaker)
        else:
            self._previous_defualt_speaker = self._musicSender.getDefualtSpeaker()
            self._musicSender.setDefaultSpeaker('CABLE Input')
            self._thread_musicsender = threading.Thread(target=self._musicSender.sendMusic,args=())
            self._thread_musicsender.daemon=True
            self._thread_musicsender.start()

    def increaseReceiverVolume(self):
        self._musicSender.sendCommand_once('j')

    def decreaseReceiverVolume(self):
        self._musicSender.sendCommand_once('k')

    def closeReceiver(self):
        self._musicSender.sendCommand_once('stop')



class ReceiverScreen(MDScreen):
    _input_text=''
    _chunk_size = None
    _encode_mode = None
    _queueMaxsizePCM = None
    _queueMaxsizeAAC = None
    _thresholdPCM = None
    _thresholdAAC = None
    _DLNASevice_on = False

    _udpReceiver = MusicReceiver()
    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.refresh_chunk_size()
        self.refresh_encode_mode()
        self.refresh_queueMaxsizeAAC()
        self.refresh_thresholdAAC()
        self.refresh_queueMaxsizePCM()
        self.refresh_thresholdPCM()
        self._udpReceiver._load_config_from_file_callback = self._reloadConfigCallback



    def _reloadConfigCallback(self):
        self.refresh_encode_mode()

    def refresh_chunk_size(self):
        self._chunk_size = self._udpReceiver.getChunk()
        if self._chunk_size is None: 
            print("err: _chunk_size, no valid input") 
            return 
    
    def refresh_encode_mode(self):
        self._encode_mode = self._udpReceiver.getUsedRunMode().name
        if self._encode_mode is None: 
            print("err: _encode_mode, no valid input") 
            return 
        self.ids.encode_mode.text = self._encode_mode

    def refresh_queueMaxsizeAAC(self):
        self._queueMaxsizeAAC = self._udpReceiver.getQueueMaxsizeAAC()
        if self._queueMaxsizeAAC==None:
            print("err: _queueMaxsizeAAC, no valid input") 
            return
        # print(f'{self._queueMaxsizeAAC = }')
        self.ids.queueMaxsizeAAC.text=str(self._queueMaxsizeAAC)

    def refresh_queueMaxsizePCM(self):
        self._queueMaxsizePCM = self._udpReceiver.getQueueMaxsizePCM()
        if self._queueMaxsizePCM==None:
            print("err: _queueMaxsizePCM, no valid input") 
            return
        self.ids.queueMaxsizePCM.text=str(self._queueMaxsizePCM)

    def refresh_thresholdAAC(self):
        self._thresholdAAC = self._udpReceiver.getThresholdAAC()
        if self._thresholdAAC==None:
            print("err: _thresholdAAC, no valid input") 
            return
        self.ids.thresholdAAC.text=str(self._thresholdAAC)

    def refresh_thresholdPCM(self):
        self._thresholdPCM = self._udpReceiver.getThresholdPCM()
        if self._thresholdPCM==None:
            print("err: _thresholdPCM, no valid input") 
            return
        self.ids.thresholdPCM.text=str(self._thresholdPCM)

    def _opendialog(self,tagName:str,value_old,comfirm_callback,tipText=''):
        self.dialog = MDDialog(
            # ----------------------------Icon-----------------------------
            # MDDialogIcon(
            #     icon="refresh",
            # ),
            # -----------------------Headline text-------------------------
            MDDialogHeadlineText(
                text= tagName+" Setting",
            ),
            # -----------------------Supporting text-----------------------
            MDDialogSupportingText(
                text="Write a new value, and click the accept button to save. "+tipText,
            ),
            # -----------------------Custom content------------------------
            MDDialogContentContainer(
                self._dialog_inputtext_module(tagName,value_old),
                orientation="vertical",
                
            ),
            # DialogContent(),
            # ---------------------Button container------------------------
            MDDialogButtonContainer(
                Widget(),
                MDButton(
                    MDButtonText(text="Cancel",id='test1'),
                    style="text",
                    # on_press=self.close_dateinput_dialog()
                    on_press = lambda _: self.dialog.dismiss() 
                ),
                MDButton(
                    MDButtonText(text="Accept"),
                    style="text",
                    on_press = comfirm_callback
                ),
                spacing="8dp",
            ),
            # -------------------------------------------------------------
            size_hint=(0.5,None)
        ) 
        self.dialog.open()

    def _dialog_inputtext_module(self,tagName,value_old):
        a= MDTextField(
                    MDTextFieldHintText(
                        text=tagName,
                    ),
                    # MDTextFieldMaxLengthText(
                    #     max_text_length=10,
                    # ),
                    mode="outlined",
                    size_hint_x=None,
                    width="240dp",
                    pos_hint={"center_x": 0.5, "center_y": 0.5},
                )
        a.text = value_old
        a.set_text=self._dialog_callback_inputText
        return a

    def _dialog_callback_inputText(self,*args):
        self._input_text = args[1]

    def set_setQueueMaxsizePCM_dialog(self):
        self._opendialog('Queue Maxsize',str(self._queueMaxsizePCM),self.set_setQueueMaxsizePCM_dialog_callback,
                        ' tip: QueueMaxsize is integer and bigger than threshold')
        
    def set_setQueueMaxsizePCM_dialog_callback(self,*args):
        try :
            maxsize = int(self._input_text)
        except Exception as e:
            print('just number allowed in input',repr(e))
            return
        if self._queueMaxsizePCM>self._thresholdPCM and maxsize<1000:
            self._udpReceiver.setQueueMaxsizePCM(maxsize)
            self.refresh_queueMaxsizePCM()
            self.dialog.dismiss()
        else:
            print('invalid input: queueMaxsizePCM ')

    def set_setQueueMaxsizeAAC_dialog(self):
        self._opendialog('Queue Maxsize',str(self._queueMaxsizeAAC),self.set_setQueueMaxsizeAAC_dialog_callback,
                        ' tip: QueueMaxsize is integer and bigger than threshold')
        
    def set_setQueueMaxsizeAAC_dialog_callback(self,*args):
        try :
            maxsize = int(self._input_text)
        except Exception as e:
            print('just number allowed in input',repr(e))
            return
        if self._queueMaxsizeAAC>self._thresholdAAC and maxsize<1000:
            self._udpReceiver.setQueueMaxsizeAAC(maxsize)
            self.refresh_queueMaxsizeAAC()
            self.dialog.dismiss()
        else:
            print('invalid input: queueMaxsizeAAC ')

    def set_set_thresholdAAC_dialog(self):
        self._opendialog('Queue Threshold',str(self._thresholdAAC),self.set_thresholdAAC_dialog_callback,
                        ' tip: threshold is integer and smaller than queue maxsize')
        
    def set_thresholdAAC_dialog_callback(self,*args):
        try :
            threshold = int(self._input_text)
        except Exception as e:
            print('just number allowed in input',repr(e))
            return
        if self._queueMaxsizeAAC>self._thresholdAAC and threshold<1000 and threshold>0:
            self._udpReceiver.setThresholdAAC(threshold)
            self.refresh_thresholdAAC()
            self.dialog.dismiss()
        else:
            print('invalid input: threshold ')

    def set_set_thresholdPCM_dialog(self):
        self._opendialog('Queue Threshold',str(self._thresholdPCM),self.set_thresholdPCM_dialog_callback,
                        ' tip: threshold is integer and smaller than queue maxsize')
        
    def DLNASeviceSwitch(self):
        if self._DLNASevice_on:
            self._udpReceiver.DLNAseverStop()
            self._DLNASevice_on = False
            self.ids.DLNAbutton.theme_bg_color="Primary"
        else:
            self._udpReceiver.DLNAseverRun()
            self._DLNASevice_on = True
            self.ids.DLNAbutton.theme_bg_color="Custom"
            self.ids.DLNAbutton.md_bg_color='green'

        
    def set_thresholdPCM_dialog_callback(self,*args):
        try :
            threshold = int(self._input_text)
        except Exception as e:
            print('just number allowed in input',repr(e))
            return
        if self._queueMaxsizePCM>self._thresholdPCM and threshold<1000 and threshold>0:
            self._udpReceiver.setThresholdPCM(threshold)
            self.refresh_thresholdPCM()
            self.dialog.dismiss()
        else:
            print('invalid input: threshold ')

    


class UdpMusicApp(MDApp):

    def build(self):
        Window.bind(on_request_close=self.close_window_callback)
        self.icon = 'icon/sendericon.ico'
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Green"  # "Purple", "Orange"
        self.sm = ScreenManager(transition=NoTransition())
        self.mainscreen = MainScreen(name = 'main')
        self.screen1 = SenderScreen(name='sender')
        self.screen2 = ReceiverScreen(name='receiver')
        self.sm.add_widget(self.mainscreen)
        self.sm.add_widget(self.screen1)
        self.sm.add_widget(self.screen2) 
        # sm.current='receiver'   
        return  self.sm
    

    def close_window_callback(self,*args):
        if self.screen1._power_on:
            self.screen1._musicSender.setDefaultSpeaker(self.screen1._previous_defualt_speaker)
    
    def open_receiver(self):
        self.sm.current='receiver'
        self.screen2._udpReceiver.commandSeverRun()

    
    

if __name__ == '__main__':
    Builder.load_file('udpMusic_gui.kv')
    UdpMusicApp().run()
