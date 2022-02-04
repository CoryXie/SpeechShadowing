from fnmatch import translate
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
from turtle import width
from spleeter.separator import Separator
import tkinter.font as tkFont
import recorder
import AudioFile
import audioSplitter
import os
import time
from os.path import join, getsize
import math
import shutil
import threading
import configparser
import markdown
import webbrowser
import markdown
import utils
import SpeechToText
import TranslateText
import ichiran

# --- global values ---
global originAudioFolder
global currentAudioFolder
global recordedAudioFolder
global silenceThreshold
global repeatPlayCount
global autoPlayNext
global autoSTTNext

originAudioFolder = "./TargetAudio"
currentAudioFolder = ""
recordedAudioFolder = "./RecordedAudio"
silenceThreshold = -36
repeatPlayCount = 1

# --- functions ---

# -- helper functions


def getTargetAudioFileName():
    selectedTuple = targetAudioListBox.curselection()
    if (len(selectedTuple) > 0):
        filename = targetAudioListBox.get(selectedTuple[0])
        filename = filename[0:filename.rfind(" - ")]
        return filename
    else:
        print("selectedTuple is not greater than 0")
        return ''


def getOriginAudioFileName():
    selectedTuple = originAudioListBox.curselection()
    if (len(selectedTuple) > 0):
        filename = originAudioListBox.get(selectedTuple[0])
        filename = filename[0:filename.rfind(" - ")]
        return filename
    else:
        print("selectedTuple is not greater than 0")
        return ''


def getRecordedAudioFileName():
    targetFilename = getOriginAudioFileName()
    if targetFilename != '':
        filename = "recordedAudio-" + \
            targetFilename[0:len(targetFilename)-4] + ".wav"
        return filename
    else:
        print("targetfilename doesn't exist")
        return ''


def loadTargetAudioList(folder):
    # remove all elements in targetAudioListbox
    targetAudioListBox.delete(0, targetAudioListBox.size())
    # loop thru files
    fileList = os.listdir(folder)
    fileList.sort()
    fileformat = speechTextConfig["DEFAULT"]["format"]
    for file in fileList:
        if file[len(file) - 4:] in [fileformat]:
            displayname = file
            audioFile = AudioFile.audiofile(os.path.join(folder, file))
            length = audioFile.length()
            displaylength = ""
            if length > 60:
                displaylength = str(math.floor(length/60)) + \
                    ":" + str(math.floor(length % 60)).zfill(2)
            else:
                displaylength = str(math.floor(length % 60)) + " seconds"
            foldername = os.path.basename(os.path.normpath(folder))
            if (speechTextConfig.has_option(foldername, file) and
                    len(speechTextConfig[foldername][file].strip()) > 0):
                displayname += " - " + displaylength + \
                    " [" + speechTextConfig[foldername][file] + "]"
            else:
                displayname += " - " + displaylength
            targetAudioListBox.insert("end", displayname)
            targetAudioListBox.see(targetAudioListBox.size())
            utils.root.update()


def loadOriginAudioList():
    # remove all elements in originAudioListBox
    originAudioListBox.delete(0, originAudioListBox.size())
    # loop thru files
    fileList = os.listdir(originAudioFolder)
    fileList.sort()
    for file in fileList:
        if file[len(file) - 4:] in [".wav", ".mp3"]:
            displayname = file
            audioFile = AudioFile.audiofile(
                os.path.join(originAudioFolder, file))
            length = audioFile.length()
            displaylength = ""
            if length > 60:
                displaylength = str(math.floor(length/60)) + \
                    ":" + str(math.floor(length % 60)).zfill(2)
            else:
                displaylength = str(math.floor(length % 60)) + " seconds"
            displayname += " - " + displaylength
            originAudioListBox.insert("end", displayname)
            originAudioListBox.see(targetAudioListBox.size())
            utils.root.update()


def refreshOriginAudioList():
    global running
    if running is not None:
        utils.displayErrorMessage('recording audio, gotta stop that first')
    else:
        loading = threading.Thread(target=loadOriginAudioList)
        loading.start()


