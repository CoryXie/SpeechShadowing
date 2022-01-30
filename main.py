import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
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
import webbrowser
import markdown
import utils
import SpeechToText

# --- global values ---
global originAudioFolder
global currentAudioFolder
global recordedAudioFolder
global silenceThreshold
global repeatPlayCount

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
        filename = "recordedAudio-" + targetFilename[0:len(targetFilename)-4] + ".wav"
        return filename
    else:
        print("targetfilename doesn't exist")
        return ''

def loadTargetAudioList(folder):
    # remove all elements in targetAudioListbox
    targetAudioListBox.delete(0, targetAudioListBox.size())
    #loop thru files
    fileList = os.listdir(folder)
    fileList.sort()
    for file in fileList:
        if file[len(file) - 4:] in [".wav", ".mp3"]:
            displayname = file
            audioFile = AudioFile.audiofile(os.path.join(folder, file))
            length = audioFile.length()
            displaylength = ""
            if length > 60:
                displaylength = str(math.floor(length/60)) + ":" + str(math.floor(length % 60)).zfill(2)
            else:
                displaylength = str(math.floor(length % 60)) + " seconds"
            displayname += " - " + displaylength
            targetAudioListBox.insert("end", displayname )
            print(displayname)
            targetAudioListBox.see(targetAudioListBox.size())
            utils.root.update()


def loadOriginAudioList():
    # remove all elements in originAudioListBox
    originAudioListBox.delete(0, originAudioListBox.size())
    #loop thru files
    fileList = os.listdir(originAudioFolder)
    fileList.sort()
    for file in fileList:
        if file[len(file) - 4:] in [".wav", ".mp3"]:
            displayname = file
            audioFile = AudioFile.audiofile(os.path.join(originAudioFolder, file))
            length = audioFile.length()
            displaylength = ""
            if length > 60:
                displaylength = str(math.floor(length/60)) + ":" + str(math.floor(length % 60)).zfill(2)
            else:
                displaylength = str(math.floor(length % 60)) + " seconds"
            displayname += " - " + displaylength
            originAudioListBox.insert("end", displayname )
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
        loading = threading.Thread(target=loadTargetAudioList, args=(currentAudioFolder,))
        loading.start()

def initialChecks():
    global running
    #general things to do before running events
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
            markdown.markdownFromFile(input="./README.MD",output="./README.html")
        else:
            utils.displayErrorMessage("Cannot find help page")
            return
    webbrowser.open('./README.html')

# -- Target Audio Events --
def uploadTargetAudio(event=None):
    if initialChecks():
        filenames = filedialog.askopenfilenames(title="Select Target Audio", filetypes=[("Audio Files", ".mp3 .wav")])
        for filename in filenames:
            shutil.copy(filename, originAudioFolder)
        if (len(filenames) > 0):
            refreshOriginAudioList()

def splitAudio(filename):
    print(filename)
    separator = Separator('spleeter:2stems')
    separator.separate_to_file(filename, originAudioFolder)

def separateAudioVocals(event=None):
    if initialChecks():
        filenames = filedialog.askopenfilenames(title="Select Target Audio", filetypes=[("Audio Files", ".mp3 .wav")])
        for filename in filenames:
            # Using embedded configuration.
            splitting = threading.Thread(target=splitAudio, args=(filename,))
            splitting.start()

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
    if initialChecks():
        filename = getOriginAudioFileName()
        if filename != '':
            audiosplit = audioSplitter.AudioSplitter(originAudioFolder, filename, silencethresh=silenceThreshold)
            audiosplit.split()
            refreshOriginAudioList()
        else:
            utils.displayErrorMessage('Select Target Audio To Split')

def translatetargetaudio(event=None):
    global currentAudioFolder
    if initialChecks():
        filename = getTargetAudioFileName()
        if filename != '':
            speech = SpeechToText.SpeechToText(currentAudioFolder, filename, "config.ini")
            utils.displayInfoMessage(speech.stt())
        else:
            utils.displayErrorMessage("Select Target Audio First")

