# -*- coding: utf-8 -*-

'''
一次性读取音频文件：
from scipy.io import wavfile

rate, wav = wavfile.read('')
wav = wav.astype(np.float32)
if not wav.flags['C_CONTIGUOUS']:
    wav = np.ascontiguousarray(wav, dtype=wav.dtype)  # 如果不是C连续的内存，必须强制转换


'''

import ctypes
import numpy as np
from numpy.ctypeslib import ndpointer
from sounddevice import OutputStream
import soundfile as sf
import sys
import os
import time


class Music(object):
    def __init__(self):
        self.dll_init()
        self.instance = self.soundtouch_createInstance()

        self._rec_samples = 4096  # How many samples to receive at max.
        self._rate = 0  # 速度
        self._pitch = 0.  # 音调
        self._tempo = 0  # 节拍
        self._pause = True
        self._loop = False

    def dll_init(self):
        self.dll = ctypes.CDLL("SoundTouch_x64.dll")

        self.soundtouch_getVersionString = self.dll.soundtouch_getVersionString
        self.soundtouch_getVersionString.restype = ctypes.c_char_p
        versionString = self.soundtouch_getVersionString().decode(encoding='gbk', errors='replace')
        print('SoundTouch Version:', versionString)

        self.soundtouch_getVersionId = self.dll.soundtouch_getVersionId
        self.soundtouch_getVersionId.restype = ctypes.c_uint

        self.soundtouch_createInstance = self.dll.soundtouch_createInstance
        self.soundtouch_createInstance.restype = ctypes.c_void_p

        self.soundtouch_setSampleRate = self.dll.soundtouch_setSampleRate
        self.soundtouch_setSampleRate.argtypes = [ctypes.c_void_p, ctypes.c_int]

        self.soundtouch_setChannels = self.dll.soundtouch_setChannels
        self.soundtouch_setChannels.argtypes = [ctypes.c_void_p, ctypes.c_uint]

        # Sets new rate control value as a difference in percents compared to the original rate (-50 .. +100 %)
        self.soundtouch_setRateChange = self.dll.soundtouch_setRateChange
        self.soundtouch_setRateChange.argtypes = [ctypes.c_void_p, ctypes.c_float]

        # Sets pitch change in semi-tones（半音阶） compared to the original pitch (-12 .. +12)
        self.soundtouch_setPitchSemiTones = self.dll.soundtouch_setPitchSemiTones
        self.soundtouch_setPitchSemiTones.argtypes = [ctypes.c_void_p, ctypes.c_float]

        # Sets new tempo（节拍） control value as a difference in percents compared to the original tempo (-50 .. +100 %)
        self.soundtouch_setTempoChange = self.dll.soundtouch_setTempoChange
        self.soundtouch_setTempoChange.argtypes = [ctypes.c_void_p, ctypes.c_float]

        self.soundtouch_putSamples = self.dll.soundtouch_putSamples
        self.soundtouch_putSamples.argtypes = [ctypes.c_void_p, ndpointer(dtype=ctypes.c_float), ctypes.c_uint]

        self.soundtouch_receiveSamples = self.dll.soundtouch_receiveSamples
        self.soundtouch_receiveSamples.argtypes = [ctypes.c_void_p, ndpointer(dtype=ctypes.c_float), ctypes.c_uint]
        self.soundtouch_receiveSamples.restype = ctypes.c_uint

        self.soundtouch_numUnprocessedSamples = self.dll.soundtouch_numUnprocessedSamples
        self.soundtouch_numUnprocessedSamples.argtypes = [ctypes.c_void_p]
        self.soundtouch_numUnprocessedSamples.restype = ctypes.c_uint

        self.soundtouch_numSamples = self.dll.soundtouch_numSamples
        self.soundtouch_numSamples.argtypes = [ctypes.c_void_p]
        self.soundtouch_numSamples.restype = ctypes.c_uint

        self.soundtouch_flush = self.dll.soundtouch_flush
        self.soundtouch_flush.argtypes = [ctypes.c_void_p]

        self.soundtouch_clear = self.dll.soundtouch_clear
        self.soundtouch_clear.argtypes = [ctypes.c_void_p]

        self.soundtouch_destroyInstance = self.dll.soundtouch_destroyInstance
        self.soundtouch_destroyInstance.argtypes = [ctypes.c_void_p]

    def load(self, path):
        '''

        :param path:
        :return:
        soundfile.info
            self.name = f.name
            self.samplerate = f.samplerate
            self.channels = f.channels
            self.frames = f.frames
            self.duration = float(self.frames)/f.samplerate
            self.format = f.format
            self.subtype = f.subtype
            self.endian = f.endian
            self.format_info = f.format_info
            self.subtype_info = f.subtype_info
            self.sections = f.sections
            self.extra_info = f.extra_info

        '''

        if os.path.splitext(path)[1].lower() != '.wav':
            base, name = os.path.split(path)
            name = '~$' + os.path.splitext(name)[0] + '.wav'
            _path = os.path.join(base, name)
            _str = os.popen(r'''ffmpeg -n -i "%s" "%s"''' % (path, _path)).read()
            print(_str)
        else:
            _path = path

        self.path = _path
        self.sf_info = sf.info(self.path)

        self._rec_buffer = np.zeros((self._rec_samples, self.sf_info.channels), dtype=np.float32)
        self.soundtouch_setSampleRate(self.instance, self.sf_info.samplerate)
        self.soundtouch_setChannels(self.instance, self.sf_info.channels)

        if hasattr(self, 'sf_file'):
            self.sf_file.close()
        self.sf_file = sf.SoundFile(self.path, mode='r')

    def play(self):
        with OutputStream(samplerate=self.sf_info.samplerate, channels=self.sf_info.channels) as out_stream:
            block = self.sf_file.read(frames=2048, dtype='float32')
            while block.size > 0:
                self.soundtouch_putSamples(self.instance, block, block.shape[0])
                nSamples = self.soundtouch_receiveSamples(self.instance, self._rec_buffer, self._rec_samples)
                while nSamples > 0:
                    self.wait()
                    out_stream.write(self._rec_buffer[:nSamples])
                    nSamples = self.soundtouch_receiveSamples(self.instance, self._rec_buffer, self._rec_samples)
                block = self.sf_file.read(frames=2048, dtype='float32')
            self.soundtouch_flush(self.instance)
            nSamples = self.soundtouch_receiveSamples(self.instance, self._rec_buffer, self._rec_samples)
            while nSamples > 0:
                self.wait()
                out_stream.write(self._rec_buffer[:nSamples])
                nSamples = self.soundtouch_receiveSamples(self.instance, self._rec_buffer, self._rec_samples)

    def seek(self, seconds):
        if seconds < 0:
            seconds = 0
        if seconds > self.sf_info.duration:
            seconds = self.sf_info.duration - 1.
        frames = int(seconds / self.sf_info.duration * self.sf_info.frames)
        self.sf_file.seek(frames)
        self.soundtouch_clear(self.instance)

    def tell(self) -> float:
        return self.sf_file.tell() / self.sf_info.frames * self.sf_info.duration

    def wait(self, seconds=0.01):
        while self.pause:
            time.sleep(seconds)

    def exit(self):
        self.pause = True
        if hasattr(self, 'sf_file'):
            self.sf_file.close()
        self.soundtouch_clear(self.instance)
        self.soundtouch_destroyInstance(self.instance)

    @property
    def rate(self):
        return self._rate

    @rate.setter
    def rate(self, value):
        self.soundtouch_setRateChange(self.instance, float(value))
        self._rate = value

    @property
    def pitch(self):
        return self._pitch

    @pitch.setter
    def pitch(self, value):
        self.soundtouch_setPitchSemiTones(self.instance, float(value))
        self._pitch = value

    @property
    def tempo(self):
        return self._tempo

    @tempo.setter
    def tempo(self, value):
        self.soundtouch_setTempoChange(self.instance, float(value))
        self._tempo = value

    @property
    def pause(self):
        return self._pause

    @pause.setter
    def pause(self, value):
        self._pause = value

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value):
        self._loop = value


if __name__ == '__main__':
    music = Music()
    music.exit()

    sys.exit()