def refreshTargetAudioList():
    global running
    global currentAudioFolder
    if running is not None:
        utils.displayErrorMessage('recording audio, gotta stop that first')
    else:
        loading = threading.Thread(
            target=loadTargetAudioList, args=(currentAudioFolder,))
        loading.start()


def splitOriginAudioList(filename):
    global running
    global currentAudioFolder
    if running is not None:
        utils.displayErrorMessage('recording audio, gotta stop that first')
    else:
        silenceThreshold = int(combo_min_silence_threshold.get())
        silenceLength = int(combo_min_silence_length.get())
        audiosplit = audioSplitter.AudioSplitter(
            originAudioFolder, filename, currentAudioFolder,
            minsilencelen=silenceLength,
            silencethresh=silenceThreshold)
        audiosplit.split()
        loadTargetAudio()


def initialChecks():
    global running
    # general things to do before running events
    if running is not None:
        utils.displayErrorMessage('Recording Audio, Stop That First')
        return False
    utils.displayErrorMessage('')
    utils.displayInfoMessage('')
    return True

# -- event functions


def openHelp(event=None):
    if not os.path.exists("./README.html"):
        if os.path.exists("./README.MD"):
            markdown.markdownFromFile(
                input="./README.MD", output="./README.html")
        else:
            utils.displayErrorMessage("Cannot find help page")
            return
    webbrowser.open('./README.html')

# -- Target Audio Events --


def uploadTargetAudio(event=None):
    if initialChecks():
        filenames = filedialog.askopenfilenames(
            title="Select Target Audio", filetypes=[("Audio Files", ".mp3 .wav")])
        for filename in filenames:
            shutil.copy(filename, originAudioFolder)
        if (len(filenames) > 0):
            refreshOriginAudioList()


def separateAudio(filename):
    global currentAudioFolder
    global silenceThreshold
    print("Separating " + filename)
    silenceThreshold = int(combo_min_silence_threshold.get())
    silenceLength = int(combo_min_silence_length.get())
    audiosplit = audioSplitter.AudioSplitter(
        originAudioFolder, filename, currentAudioFolder,
        minsilencelen=silenceLength,
        silencethresh=silenceThreshold)
    audiosplit.splitVocals()
    loadTargetAudio()


def separateAudioVocals(event=None):
    global silenceThreshold
    global currentAudioFolder
    if initialChecks():
        filename = getOriginAudioFileName()
        if filename != '':
            pathparts = filename.rsplit(".", 1)
            foldername = pathparts[0]
            filepath = os.path.join(originAudioFolder, foldername)
            currentAudioFolder = filepath
            if not os.path.exists(currentAudioFolder):
                os.makedirs(currentAudioFolder)
            separating = threading.Thread(
                target=separateAudio, args=(filename,))
            separating.start()
        else:
            utils.displayErrorMessage('Select Origin Audio To Split')


def deleteOriginAudio(event=None):
    # remove all elements in targetAudioListbox
    if initialChecks():
        filename = getOriginAudioFileName()
        os.remove(os.path.join(originAudioFolder, filename))
        refreshOriginAudioList()


def deleteTargetAudio(event=None):
    global currentAudioFolder
    # remove all elements in targetAudioListbox
    if initialChecks():
        filename = getTargetAudioFileName()
        os.remove(os.path.join(currentAudioFolder, filename))
        refreshTargetAudioList()


def splitOriginAudio(event=None):
    global silenceThreshold
    global currentAudioFolder
    if initialChecks():
        filename = getOriginAudioFileName()
        if filename != '':
            pathparts = filename.rsplit(".", 1)
            foldername = pathparts[0]
            filepath = os.path.join(originAudioFolder, foldername)
            currentAudioFolder = filepath
            if not os.path.exists(currentAudioFolder):
                os.makedirs(currentAudioFolder)
            splitting = threading.Thread(
                target=splitOriginAudioList, args=(filename,))
            splitting.start()
        else:
            utils.displayErrorMessage('Select Target Audio To Split')