def playthread(filepath):
    global repeatPlayCount
    a = AudioFile.audiofile(filepath)
    length = a.length()
    print("audio is around " + str(length) + " seconds")
    repeatPlayCount = int(combo_repeat.get())
    for x in range(repeatPlayCount):
        a.play()
        time.sleep(int((length * 0.8)))

def playtargetaudio(event=None):
    global currentAudioFolder
    if initialChecks():
        filename = getTargetAudioFileName()
        if filename != '':
            print("playing folder " + currentAudioFolder)
            print("playing file " + filename)
            filepath = os.path.join(currentAudioFolder, filename)
            playing = threading.Thread(target=playthread, args=(filepath,))
            playing.start()
        else:
            utils.displayErrorMessage("Select Target Audio First")

def loadtargetaudio(event=None):
    global currentAudioFolder
    if initialChecks():
        filename = getOriginAudioFileName()
        if filename != '':
            foldername = filename.rsplit(".", 1)[0];
            print("loading " + filename)
            print("foldername " + foldername)
            filepath = os.path.join(originAudioFolder, foldername)
            currentAudioFolder = filepath
            print("currentAudioFolder " + currentAudioFolder)
            loading = threading.Thread(target=loadTargetAudioList, args=(filepath,))
            loading.start()
        else:
            utils.displayErrorMessage("Select Origin Audio First")

# -- Recorded Audio Events --
def playrecordedaudio(event=None):
    if initialChecks():
        filename = getRecordedAudioFileName()
        if filename != '':
            if os.path.exists(os.path.join(recordedAudioFolder, filename)):
                print("playing " + os.path.join(recordedAudioFolder, filename))
                a = AudioFile.audiofile(os.path.join(recordedAudioFolder, filename))
                a.play()
            else:
                utils.displayErrorMessage("You must record audio first")
        else:
            utils.displayErrorMessage("You must record audio first")

def playbothaudio(event=None):
   if initialChecks():
        playtargetaudio()
        playrecordedaudio()


