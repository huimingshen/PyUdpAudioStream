'''
calsses for DLNA fuction and DLNA stream player
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

class VlcPlayer:
    '''
        args:设置 options
    '''
    def __init__(self, *args):
        if args:
            instance = vlc.Instance(*args) 
        else:
            instance = vlc.Instance(*args)
        self.media = instance.media_player_new()
        self.url = None

    # 设置待播放的url地址或本地文件路径，每次调用都会重新加载资源
    def set_url(self, url):
        self.media.set_mrl(url)

    # 播放 成功返回0，失败返回-1
    def play(self, path=None):
        if path:
            self.set_url(path)
            return self.media.play()
        else:
            return self.media.play()

    # 暂停
    def pause(self):
        self.media.pause()

    # 恢复
    def resume(self):
        self.media.set_pause(0)

    # 停止
    def stop(self):
        self.media.stop()

    # 释放资源
    def release(self):
        return self.media.release()

    # 是否正在播放
    def is_playing(self):
        return self.media.is_playing()

    # 已播放时间，返回毫秒值
    def get_time(self):
        return self.media.get_time()

    # 拖动指定的毫秒值处播放。成功返回0，失败返回-1 (需要注意，只有当前多媒体格式或流媒体协议支持才会生效)
    def set_time(self, ms):
        return self.media.set_time(ms)

    # 音视频总长度，返回毫秒值
    def get_length(self):
        return self.media.get_length()

    # 获取当前音量（0~100）
    def get_volume(self):
        return self.media.audio_get_volume()

    # 设置音量（0~100）
    def set_volume(self, volume):
        return self.media.audio_set_volume(volume)

    # 返回当前状态：正在播放；暂停中；其他
    def get_state(self):
        state = self.media.get_state()
        if state == vlc.State.Playing:
            return 1
        elif state == vlc.State.Paused:
            return 0
        else:
            return -1

    # 当前播放进度情况。返回0.0~1.0之间的浮点数
    def get_position(self):
        return self.media.get_position()

    # 拖动当前进度，传入0.0~1.0之间的浮点数(需要注意，只有当前多媒体格式或流媒体协议支持才会生效)
    def set_position(self, float_val):
        return self.media.set_position(float_val)

    # 获取当前文件播放速率
    def get_rate(self):
        return self.media.get_rate()

    # 设置播放速率（如：1.2，表示加速1.2倍播放）
    def set_rate(self, rate):
        return self.media.set_rate(rate)

    # 设置宽高比率（如"16:9","4:3"）
    def set_ratio(self, ratio):
        self.media.video_set_scale(0)  # 必须设置为0，否则无法修改屏幕宽高
        self.media.video_set_aspect_ratio(ratio)

    # 注册监听器
    def add_callback(self, event_type, callback):
        self.media.event_manager().event_attach(event_type, callback)

    # 移除监听器
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
    
    
    # cli(VLCRenderer())
    pass