def convertSpeechText(event=None):
    global currentAudioFolder
    if initialChecks():
        filename = getTargetAudioFileName()
        if filename != '':
            foldername = currentAudioFolder
            wavename = filename.rsplit(".", 1)[0] + ".wav"
            if (speechTextConfig.has_option(foldername, filename) and
                    len(speechTextConfig[foldername][filename].strip()) > 0):
                speech = SpeechToText.SpeechToText(
                    foldername, wavename, "config.ini")
                speechtext = speech.stt()
            else:
                speechtext = speechTextConfig[currentAudioFolder][filename].strip(
                )
            speechtextEditArea.delete("1.0", tk.END)
            speechtextEditArea.insert("end-1c", speechtext)
            if (speechTextConfig.has_option(foldername + "_zh", filename) and
                    len(speechTextConfig[foldername + "_zh"][filename].strip()) > 0):
                speechinfoEditArea.insert(
                    "end-1c", speechTextConfig[foldername + "_zh"][filename])
            elif (len(speechtext) > 0):
                translater = TranslateText.TranslateText(cfgfile="config.ini")
                speechtext = translater.translate(speechtext)
                if (len(speechtext) > 0):
                    speechinfoEditArea.insert("end-1c", speechtext)
                    speechTextConfig[foldername + "_zh"][filename] = speechtext
                    speechfilepath = os.path.join(
                        currentAudioFolder, foldername + "_speechtext.txt")
                    speechTextConfig.write(open(speechfilepath, "w"))
        else:
            utils.displayErrorMessage("Select Target Audio First 1")


def saveSpeechText(event=None):
    global currentAudioFolder
    global speechTextConfig
    if initialChecks():
        filename = getTargetAudioFileName()
        if filename != '':
            foldername = os.path.basename(os.path.normpath(currentAudioFolder))
            speechfilepath = os.path.join(
                currentAudioFolder, foldername + "_speechtext.txt")
            speechTextConfig[foldername][filename] = speechtextEditArea.get(
                '0.0', tk.END).strip()
            speechTextConfig[foldername + "_zh"][filename] = speechinfoEditArea.get(
                '0.0', tk.END).strip()
            speechTextConfig.write(open(speechfilepath, "w"))
        else:
            utils.displayErrorMessage("Select Target Audio First 2")


def infoSpeechText(event=None):
    if initialChecks():
        speechtext = speechtextEditArea.get(
            '0.0', tk.END).strip()
        speechinfo = ichiran.ichiran(speechtext).info()
        speechinfoEditArea.delete("1.0", tk.END)
        speechinfoEditArea.insert("end-1c", speechinfo)


def loadSpeechText(event=None):
    global currentAudioFolder
    global speechTextConfig
    if initialChecks():
        filename = getTargetAudioFileName()
        if filename != '':
            foldername = os.path.basename(os.path.normpath(currentAudioFolder))
            wavename = filename.rsplit(".", 1)[0] + ".wav"
            speechtextEditArea.delete("1.0", tk.END)
            speechinfoEditArea.delete("1.0", tk.END)
            speechtext = ""
            if (speechTextConfig.has_option(foldername, filename) and
                    len(speechTextConfig[foldername][filename].strip()) > 0):
                speechtext = speechTextConfig[foldername][filename]
                speechtextEditArea.insert("end-1c", speechtext)
            elif (autoSTTNext.get() == 1):
                speech = SpeechToText.SpeechToText(
                    currentAudioFolder, wavename, cfgfile="config.ini")
                speechtext = speech.stt().strip()
                if (len(speechtext) > 0):
                    speechtextEditArea.insert("end-1c", speechtext)
                    speechTextConfig[foldername][filename] = speechtext
                    speechfilepath = os.path.join(
                        currentAudioFolder, foldername + "_speechtext.txt")
                    speechTextConfig.write(open(speechfilepath, "w"))
            if (speechTextConfig.has_option(foldername + "_zh", filename) and
                    len(speechTextConfig[foldername + "_zh"][filename].strip()) > 0):
                speechinfoEditArea.insert(
                    "end-1c", speechTextConfig[foldername + "_zh"][filename])
            elif (len(speechtext) > 0):
                translater = TranslateText.TranslateText(cfgfile="config.ini")
                speechtext = translater.translate(speechtext)
                if (len(speechtext) > 0):
                    speechinfoEditArea.insert("end-1c", speechtext)
                    speechTextConfig[foldername + "_zh"][filename] = speechtext
                    speechfilepath = os.path.join(
                        currentAudioFolder, foldername + "_speechtext.txt")
                    speechTextConfig.write(open(speechfilepath, "w"))
        else:
            utils.displayErrorMessage("Select Target Audio First 3")