def startRecording(event=None):
    global running
    if initialChecks():
        filename = getRecordedAudioFileName()
        if filename != '':
            running = rec.open(os.path.join(recordedAudioFolder,filename), 'wb')
            running.start_recording()
        else:
            utils.displayErrorMessage("Select Target Audio First")

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
    hotkeyList="""
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
    popupLabel = tk.Label(popupWindow, text="Update what 'silence' is defined as when splitting target audio (in dBS)")
    popupLabel.pack(pady=5)
    popupLabel2 = tk.Label(popupWindow, text="Current Silence Threshold is: " + str(silenceThreshold) + "dBS")
    popupLabel2.pack(pady=5)

    popupEntry = tk.Entry(popupWindow)
    popupEntry.pack()

    button = tk.Button(popupWindow, text="Update", command=silenceThreshholdClose)
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
utils.root.title("Speech Shadowing App")

# -- create menu bar --
menubar = tk.Menu(utils.root)
filemenu = tk.Menu(menubar, tearoff=0)
filemenu.add_command(label="Upload Origin Audio", command=uploadTargetAudio)
filemenu.add_command(label="Separate Vocals from Origin Audio", command=separateAudioVocals)
filemenu.add_command(label="Split Origin Audio on Silences", command=splitOriginAudio)
filemenu.add_command(label="Delete Selected Target Audio", command=deleteTargetAudio)
filemenu.add_command(label="Update Silence Threshold", command=updateSilenceThreshhold)
filemenu.add_separator()

filemenu.add_command(label="Exit", command=utils.root.quit)
menubar.add_cascade(label="File", menu=filemenu)

helpmenu = tk.Menu(menubar, tearoff=0)
helpmenu.add_command(label="Help", command=openHelp)
helpmenu.add_command(label="Hotkeys", command=displayHotkeysPopup)
menubar.add_cascade(label="Help", menu=helpmenu)

utils.root.config(menu=menubar)

topFrame = tk.Frame(utils.root)
topFrame.grid(row=0, column=0, padx=10, pady=5)

# -- create info message area
utils.infoMessage = tk.StringVar(topFrame)
ft = tkFont.Font(size=30, weight=tkFont.BOLD)
infomsg = tk.Label(topFrame, textvariable=utils.infoMessage, fg="blue", font=ft)
infomsg.pack()

# -- create error message area
utils.errorMessage = tk.StringVar(utils.root)
error = tk.Label(topFrame, textvariable=utils.errorMessage, fg="red")
error.pack()

midFrame = tk.Frame(utils.root)
midFrame.grid(row=1, column=0, padx=10, pady=5)

# -- generate list of original audio
originAudioFrame = tk.Frame(midFrame)
originAudioFrame.grid(row=0, column=0, padx=10, pady=5)

label = tk.Label(originAudioFrame, text="Origin Audio List")
label.pack()

originAudioListBoxFrame = tk.Frame(originAudioFrame)
originAudioListBoxFrame.pack(padx=10)

originAudioListBox = tk.Listbox(originAudioListBoxFrame, selectmode="SINGLE", width=75)

originScrollbar = tk.Scrollbar(originAudioListBoxFrame)
originScrollbar.pack(side=tk.RIGHT, fill=tk.Y,pady=5)
originAudioListBox.config(yscrollcommand=originScrollbar.set)
originScrollbar.config(command=originAudioListBox.yview)

originAudioListBox.pack(pady=5)

# -- generate list of splited audio
targetAudioFrame = tk.Frame(midFrame)
targetAudioFrame.grid(row=0, column=1, padx=10, pady=5)

label = tk.Label(targetAudioFrame, text="Target Audio List")
label.pack()

targetAudioListBoxFrame = tk.Frame(targetAudioFrame)
targetAudioListBoxFrame.pack(padx=10)

targetAudioListBox = tk.Listbox(targetAudioListBoxFrame, selectmode="SINGLE", width=75)


scrollbar = tk.Scrollbar(targetAudioListBoxFrame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y,pady=5)
targetAudioListBox.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=targetAudioListBox.yview)

targetAudioListBox.pack(pady=5)

lowFrame = tk.Frame(utils.root)
lowFrame.grid(row=2, column=0, padx=10, pady=5)

lowLeftFrame = tk.Frame(lowFrame)
lowLeftFrame.grid(row=0, column=0, padx=10, pady=5)

lowRightFrame = tk.Frame(lowFrame)
lowRightFrame.grid(row=0, column=1, padx=10, pady=5)

# --  create buttons for left frame
button_playtarget = tk.Button(lowLeftFrame, text='Load Splited Audio for Selected Origin Audio', command=loadtargetaudio)
button_playtarget.pack(pady=5)

button_playboth = tk.Button(lowLeftFrame, text='Separate Vocals from Selected Origin Audio', command=separateAudioVocals)
button_playboth.pack(pady=5)

# --  create buttons for right frame

button_playtarget = tk.Button(lowRightFrame, text='Play Target Audio (Enter Key)', command=playtargetaudio)
button_playtarget.pack(pady=5)

button_rec = tk.Button(lowRightFrame, text='Start/Stop Recording (Space bar)', command=startStopRecording)
button_rec.pack(pady=5)

button_playboth = tk.Button(lowRightFrame, text='Play Both Audio (Right Ctrl Key)', command=playbothaudio)
button_playboth.pack(pady=5)

button_playboth = tk.Button(lowRightFrame, text='Translate Target Audio', command=translatetargetaudio)
button_playboth.pack(pady=5)

combo_repeat = ttk.Combobox(lowRightFrame)
combo_repeat['values']= (1, 2, 3, 4, 5)
combo_repeat.current(0)
combo_repeat.pack(pady=5)


# -- create keybindings
utils.root.bind("<Return>", playtargetaudio)
utils.root.bind("<Control_R>", playbothaudio)

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

utils.root.bind("<Down>", targetAudioSelectionDown)
utils.root.bind("<Right>", targetAudioSelectionDown)
utils.root.bind("<Up>", targetAudioSelectionUp)
utils.root.bind("<Left>", targetAudioSelectionUp)
utils.root.bind("<space>", startStopRecording)


if __name__=='__main__':
    # -- load target audio initially. Set info message also has a bonus that it'll start
    # the GUI before the targetAudio list has completed
    utils.displayInfoMessage("Loading Origin Audio...")
    refreshOriginAudioList()
    utils.displayInfoMessage("")
    utils.root.mainloop() 
