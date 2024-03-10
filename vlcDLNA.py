'''
calsses for DLNA fuction and DLNA stream player, based on packet: macast
'''
import os
import time
import threading
import subprocess
from macast import cli,Service,Setting
from macast.renderer import Renderer
import logging
# logging.disable(logging.CRITICAL)
os.environ['PYTHON_VLC_MODULE_PATH'] = "VLC"
import vlc
# from terminal_layout.extensions.progress import Loading
import inspect
import ctypes

# class for the API of VLC player 
class VlcPlayer:
    '''
        args: set options
    '''
    def __init__(self, *args):
        if args:
            instance = vlc.Instance(*args) 
        else:
            instance = vlc.Instance(*args)
        self.media = instance.media_player_new()
        self.url = None

    # play the resource from file or url address in internet
    def set_url(self, url):
        self.media.set_mrl(url)

    # play, if succefully return 0， otherwise -1
    def play(self, path=None):
        if path:
            self.set_url(path)
            return self.media.play()
        else:
            return self.media.play()

    # pause
    def pause(self):
        self.media.pause()

    # resume
    def resume(self):
        self.media.set_pause(0)

    # stop
    def stop(self):
        self.media.stop()

    # release
    def release(self):
        return self.media.release()

    # check, wheather is it palying
    def is_playing(self):
        return self.media.is_playing()

    # get the time of playing position (ms)
    def get_time(self):
        return self.media.get_time()

    # set playing position (ms), if succefully return 0， otherwise -1
    def set_time(self, ms):
        return self.media.set_time(ms)

    # get video/audio length (ms)
    def get_length(self):
        return self.media.get_length()

    # get volume（0~100）
    def get_volume(self):
        return self.media.audio_get_volume()

    # set volume（0~100）
    def set_volume(self, volume):
        return self.media.audio_set_volume(volume)

    # get status
    def get_state(self):
        state = self.media.get_state()
        if state == vlc.State.Playing:
            return 1
        elif state == vlc.State.Paused:
            return 0
        else:
            return -1

    # get playing position 0.0~1.0
    def get_position(self):
        return self.media.get_position()

    # set playing position，0.0~1.0
    def set_position(self, float_val):
        return self.media.set_position(float_val)

    # get rate
    def get_rate(self):
        return self.media.get_rate()

    # set playing rate
    def set_rate(self, rate):
        return self.media.set_rate(rate)

    # set vedio ratio
    def set_ratio(self, ratio):
        self.media.video_set_scale(0)  # 必须设置为0，否则无法修改屏幕宽高
        self.media.video_set_aspect_ratio(ratio)

    # callback
    def add_callback(self, event_type, callback):
        self.media.event_manager().event_attach(event_type, callback)


    def remove_callback(self, event_type, callback):
        self.media.event_manager().event_detach(event_type, callback)

class VLCRenderer(Renderer):
    def __init__(self):
        super(VLCRenderer, self).__init__()
        self.position_thread = threading.Thread(target=self.position_tick, daemon=True)
        self.position_thread.start()
        # a thread is started here to increase the playback position once per second
        # to simulate that the media is playing.

    vlcplayer = VlcPlayer()
    styleLogoList = ['⣾', '⣷', '⣯', '⣟', '⡿', '⢿', '⣻', '⣽']
    styleLogoIndx = 0
    def position_tick(self):
        while True:
            if self.vlcplayer.get_state() == 1:
                sec_now= int(self.vlcplayer.get_time()/1000)
                position = '%d:%02d:%02d' % (sec_now // 3600, (sec_now % 3600) // 60, sec_now % 60)
                self.set_state_position(position)
                sec_duration = int(self.vlcplayer.get_length()/1000)
                duration = '%d:%02d:%02d' % (sec_duration // 3600, (sec_duration % 3600) // 60, sec_duration % 60)
                self.set_state_duration(duration)
                styleLogo = self.styleLogoList[self.styleLogoIndx]
                percent = int(sec_now/sec_duration*100)
                print("\r"+f" \033[1;32;40m Playing {styleLogo} {percent}% : {position}/{duration} \033[0m",end='')
                self.styleLogoIndx+=1
                self.styleLogoIndx= self.styleLogoIndx%7
            time.sleep(1)
            

    def set_media_stop(self):
        self.vlcplayer.stop()
        self.set_state_transport('STOPPED')

    def set_media_url(self, url):
        self.set_media_stop()
        self.vlcplayer.play(url)
        self.set_state_transport("PLAYING")
        # self.set_state_volume(100)
        

    def set_media_pause(self):
        self.vlcplayer.pause()
        self.set_state_transport("PAUSED_PLAYBACK")
    
    def set_media_resume(self):
        self.vlcplayer.resume()
        self.set_state_transport("PLAYING")

    def set_media_position(self, data):
        h,m,s = data.strip().split(":")
        sec = int(h)*3600+int(m)*60+int(s)
        self.vlcplayer.set_time(sec*1000)

    def set_media_volume(self, data):
        print("set volume to: "+ data)
        self.vlcplayer.set_volume(int(data))

    def stop(self):
        super(VLCRenderer, self).stop()
        self.set_media_stop()
        print("VLCPlayer stop")

    def start(self):
        super(VLCRenderer, self).start()
        print("VLCPlayer start")


class DLNAService(Service):
    def stopDLNA(self):
        exit(0)


if __name__ == '__main__':

    cli(VLCRenderer())