def playing_update():
    global playingSeconds
    global playing_timer
    global totalSeconds
    playingSeconds += 1
    update_value = ((100 * playingSeconds) / totalSeconds)
    playingProgressbar["value"] = update_value
    if (playingSeconds == totalSeconds):
        playing_timer.cancel()
    else:
        playing_timer = threading.Timer(1, playing_update)
        playing_timer.start()


def playthread(filepath):
    global repeatPlayCount
    global playingSeconds
    global totalSeconds
    global playing_timer
    loadSpeechText()
    a = AudioFile.audiofile(filepath)
    length = a.length()
    print("audio is around " + str(length) + " seconds")
    repeatPlayCount = int(combo_repeat.get())
    for x in range(repeatPlayCount):
        playingProgressbar["value"] = 0
        playingSeconds = 0
        totalSeconds = int(a.length())
        playing_timer = threading.Timer(1, playing_update)
        playing_timer.start()
        a.play()
        playingProgressbar["value"] = 0
        time.sleep(int((length * 0.1)))
    if (autoPlayNext.get() == 1):
        selectedTuple = targetAudioListBox.curselection()
        if (len(selectedTuple) > 0):
            selected = selectedTuple[0]
            print("selected index " + str(selected))
            targetAudioListBox.selection_clear(selected)
            targetAudioListBox.select_set(selected + 1)
            targetAudioListBox.see(selected+1)
            button_playtarget.invoke()


def playTargetAudio(event=None):
    global currentAudioFolder
    print("playTargetAudio")
    if initialChecks():
        filename = getTargetAudioFileName()
        if filename != '':
            print("playing folder " + currentAudioFolder)
            print("playing file " + filename)
            filepath = os.path.join(currentAudioFolder, filename)
            playing = threading.Thread(target=playthread, args=(filepath,))
            playing.start()
        else:
            utils.displayErrorMessage("Select Target Audio First 4")


def loadTargetAudio(event=None):
    global currentAudioFolder
    global speechTextConfig
    if initialChecks():
        filename = getOriginAudioFileName()
        if filename != '':
            pathparts = filename.rsplit(".", 1)
            foldername = pathparts[0]
            fileformat = "." + pathparts[1]
            print("loading " + filename)
            print("foldername " + foldername)
            filepath = os.path.join(originAudioFolder, foldername)
            currentAudioFolder = filepath
            print("currentAudioFolder " + currentAudioFolder)
            speechfilepath = os.path.join(
                currentAudioFolder, foldername + "_speechtext.txt")
            speechTextConfig = configparser.ConfigParser()
            if (os.path.exists(speechfilepath)):
                speechTextConfig.read(speechfilepath)
            else:
                # speechTextConfig.add_section("DEFAULT")
                speechTextConfig.add_section(foldername)
                speechTextConfig.add_section(foldername + "_zh")
                speechTextConfig["DEFAULT"]["format"] = fileformat
                speechTextConfig.write(open(speechfilepath, "w"))

            loading = threading.Thread(
                target=loadTargetAudioList, args=(filepath,))
            loading.start()
        else:
            utils.displayErrorMessage("Select Origin Audio First")

# -- Recorded Audio Events --


