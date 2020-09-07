import tkinter as tk
import easygui
from scipy.io import wavfile
from scipy import signal
import numpy as np
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
matplotlib.use('TkAgg')

import threading
import sounddevice as sd
from scipy.io.wavfile import write
import time
import pylab

# global variable
isRecording = False
firstPart = False
recFile = None

class Application(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.width = 1200
        self.height = 800
        self.screen_w = self.winfo_screenwidth()
        self.screen_h = self.winfo_screenheight()

        x = (self.screen_w / 2) - (self.width / 2)
        y = (self.screen_h / 2) - (self.height / 2)

        self.geometry('%dx%d+%d+%d' % (self.width, self.height, x, y))

        # self.geometry("1200x800")
        container = tk.Frame(self)

        container.pack(side='top', fill='both', expand='True')

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}

        frame = MainPage(container, self)

        self.frames[MainPage] = frame

        frame.grid(row=0, column=0, sticky='nsew')

        self.show_frame(MainPage)

    def show_frame(self, key):
        frame = self.frames[key]
        frame.tkraise()


class MainPage(tk.Frame):

    def __init__(self, parent, controller):

        tk.Frame.__init__(self, parent)

        self.samples = None
        self.sample_rates = None
        self.isFileOpened = False
        self.frequencies = None
        self.times = None
        self.spectrogram = None
        self.canvas = None

        self.frame = tk.Frame(self, relief=tk.RAISED, borderwidth=1)
        self.frame.pack(fill=tk.BOTH)

        openFileButton = tk.Button(self.frame, text='Open wav file', command=self.openfile)
        openFileButton.grid(row=0,column=0)

        self.recordAudioButton = tk.Button(self.frame, text='Nagraj audio', command=lambda: self.startRecording("nagranie.wav"))
        self.recordAudioButton.grid(row=0,column=1)

        self.saveButton = tk.Button(self.frame, text='Zapisz wykresy', command=self.saveDiagrams)
        self.saveButton.config(state="disabled")
        self.saveButton.grid(row=0,column=2)

        self.printButton = tk.Button(self.frame, text='Drukuj', command=self.printDiagram)
        self.printButton.config(state="disabled")
        self.printButton.grid(row=0, column=3)

        self.tkvar = tk.StringVar(self.frame)
        self.choices = {'Hanning', 'Bartlett', 'Blackman'}
        self.popupMenu = tk.OptionMenu(self.frame, self.tkvar, *self.choices)
        self.popupMenu.grid(row=1, column=4)
        self.tkvar.set('Hanning')

        self.windowButton = tk.Button(self.frame, text='Okienkuj', command=self.windowing)
        self.windowButton.grid(row=0, column=4)
        self.windowButton.config(state="disabled")

        self.f = Figure(figsize=(6, 6), dpi=100)
        self.f.subplots_adjust(hspace=0.5)
        self.a = self.f.add_subplot(211)
        self.b = self.f.add_subplot(212)

    def printDiagram(self):
        import os
        self.saveDiagrams()
        os.startfile("diagrams.png", "print")
        self.saveButton.config(state='normal')
        self.printButton.config(state="disabled")




    def openfile(self):
        try:
            self.sample_rates, self.samples = wavfile.read(easygui.fileopenbox())

            if len(self.samples.shape) > 1:
                self.samples = self.samples[:, 0]

            self.isFileOpened = True

            if self.canvas is not None:
                self.canvas.get_tk_widget().destroy()

            self.canvas = FigureCanvasTkAgg(self.f, self)

            self.generate_audiogram()
            self.generate_spectogram()


            self.toolbar = NavigationToolbar2Tk(self.canvas, self)
            self.toolbar.update()
            self.canvas._tkcanvas.pack(fill=tk.BOTH, expand=True)


            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            self.saveButton.config(state="normal")
            self.printButton.config(state="normal")
            self.windowButton.config(state="normal")
        except TypeError:
            pass

    def windowing(self):
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(self.f, self)

        self.generate_spectogram()

        self.toolbar.destroy()
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        self.canvas._tkcanvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def generate_spectogram(self):
        self.a.clear()
        # self.frequencies, self.times, self.spectrogram = signal.spectrogram(self.samples, self.sample_rates)
        # self.a.pcolormesh(self.times, self.frequencies, self.spectrogram)
        self.a.set_ylabel('Czestotliwosc [Hz]')
        self.a.set_xlabel('Czas [s]')
        self.a.set_title("Spektogram")
        if self.tkvar.get() == 'Hanning':
            self.a.specgram(self.samples, Fs=self.sample_rates)
        elif self.tkvar.get() == 'Bartlett':
            self.a.specgram(self.samples, Fs=self.sample_rates, window=np.bartlett(256))
        elif self.tkvar.get() == 'Blackman':
            self.a.specgram(self.samples, Fs=self.sample_rates, window=np.blackman(256))


    def generate_audiogram(self):
        self.b.clear()

        file_length = self.samples.shape[0] / self.sample_rates

        seconds = np.arange(len(self.samples)) / float(self.sample_rates)

        # normalize values to (-1,1)
        max_element = np.amax(self.samples)
        min_element = np.amin(self.samples)
        element = max(abs(max_element), abs(min_element))
        normalized = self.samples / element

        # create plot
        self.b.plot(seconds, normalized)
        self.b.set_title('audiogram')
        self.b.set_xlabel('czas [s]')
        self.b.set_ylabel('amplituda')
        self.b.set_ylim(-1, 1)
        self.b.set_xlim(0.0, file_length)

    def record(self, seconds=2):
        fs = 44100
        global isRecording, firstPart, recFile
        if isRecording:
            if firstPart:
                recFile = sd.rec(int(0 * fs), samplerate=fs, channels=1)
                firstPart = False

        while isRecording:
            newRecording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
            sd.wait()
            # time.sleep(0.0001)
            recFile = np.concatenate((recFile, newRecording), axis=0)

        write('output.wav', fs, recFile)  # Save as WAV file

    def saveDiagrams(self):
        self.f.savefig('diagrams.png')
        self.saveButton.config(state="disabled")



    def startRecording(self, file_path):
        global isRecording
        if isRecording:
            isRecording = False
            self.recordAudioButton.config(text='nagraj audio')
        else:
            isRecording = True
            self.recordAudioButton.config(text='koniec nagrania')
            global firstPart
            firstPart = True
            t1 = threading.Thread(target=self.record)
            t1.start()

if __name__ == "__main__":
    app = Application()
    app.mainloop()
