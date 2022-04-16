# -*- coding: utf-8 -*-

"""
Module implementing Player.
"""

from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QMessageBox, QTableWidgetItem

from Ui_MainWindow import Ui_MainWindow
from Music import Music

import os
import re
import time


class Player(QMainWindow, Ui_MainWindow):
    """
    Class documentation goes here.
    """

    def __init__(self, parent=None):
        """
        Constructor
        
        @param parent reference to the parent widget
        @type QWidget
        """
        super(Player, self).__init__(parent)
        self.setupUi(self)
        self.init_ui_states()
        self.init_ui_signals_slots()
        self.init_music()

    def init_ui_states(self):
        self.pushButton_play.setCheckable(True)
        self.on_off_ui(False)

    def init_ui_signals_slots(self):
        self.horizontalSlider_time.sliderMoved.connect(lambda x: self.statusbar.showMessage(self.sec2hms(x / 1000)))
        self.horizontalSlider_rate.sliderMoved.connect(lambda x: self.statusbar.showMessage('速度：%+4d %%' % x))
        self.horizontalSlider_pitch.sliderMoved.connect(lambda x: self.statusbar.showMessage('音调：%+8.2f' % (x / 100)))
        self.horizontalSlider_tempo.sliderMoved.connect(lambda x: self.statusbar.showMessage('节拍：%+4d %%' % x))

        self.horizontalSlider_time.sliderReleased.connect(self.statusbar.clearMessage)
        self.horizontalSlider_rate.sliderReleased.connect(self.statusbar.clearMessage)
        self.horizontalSlider_pitch.sliderReleased.connect(self.statusbar.clearMessage)
        self.horizontalSlider_tempo.sliderReleased.connect(self.statusbar.clearMessage)

        self.doubleSpinBox_rate.valueChanged.connect(lambda x: self.horizontalSlider_rate.setValue(int(x)))
        self.doubleSpinBox_pitch.valueChanged.connect(lambda x: self.horizontalSlider_pitch.setValue(round(x * 100.)))
        self.doubleSpinBox_tempo.valueChanged.connect(lambda x: self.horizontalSlider_tempo.setValue(int(x)))

        self.pushButton_rate.clicked.connect(lambda: self.horizontalSlider_rate.setValue(0))
        self.pushButton_pitch.clicked.connect(lambda: self.horizontalSlider_pitch.setValue(0))
        self.pushButton_tempo.clicked.connect(lambda: self.horizontalSlider_tempo.setValue(0))

        self.action_exit.triggered.connect(self.close)
        self.action_aboutqt.triggered.connect(lambda: QMessageBox.aboutQt(None))

    def init_music(self):
        self.directory = r'F:\Dell\Music'

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)

        self.playmusic = PlayThread()
        self.playmusic.end_sigOut.connect(self.reset)

    def update_time(self):
        time = self.playmusic.music.tell()
        self.label_time.setText(self.sec2hms(time))
        if self.horizontalSlider_time.isSliderDown():
            return
        else:
            self.horizontalSlider_time.setSliderPosition(int(time * 1000))

    def reset(self):
        if self.pushButton_play.isChecked():
            self.pushButton_play.click()
        self.pushButton_begin.click()

    @pyqtSlot()
    def on_pushButton_begin_clicked(self):
        """
        Slot documentation goes here.
        """
        self.horizontalSlider_time.setValue(0)
        self.label_time.setText(self.sec2hms(0))

    @pyqtSlot(int)
    def on_horizontalSlider_time_valueChanged(self, milliseconds):
        """
        Slot documentation goes here.

        @param value DESCRIPTION
        @type int
        """
        self.playmusic.music.seek(milliseconds / 1000)

    @pyqtSlot(int)
    def on_horizontalSlider_rate_valueChanged(self, value):
        """
        Slot documentation goes here.

        @param value DESCRIPTION
        @type int
        """
        self.playmusic.music.rate = value
        self.doubleSpinBox_rate.setValue(value)

    @pyqtSlot(int)
    def on_horizontalSlider_pitch_valueChanged(self, value):
        """
        Slot documentation goes here.

        @param value DESCRIPTION
        @type int
        """
        self.playmusic.music.pitch = round(value / 100, 2)
        self.doubleSpinBox_pitch.setValue(round(value / 100, 2))

    @pyqtSlot(int)
    def on_horizontalSlider_tempo_valueChanged(self, value):
        """
        Slot documentation goes here.

        @param value DESCRIPTION
        @type int
        """
        self.playmusic.music.tempo = value
        self.doubleSpinBox_tempo.setValue(value)

    @pyqtSlot(bool)
    def on_radioButton_loop_toggled(self, checked):
        """
        Slot documentation goes here.
        
        @param checked DESCRIPTION
        @type bool
        """
        self.playmusic.music.loop = checked

    @pyqtSlot(bool)
    def on_pushButton_play_clicked(self, checked):
        """
        Slot documentation goes here.
        
        @param checked DESCRIPTION
        @type bool
        """
        if checked:
            self.playmusic.music.pause = False
            self.timer.start(50)
            self.pushButton_play.setText("暂停")
        else:
            self.playmusic.music.pause = True
            self.timer.stop()
            self.pushButton_play.setText("播放")

    @pyqtSlot()
    def on_action_open_triggered(self):
        """
        Slot documentation goes here.
        """
        path = QFileDialog.getOpenFileName(self, caption='打开音频文件', directory=self.directory,
                                           filter=r'''
                                           Audio files(*.aac;*.ape;*.flac;*.m4a;*.mp3;*.wav);;
                                           All Files(*.*)''')[0]
        if path == '':
            return
        try:
            self.playmusic.music.load(path)

            self.directory, filename = os.path.split(self.playmusic.music.path)
            filesize = re.findall(r'Length.*?(\d+)\n', self.playmusic.music.sf_info.extra_info)
            filesize = '{:,} 字节'.format(int(filesize[0])).replace(',', ' ') if filesize else '未知 字节'
            duration = self.sec2hms(self.playmusic.music.sf_info.duration, r'{:.0f}:{:.0f}:{:.0f}')
            frames = ' （{:,} 采样）'.format(self.playmusic.music.sf_info.frames).replace(',', ' ')
            samplerate = '{} Hz'.format(self.playmusic.music.sf_info.samplerate)
            channels = str(self.playmusic.music.sf_info.channels)
            subtype_info = self.playmusic.music.sf_info.subtype_info
            self.tableWidget.setItem(0, 1, QTableWidgetItem(filename))
            self.tableWidget.setItem(1, 1, QTableWidgetItem(filesize))
            self.tableWidget.setItem(2, 1, QTableWidgetItem(duration + frames))
            self.tableWidget.setItem(3, 1, QTableWidgetItem(samplerate))
            self.tableWidget.setItem(4, 1, QTableWidgetItem(channels))
            self.tableWidget.setItem(5, 1, QTableWidgetItem(subtype_info))
            self.tableWidget.resizeColumnToContents(1)

            self.pushButton_begin.click()
            self.horizontalSlider_time.setMaximum(int(self.playmusic.music.sf_info.duration * 1000))
            self.on_off_ui(True)
            self.playmusic.start()
        except:
            QMessageBox.warning(self, '警告', '文件打开失败')

    @pyqtSlot()
    def on_action_save_triggered(self):
        """
        Slot documentation goes here.
        """
        _wp = QFileDialog.getSaveFileName(self, caption='另存为', directory=self.directory,
                                          filter=r'WAV(*.wav);;All Files(*.*)')[0]
        if _wp == '':
            return
        _rp = os.path.abspath(self.playmusic.music.path)
        if os.path.abspath(_wp) == _rp:
            QMessageBox.information(self, '提示', '输出文件路径不能与打开文件相同')
            return

        rate = self.playmusic.music.rate
        pitch = self.playmusic.music.pitch
        tempo = self.playmusic.music.tempo
        _str = os.popen(
            r'''soundstretch "%s" "%s" -rate=%d -pitch=%.2f -tempo=%d''' % (_rp, _wp, rate, pitch, tempo)).read()
        print(_str)

    @pyqtSlot()
    def on_action_usinghelp_triggered(self):
        """
        Slot documentation goes here.
        """
        _string = '''
        变速（速度，rate，变速变调）
        变调（音调，pitch，变调不变速）
        变拍（节拍，tempo，变速不变调）
        '''
        QMessageBox.about(self, '使用帮助', _string)

    def on_off_ui(self, able: bool):
        self.horizontalSlider_time.setEnabled(able)
        self.horizontalSlider_rate.setEnabled(able)
        self.horizontalSlider_pitch.setEnabled(able)
        self.horizontalSlider_tempo.setEnabled(able)
        self.doubleSpinBox_rate.setEnabled(able)
        self.doubleSpinBox_pitch.setEnabled(able)
        self.doubleSpinBox_tempo.setEnabled(able)
        self.pushButton_rate.setEnabled(able)
        self.pushButton_pitch.setEnabled(able)
        self.pushButton_tempo.setEnabled(able)
        self.pushButton_play.setEnabled(able)
        self.pushButton_begin.setEnabled(able)
        self.radioButton_loop.setEnabled(able)

    def closeEvent(self, event):
        reply = QMessageBox.question(self, '询问', '确定退出吗？',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self.timer.stop()
            self.playmusic.exit()
            time.sleep(0.1)
            event.accept()
        else:
            event.ignore()

    @staticmethod
    def sec2hms(sec, hms_mat=r'{:0>2.0f}:{:0>2.0f}:{:0>6.3f}'):
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        return hms_mat.format(h, m, s)


class PlayThread(QThread):
    end_sigOut = pyqtSignal()

    def __init__(self, parent=None):
        super(PlayThread, self).__init__(parent)
        self.music = Music()

    def __del__(self):
        self.music.exit()

    def run(self):
        def playmusic():
            try:
                self.music.play()
            except:
                pass

        while True:
            self.music.wait()
            playmusic()
            while self.music.loop:
                self.music.seek(0)
                playmusic()
            self.music.pause = True
            self.end_sigOut.emit()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    player = Player()
    player.show()
    sys.exit(app.exec_())