def playRecordedAudio(event=None):
    if initialChecks():
        filename = getRecordedAudioFileName()
        if filename != '':
            if os.path.exists(os.path.join(recordedAudioFolder, filename)):
                print("playing " + os.path.join(recordedAudioFolder, filename))
                a = AudioFile.audiofile(os.path.join(
                    recordedAudioFolder, filename))
                a.play()
            else:
                utils.displayErrorMessage("You must record audio first")
        else:
            utils.displayErrorMessage("You must record audio first")


def playBothAudio(event=None):
    if initialChecks():
        playTargetAudio()
        playRecordedAudio()


def startRecording(event=None):
    global running
    if initialChecks():
        filename = getRecordedAudioFileName()
        if filename != '':
            running = rec.open(os.path.join(
                recordedAudioFolder, filename), 'wb')
            running.start_recording()
        else:
            utils.displayErrorMessage("Select Target Audio First 5")


def stopRecording(event=None):
    global running

    if running is not None:
        running.stop_recording()
        running.close()
        running = None
    else:
        utils.displayErrorMessage('Recording Not Running')


def startStopRecording(event=None):
    global running
    if running is not None:
        stopRecording()
    else:
        startRecording()


def displayHotkeysPopup(event=None):
    hotkeyList = """
    Start/Stop recording - Space bar
    Listen to target audio - Enter
    Navigate Target Audio List - Up/Down arrow keys
    Listen to target and recorded audio - Right Ctrl key
    """
    popupWindow = tk.Toplevel(utils.root)
    popupWindow.wm_geometry("750x300")
    popupWindow.title("Hotkey list")
    msg = tk.Message(popupWindow, text=hotkeyList, width=750)
    msg.pack()

    button = tk.Button(popupWindow, text="Ok", command=popupWindow.destroy)
    button.pack(pady=5)
    utils.root.wait_window(popupWindow)


def updateSilenceThreshhold(event=None):
    global silenceThreshold

    def silenceThreshholdClose():
        global silenceThreshold
        try:
            silenceThreshold = int(popupEntry.get())
            print(silenceThreshold)
            popupWindow.destroy()
        except:
            popupErrorMsg.set("Must be a valid number")

    popupWindow = tk.Toplevel(utils.root)
    popupWindow.wm_geometry("1000x250")
    popupWindow.title("Change Silence dBS")
    popupLabel = tk.Label(
        popupWindow, text="Update what 'silence' is defined as when splitting target audio (in dBS)")
    popupLabel.pack(pady=5)
    popupLabel2 = tk.Label(
        popupWindow, text="Current Silence Threshold is: " + str(silenceThreshold) + "dBS")
    popupLabel2.pack(pady=5)

    popupEntry = tk.Entry(popupWindow)
    popupEntry.pack()

    button = tk.Button(popupWindow, text="Update",
                       command=silenceThreshholdClose)
    button.pack(pady=5)

    popupErrorMsg = tk.StringVar()
    popupError = tk.Label(popupWindow, textvariable=popupErrorMsg, fg="red")
    popupError.pack(pady=5)

    utils.root.wait_window(popupWindow)

# --- main ---


# create the target audio and recorded audio folders, if they don't already exist
if not os.path.exists(originAudioFolder):
    os.makedirs(originAudioFolder)
if not os.path.exists(recordedAudioFolder):
    os.makedirs(recordedAudioFolder)

rec = recorder.Recorder(channels=2)
running = None

utils.root = tk.Tk()
width = utils.root .winfo_screenwidth()
height = utils.root .winfo_screenheight()
utils.root.geometry("%dx%d+0+0" % (width, height))
utils.root.state('zoomed')
utils.root.title("Speech Shadowing App")

# Create menu bar
menubar = tk.Menu(utils.root)
filemenu = tk.Menu(menubar, tearoff=0)
filemenu.add_command(label="Upload Origin Audio", command=uploadTargetAudio)
filemenu.add_command(label="Delete Selected Target Audio",
                     command=deleteTargetAudio)
filemenu.add_command(label="Update Silence Threshold",
                     command=updateSilenceThreshhold)
filemenu.add_separator()

filemenu.add_command(label="Exit", command=utils.root.quit)
menubar.add_cascade(label="File", menu=filemenu)

helpmenu = tk.Menu(menubar, tearoff=0)
helpmenu.add_command(label="Help", command=openHelp)
helpmenu.add_command(label="Hotkeys", command=displayHotkeysPopup)
menubar.add_cascade(label="Help", menu=helpmenu)

utils.root.config(menu=menubar)

# Create app left frame
appLeftFrame = tk.Frame(utils.root, bg='light sky blue')
appLeftFrame.grid(row=0, column=0, padx=5, pady=5)

# Create app right frame
appRightFrame = tk.Frame(utils.root, bg='light sky blue')
appRightFrame.grid(row=0, column=1, padx=5, pady=5)

utils.root.columnconfigure(0, weight=3)
utils.root.columnconfigure(1, weight=1)

# Generate top frame
topFrame = tk.Frame(appLeftFrame, bg='light sky blue')
topFrame.grid(row=0, column=0)

# create info message area
utils.infoMessage = tk.StringVar(topFrame)
ft = tkFont.Font(size=15, weight=tkFont.BOLD)
infomsg = tk.Label(topFrame, textvariable=utils.infoMessage,
                   fg="blue", font=ft, bg='light sky blue')
infomsg.pack()

# create error message area
utils.errorMessage = tk.StringVar(topFrame)
ft = tkFont.Font(size=15, weight=tkFont.BOLD)
error = tk.Label(topFrame, textvariable=utils.errorMessage,
                 fg="red", font=ft, bg='light sky blue')
error.pack()

# create speechtext text area
speechtextFrame = tk.Frame(topFrame, bg='light sky blue')
speechtextScrollbarY = tk.Scrollbar(speechtextFrame)
ft = tkFont.Font(size=15, weight=tkFont.BOLD)
speechtextEditArea = tk.Text(speechtextFrame, height=7, wrap="word",
                             yscrollcommand=speechtextScrollbarY.set,
                             borderwidth=0, highlightthickness=0,
                             maxundo=5, font=ft, width=50,
                             bg="#F4F5FF", fg='magenta2')
speechtextScrollbarY.config(command=speechtextEditArea.yview)
speechtextScrollbarY.pack(side="right", fill="y")
speechtextEditArea.pack(side="left", fill="both", expand=True)
speechtextFrame.pack()

playingProgressbar = ttk.Progressbar(topFrame, orient=tk.HORIZONTAL,
                                     length=300, mode='determinate')
playingProgressbar["value"] = 0
playingProgressbar.pack()

# Generate middle frame
midFrame = tk.Frame(appLeftFrame, bg='light sky blue')
midFrame.grid(row=1, column=0)

# generate list of original audio
originAudioFrame = tk.Frame(midFrame, bg='light sky blue')
originAudioFrame.grid(row=0, column=0)

label = tk.Label(originAudioFrame, text="Origin Audio List",
                 bg='light sky blue')
label.pack()

originAudioListBoxFrame = tk.Frame(originAudioFrame, bg='light sky blue')
originAudioListBoxFrame.pack()

originAudioListBox = tk.Listbox(
    originAudioListBoxFrame, selectmode="SINGLE", width=25, exportselection=False, bg="#F4F5FF", fg='HotPink1')

originScrollbar = tk.Scrollbar(originAudioListBoxFrame)
originScrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=2)
originScrollbar.config(command=originAudioListBox.yview)

originAudioListBox.config(yscrollcommand=originScrollbar.set)
originAudioListBox.bind('<Double-1>', loadTargetAudio)
originAudioListBox.pack(pady=2)

# generate list of splited audio
targetAudioFrame = tk.Frame(midFrame, bg='light sky blue')
targetAudioFrame.grid(row=0, column=1, padx=2, pady=2)

# create target audio list
label = tk.Label(targetAudioFrame, text="Target Audio List",
                 bg='light sky blue')
label.pack()

targetAudioListBoxFrame = tk.Frame(targetAudioFrame, bg='light sky blue')
targetAudioListBoxFrame.pack(padx=5)

targetAudioListBox = tk.Listbox(
    targetAudioListBoxFrame, selectmode="SINGLE", width=60, exportselection=False, bg="#F4F5FF", fg='HotPink1')

# create target audio list scroll bar
scrollbar = tk.Scrollbar(targetAudioListBoxFrame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=2)
scrollbar.config(command=targetAudioListBox.yview)

targetAudioListBox.config(yscrollcommand=scrollbar.set)
targetAudioListBox.bind('<Double-1>', playTargetAudio)
targetAudioListBox.pack(pady=2)

midFrame.columnconfigure(0, weight=1, minsize=40)
midFrame.columnconfigure(1, weight=1, minsize=100)

# Generate low frame
lowFrame = tk.Frame(appLeftFrame, bg='light sky blue')
lowFrame.grid(row=2, column=0)

# create low left frame
lowLeftFrame = tk.Frame(lowFrame, bg='light sky blue')
lowLeftFrame.grid(row=0, column=0, padx=5, pady=2)

# create low middle frame
lowMiddleFrame = tk.Frame(lowFrame, bg='light sky blue')
lowMiddleFrame.grid(row=0, column=1, padx=5, pady=2)

# create low right frame
lowRightFrame = tk.Frame(lowFrame, bg='light sky blue')
lowRightFrame.grid(row=0, column=2, padx=5, pady=2)

lowFrame.columnconfigure(0, weight=1)
lowFrame.columnconfigure(1, weight=1)
lowFrame.columnconfigure(2, weight=1)

# create buttons for left frame
button_load_splited = tk.Button(
    lowLeftFrame, text='Load Splited Audio for Origin Audio', command=loadTargetAudio, width=35)
button_load_splited.pack(pady=2)

button_separate_vocal = tk.Button(
    lowLeftFrame, text='Split Origin Audio (no Vocal Separation)', command=splitOriginAudio, width=35)
button_separate_vocal.pack(pady=2)

button_separate_vocal = tk.Button(
    lowLeftFrame, text='Split Origin Audio (with Vocal Separation)', command=separateAudioVocals, width=35)
button_separate_vocal.pack(pady=2)

lowLeftSilenceLengthCombonFrame = tk.Frame(lowLeftFrame, bg='light sky blue')
lowLeftSilenceLengthCombonFrame.pack()

label = tk.Label(lowLeftSilenceLengthCombonFrame, text="Min Slience Length (ms)",
                 bg='light sky blue')
label.grid(row=0, column=0)
combo_min_silence_length = ttk.Combobox(
    lowLeftSilenceLengthCombonFrame, width=5)
combo_min_silence_length['values'] = (
    200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000)
combo_min_silence_length.current(4)
combo_min_silence_length.grid(row=0, column=1)

lowLeftSilenceThresholdCombonFrame = tk.Frame(
    lowLeftFrame, bg='light sky blue')
lowLeftSilenceThresholdCombonFrame.pack()

label = tk.Label(lowLeftSilenceThresholdCombonFrame, text="Min Slience Threshold (dBFS)",
                 bg='light sky blue')
label.grid(row=0, column=0)
combo_min_silence_threshold = ttk.Combobox(
    lowLeftSilenceThresholdCombonFrame, width=5)
combo_min_silence_threshold['values'] = (-36, -26, -16)
combo_min_silence_threshold.current(0)
combo_min_silence_threshold.grid(row=0, column=1)

# create buttons for right frame

button_playtarget = tk.Button(
    lowMiddleFrame, text='Play Target Audio (Left Alt Key)', command=playTargetAudio, width=25)
button_playtarget.pack(pady=2)

button_rec = tk.Button(
    lowMiddleFrame, text='Toggle Recording (Right Shift Key)', command=startStopRecording, width=25)
button_rec.pack(pady=2)

button_playboth = tk.Button(
    lowMiddleFrame, text='Play Both Audio (Right Ctrl Key)', command=playBothAudio, width=25)
button_playboth.pack(pady=2)

button_convert_speechtext = tk.Button(
    lowRightFrame, text='Convert Speech to Text', command=convertSpeechText, width=20)
button_convert_speechtext.pack(pady=2)

button_save_speechtext = tk.Button(
    lowRightFrame, text='Save Speech to Text', command=saveSpeechText, width=20)
button_save_speechtext.pack(pady=2)

button_info_speechtext = tk.Button(
    lowRightFrame, text='Speech Text Meanings', command=infoSpeechText, width=20)
button_info_speechtext.pack(pady=2)

lowRightRepeatCombonFrame = tk.Frame(lowRightFrame, bg='light sky blue')
lowRightRepeatCombonFrame.pack()

label = tk.Label(lowRightRepeatCombonFrame, text="Repeat Times",
                 bg='light sky blue')
label.grid(row=0, column=0)
combo_repeat = ttk.Combobox(lowRightRepeatCombonFrame, width=5)
combo_repeat['values'] = (1, 2, 3, 4, 5)
combo_repeat.current(0)
combo_repeat.grid(row=0, column=1)

autoPlayNext = tk.IntVar()
checkbox_autoplay = tk.Checkbutton(
    lowRightFrame, text="Auto Play", variable=autoPlayNext).pack(pady=2)

autoSTTNext = tk.IntVar()
checkbox_autoplay = tk.Checkbutton(
    lowRightFrame, text="Auto STT", variable=autoSTTNext).pack(pady=2)

# Create app right frame

# generate speech info frame

speechinfoFrame = tk.Frame(appRightFrame, bg='light sky blue')
speechinfoFrame.grid(row=0, column=0, padx=5, pady=2)

label = tk.Label(speechinfoFrame, text="Speech Text Meanings",
                 bg="#F4F5FF", fg='Blue2')
label.pack()

# create speech text info area
speechinfoScrollbarY = tk.Scrollbar(speechinfoFrame)
ft = tkFont.Font(family="Courier New")
speechinfoEditArea = tk.Text(speechinfoFrame, height=27, wrap="word",
                             yscrollcommand=speechinfoScrollbarY.set,
                             borderwidth=0, highlightthickness=0, font=ft, width=50, bg="#F4F5FF", fg='HotPink1')
speechinfoScrollbarY.config(command=speechinfoEditArea.yview)
speechinfoScrollbarY.pack(side="right", fill="y")
speechinfoEditArea.pack(side="left", fill="both", expand=True)

# Create keybindings
utils.root.bind("<Alt_R>", playTargetAudio)
utils.root.bind("<Control_R>", playBothAudio)


def targetAudioSelectionDown(event=None):
    selectedTuple = targetAudioListBox.curselection()
    if (len(selectedTuple) > 0):
        i = selectedTuple[0]
        if (i < targetAudioListBox.size()):
            targetAudioListBox.selection_clear(i)
            targetAudioListBox.select_set(i+1)
            targetAudioListBox.see(i+1)
    else:
        targetAudioListBox.select_set(0)
        targetAudioListBox.see(0)
    loadSpeechText()


def targetAudioSelectionUp(event=None):
    selectedTuple = targetAudioListBox.curselection()
    if (len(selectedTuple) > 0):
        i = selectedTuple[0]
        if (i > 0):
            targetAudioListBox.selection_clear(i)
            targetAudioListBox.select_set(i-1)
            targetAudioListBox.see(i-1)

    else:
        targetAudioListBox.select_set(0)
        targetAudioListBox.see(0)
    loadSpeechText()


utils.root.bind("<Down>", targetAudioSelectionDown)
utils.root.bind("<Right>", targetAudioSelectionDown)
utils.root.bind("<Up>", targetAudioSelectionUp)
utils.root.bind("<Left>", targetAudioSelectionUp)
utils.root.bind("<Shift_R>", startStopRecording)
targetAudioListBox.bind("<<ListboxSelect>>", loadSpeechText)

if __name__ == '__main__':
    # -- load target audio initially. Set info message also has a bonus that it'll start
    # the GUI before the targetAudio list has completed
    utils.displayInfoMessage("Loading Origin Audio...")
    refreshOriginAudioList()
    utils.displayInfoMessage("")
    utils.root.mainloop()
