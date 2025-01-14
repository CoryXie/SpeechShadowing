import datetime
from fnmatch import translate
from glob import glob
import io
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
from turtle import width
import tkinter.font as tkFont
from RoomableCanvas import CanvasImage
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
import pytesseract
import utils
import srt
from PIL import ImageGrab, ImageTk, Image
from manga_ocr import MangaOcr
from datetime import date
import pyttsx3
import pdfplumber
import SpeechToText
import TranslateText
import ichiran

# --- global values ---
global appDataFolderPath
global currentSessionFolderPath
global recordedAudioFolderPath
global silenceThreshold
global repeatPlayCount
global autoPlayNext
global autoSTTNext
global splitWithVocals
global ttsEngine
global mangaOCR
global mangaImage
global currentSessionFolderName
global currentPdfFile
global speechTextConfig
global dailyWordsConfig

appDataFolderPath = "./TargetAudio"
recordedAudioFolderPath = "./RecordedAudio"
currentSessionFolderPath = ""
currentSessionFolderName = ""
silenceThreshold = -36
repeatPlayCount = 1
mangaOCR = None
mangaImage = None
currentPdfFile = None

# --- functions ---

# -- helper functions


def getCurrentSessionFileName():
    selectedTuple = currentSessionListBox.curselection()
    if (len(selectedTuple) > 0):
        filename = currentSessionListBox.get(selectedTuple[0])
        filename = filename[0:filename.rfind(" - ")]
        return filename
    else:
        print("selectedTuple is not greater than 0")
        return ''


def getAppDataFileName():
    selectedTuple = appDataFileListBox.curselection()
    if (len(selectedTuple) > 0):
        filename = appDataFileListBox.get(selectedTuple[0])
        filename = filename[0:filename.rfind(" - ")]
        return filename
    else:
        print("selectedTuple is not greater than 0")
        return ''


def getRecordedAudioFileName():
    global currentSessionFolderName
    return currentSessionFolderName + "-recorded.wav"


def loadCurrentSessionAudioListThread(folder, lastindex=0):
    global mangaImage
    # remove all elements in currentSessionListBox
    currentSessionListBox.delete(0, currentSessionListBox.size())
    # loop thru files
    fileList = os.listdir(folder)
    fileList.sort()
    fileformat = speechTextConfig["DEFAULT"]["format"]
    if (mangaImage != None):
        mangaImage.destroy()
        mangaImage = None
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
            currentSessionListBox.insert("end", displayname)

        currentSessionListBox.select_set(lastindex)
        currentSessionListBox.see(lastindex)


def loadAppDataFileList():
    # remove all elements in appDataFileListBox
    appDataFileListBox.delete(0, appDataFileListBox.size())
    # loop thru files
    fileList = os.listdir(appDataFolderPath)
    fileList.sort()
    for file in fileList:
        if file[len(file) - 4:] in [".wav", ".mp3", ".mp4"]:
            displayname = file
            audioFile = AudioFile.audiofile(
                os.path.join(appDataFolderPath, file))
            length = audioFile.length()
            displaylength = ""
            if length > 60:
                displaylength = str(math.floor(length/60)) + \
                    ":" + str(math.floor(length % 60)).zfill(2)
            else:
                displaylength = str(math.floor(length % 60)) + " seconds"
            displayname += " - " + displaylength
            appDataFileListBox.insert("end", displayname)
            appDataFileListBox.see(appDataFileListBox.size())
            # utils.root.update()
        elif file[len(file) - 4:] in [".pdf"]:
            filepath = os.path.join(appDataFolderPath, file)
            displayname = file
            pdf = pdfplumber.open(filepath)
            numpages = len(pdf.pages)
            displayname += " - " + str(numpages) + " pages"
            appDataFileListBox.insert("end", displayname)
            appDataFileListBox.see(appDataFileListBox.size())


def refreshAppDataFileList():
    global activeAudioRecorder
    if activeAudioRecorder is not None:
        utils.displayErrorMessage('recording audio, gotta stop that first')
    else:
        loading = threading.Thread(target=loadAppDataFileList)
        loading.start()


def refreshCurrentSessionFileList():
    global activeAudioRecorder
    global currentSessionFolderPath
    if activeAudioRecorder is not None:
        utils.displayErrorMessage('recording audio, gotta stop that first')
    else:
        loading = threading.Thread(
            target=loadCurrentSessionAudioListThread, args=(currentSessionFolderPath,))
        loading.start()


def splitAppAudioFileListThread(filename):
    global activeAudioRecorder
    global currentSessionFolderPath
    global speechTextConfig
    if activeAudioRecorder is not None:
        utils.displayErrorMessage('recording audio, gotta stop that first')
    else:
        silenceThreshold = int(combo_min_silence_threshold.get())
        silenceLength = int(combo_min_silence_length.get())
        vocalLength = int(combo_min_vocal_length.get())
        pathparts = filename.rsplit(".", 1)
        foldername = pathparts[0]
        # Open new session
        speechfilepath = os.path.join(
            currentSessionFolderPath, foldername + "_speechtext.txt")

        speechTextConfig.add_section(foldername)
        speechTextConfig.add_section(foldername + "_zh")
        speechTextConfig.add_section(foldername + "_ranges")
        speechTextConfig["DEFAULT"]["format"] = ".mp3"
        speechTextConfig["DEFAULT"]["lastindex"] = str(0)

        audiosplit = audioSplitter.AudioSplitter(
            appDataFolderPath, filename, currentSessionFolderPath, speechTextConfig,
            minsilencelen=silenceLength,
            silencethresh=silenceThreshold,
            minchunklen=vocalLength)
        audiosplit.split()
        speechTextConfig.write(open(speechfilepath, "w"))
        loadAppDataFileHandler()


def noRecorderRunning():
    global activeAudioRecorder
    # general things to do before activeAudioRecorder events
    if activeAudioRecorder is not None:
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


def uploadAppDataFileHandler(event=None):
    filenames = filedialog.askopenfilenames(
        title="Select App Data File", filetypes=[("Audio & Manga Files", ".mp4 .mp3 .wav .pdf")])
    for filename in filenames:
        shutil.copy(filename, appDataFolderPath)
    if (len(filenames) > 0):
        refreshAppDataFileList()


def separateAudioDataFile(filename):
    global currentSessionFolderPath
    global silenceThreshold
    global speechTextConfig
    print("Separating " + filename)
    pathparts = filename.rsplit(".", 1)
    foldername = pathparts[0]
    silenceThreshold = int(combo_min_silence_threshold.get())
    silenceLength = int(combo_min_silence_length.get())
    vocalLength = int(combo_min_vocal_length.get())
    # Open new session
    speechfilepath = os.path.join(
        currentSessionFolderPath, foldername + "_speechtext.txt")

    speechTextConfig.add_section(foldername)
    speechTextConfig.add_section(foldername + "_zh")
    speechTextConfig.add_section(foldername + "_ranges")
    speechTextConfig["DEFAULT"]["format"] = ".mp3"
    speechTextConfig["DEFAULT"]["lastindex"] = str(0)

    audiosplit = audioSplitter.AudioSplitter(
        appDataFolderPath, filename, currentSessionFolderPath, speechTextConfig,
        minsilencelen=silenceLength,
        silencethresh=silenceThreshold,
        minchunklen=vocalLength)
    audiosplit.splitVocals()
    speechTextConfig.write(open(speechfilepath, "w"))
    loadAppDataFileHandler()


def separateAudioFileVocalsHandler(event=None):
    global silenceThreshold
    global currentSessionFolderPath
    global currentSessionFolderName
    filename = getAppDataFileName()
    if filename != '':
        pathparts = filename.rsplit(".", 1)
        foldername = pathparts[0]
        folderpath = os.path.join(appDataFolderPath, foldername)
        currentSessionFolderPath = folderpath
        currentSessionFolderName = foldername
        if not os.path.exists(currentSessionFolderPath):
            os.makedirs(currentSessionFolderPath)
        separating = threading.Thread(
            target=separateAudioDataFile, args=(filename,))
        separating.start()
    else:
        utils.displayErrorMessage('Select Origin Audio To Split')


def deleteAppDataFileHandler(event=None):
    # remove all elements in currentSessionListBox
    filename = getAppDataFileName()
    os.remove(os.path.join(appDataFolderPath, filename))
    refreshAppDataFileList()


def deleteCurrentSessionDataFileHandler(event=None):
    global currentSessionFolderPath
    # remove all elements in currentSessionListBox
    filename = getCurrentSessionFileName()
    if (filename != ""):
        os.remove(os.path.join(currentSessionFolderPath, filename))
        refreshCurrentSessionFileList()
    else:
        utils.displayErrorMessage("Please select file to delete")


def splitAppAudioDataHandler(event=None):
    global silenceThreshold
    global currentSessionFolderPath
    global currentSessionFolderName
    if (splitWithVocals.get() == 1):
        separateAudioFileVocalsHandler(event)
    else:
        filename = getAppDataFileName()
        if (filename != ""):
            pathparts = filename.rsplit(".", 1)
            foldername = pathparts[0]
            folderpath = os.path.join(appDataFolderPath, foldername)
            currentSessionFolderPath = folderpath
            currentSessionFolderName = foldername
            if not os.path.exists(currentSessionFolderPath):
                os.makedirs(currentSessionFolderPath)
            splitting = threading.Thread(
                target=splitAppAudioFileListThread, args=(filename,))
            splitting.start()
        else:
            utils.displayErrorMessage('Select Target Audio To Split')


def convertSpeechTextHandler(event=None):
    global currentSessionFolderPath
    filename = getCurrentSessionFileName()
    if (filename != ""):
        foldername = os.path.basename(
            os.path.normpath(currentSessionFolderPath))
        wavename = filename.rsplit(".", 1)[0] + ".wav"
        if (speechTextConfig.has_option(foldername, filename) and
                len(speechTextConfig[foldername][filename].strip()) > 0):
            speechtext = speechTextConfig[foldername][filename].strip()
        else:
            speech = SpeechToText.SpeechToText(
                currentSessionFolderPath, wavename, "config.ini")
            speechtext = speech.stt()
        speechtextEditArea.delete("1.0", tk.END)
        speechtextEditArea.insert("end-1c", speechtext)

        if (len(speechtext)):
            item = currentSessionListBox.curselection()[0]
            currentSessionListBox.delete(item)
            displayname = filename
            audioFile = AudioFile.audiofile(
                os.path.join(currentSessionFolderPath, filename))
            length = audioFile.length()
            displaylength = ""
            if length > 60:
                displaylength = str(math.floor(length/60)) + \
                    ":" + str(math.floor(length % 60)).zfill(2)
            else:
                displaylength = str(math.floor(length % 60)) + " seconds"
            displayname += " - " + displaylength + " [" + speechtext + "]"
            currentSessionListBox.insert(item, displayname)

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
                    currentSessionFolderPath, foldername + "_speechtext.txt")
                speechTextConfig.write(open(speechfilepath, "w"))
    else:
        utils.displayErrorMessage("Please select audio to convert to text!")


def saveDailyTextMeaningsHandler(event=None):
    global dailyWordsConfig
    # Add a section in the daily words config
    today = date.today().strftime("%b-%d-%Y")
    if (not dailyWordsConfig.has_section(today)):
        dailyWordsConfig.add_section(today)
    num_items = today + "-" + str(len(dailyWordsConfig.options(today)) + 1)
    text_to_save = speechtextEditArea.get(
        '0.0', tk.END).strip() + "\n"
    text_to_save += speechinfoEditArea.get(
        '0.0', tk.END).strip() + "\n"
    dailyWordsConfig[today][num_items] = text_to_save
    dailyWordsConfig.write(open(daily_text_meanings_file_path, "w"))


def saveSRTHandler(event=None):
    global currentSessionFolderPath
    global speechTextConfig

    foldername = os.path.basename(
        os.path.normpath(currentSessionFolderPath))
    print("foldername=" + foldername)
    srtfilepath = os.path.join(
        currentSessionFolderPath, foldername + "_srt.txt")
    section = foldername + "_ranges"
    if speechTextConfig.has_section(section):
        range_items = speechTextConfig.items(section)
    else:
        print("no section=" + section)
        return
    subtitles = []
    index = 1
    for filename, ranges in range_items:
        try:
            ja = speechTextConfig[foldername][filename]
            zh = speechTextConfig[foldername + "_zh"][filename]
            print("filename=" + filename)
            print("ranges=" + ranges)
            content = ja + "\n" + zh
            time_range = ranges.rsplit(",", 1)
            start = datetime.timedelta(milliseconds=int(time_range[0]))
            end = datetime.timedelta(milliseconds=int(time_range[1]))
            subtitles.append(srt.Subtitle(
                index=index, start=start, end=end, content=content))
            index += 1
        except ValueError:
            print("ValueError")
        except IndexError:
            print("IndexError")
        except KeyError:
            print("KeyError")
    srt_text = srt.compose(subtitles)
    with open(srtfilepath, 'w') as f:
        f.write(srt_text)

def saveSpeechTextHandler(event=None):
    global currentSessionFolderPath
    global speechTextConfig
    filename = getCurrentSessionFileName()
    if filename != '':
        foldername = os.path.basename(
            os.path.normpath(currentSessionFolderPath))
        speechfilepath = os.path.join(
            currentSessionFolderPath, foldername + "_speechtext.txt")
        speechTextConfig[foldername][filename] = speechtextEditArea.get(
            '0.0', tk.END).strip()
        speechTextConfig[foldername + "_zh"][filename] = speechinfoEditArea.get(
            '0.0', tk.END).strip()
        speechTextConfig.write(open(speechfilepath, "w"))
    else:
        utils.displayErrorMessage(
            "Please select audio file to save speech text!")


def loadSpeechTextInfoThread():
    speechtext = speechtextEditArea.get('0.0', tk.END).strip()
    translater = TranslateText.TranslateText(cfgfile="config.ini")
    translatedtext = translater.translate(speechtext)
    speechinfo = ichiran.ichiran(speechtext).info()
    speechinfo = speechinfo.replace("NIL ", "").replace(
        "  <1>", "\n<1>").replace("\n *", "\n    *")
    speechinfoEditArea.delete("1.0", tk.END)
    speechinfoEditArea.insert("end-1c", translatedtext + "\n" + speechinfo)


def speechTextInfoHandler(event=None):
    loading = threading.Thread(target=loadSpeechTextInfoThread)
    loading.start()


def loadCurrentSessionFileHandler(event=None):
    global currentSessionFolderPath
    global speechTextConfig
    global currentPdfFile
    global mangaImage
    filename = getCurrentSessionFileName()
    if (filename != ""):
        foldername = os.path.basename(
            os.path.normpath(currentSessionFolderPath))
        wavename = filename.rsplit(".", 1)[0] + ".wav"
        speechtextEditArea.delete("1.0", tk.END)
        speechinfoEditArea.delete("1.0", tk.END)
        speechtext = ""
        fileformat = speechTextConfig["DEFAULT"]["format"]
        if (fileformat == ".mp3" or fileformat == ".mp4" or fileformat == ".wav"):
            if (speechTextConfig.has_option(foldername, filename) and
                    len(speechTextConfig[foldername][filename].strip()) > 0):
                speechtext = speechTextConfig[foldername][filename]
                speechtextEditArea.insert("end-1c", speechtext)
            elif (autoSTTNext.get() == 1):
                speech = SpeechToText.SpeechToText(
                    currentSessionFolderPath, wavename, cfgfile="config.ini")
                speechtext = speech.stt().strip()
                if (len(speechtext) > 0):
                    speechtextEditArea.insert("end-1c", speechtext)
                    speechTextConfig[foldername][filename] = speechtext
                    speechfilepath = os.path.join(
                        currentSessionFolderPath, foldername + "_speechtext.txt")
                    speechTextConfig.write(open(speechfilepath, "w"))

                    if (len(speechtext)):
                        item = currentSessionListBox.curselection()[0]
                        currentSessionListBox.delete(item)
                        displayname = filename
                        audioFile = AudioFile.audiofile(
                            os.path.join(currentSessionFolderPath, filename))
                        length = audioFile.length()
                        displaylength = ""
                        if length > 60:
                            displaylength = str(math.floor(length/60)) + \
                                ":" + str(math.floor(length % 60)).zfill(2)
                        else:
                            displaylength = str(
                                math.floor(length % 60)) + " seconds"
                        displayname += " - " + displaylength + \
                            " [" + speechtext + "]"
                        currentSessionListBox.insert(item, displayname)
                        currentSessionListBox.selection_clear(item)
                        currentSessionListBox.select_set(item)
                        currentSessionListBox.see(item)

            if (speechTextConfig.has_option(foldername + "_zh", filename) and
                    len(speechTextConfig[foldername + "_zh"][filename].strip()) > 0):
                speechinfoEditArea.insert(
                    "end-1c", speechTextConfig[foldername + "_zh"][filename])
            elif (len(speechtext) > 0):
                translater = TranslateText.TranslateText(
                    cfgfile="config.ini")
                speechtext = translater.translate(speechtext)
                if (len(speechtext) > 0):
                    speechinfoEditArea.insert("end-1c", speechtext)
                    speechTextConfig[foldername +
                                     "_zh"][filename] = speechtext
                    speechfilepath = os.path.join(
                        currentSessionFolderPath, foldername + "_speechtext.txt")
                    speechTextConfig.write(open(speechfilepath, "w"))
        elif (fileformat == ".pdf"):
            item = currentSessionListBox.curselection()[0]
            page = currentPdfFile.pages[item]
            imagepath = os.path.join(
                currentSessionFolderPath, "last_viewed_manga.png")
            page.to_image().save(imagepath, format="png")
            if (mangaImage != None):
                mangaImage.destroy()
                mangaImage = None
            mangaImage = CanvasImage(
                mangaImageFrame, imagepath)  # create widget
            mangaImage.grid(row=0, column=0)  # show widget
            speechtext = page.extract_text()
            speechtextEditArea.insert("end-1c", speechtext)
    else:
        utils.displayErrorMessage("Please select file to load!")


def playingUpdateTimerHandler():
    global playingSeconds
    global playing_timer
    global totalSeconds
    playingSeconds += 1
    update_value = ((100 * playingSeconds) / totalSeconds)
    playingProgressbar["value"] = update_value
    if (playingSeconds == totalSeconds):
        playing_timer.cancel()
    else:
        playing_timer = threading.Timer(1, playingUpdateTimerHandler)
        playing_timer.start()


def currentSessionPlayingThread(filepath):
    global repeatPlayCount
    global playingSeconds
    global totalSeconds
    global playing_timer
    loadCurrentSessionFileHandler()
    a = AudioFile.audiofile(filepath)
    length = a.length()
    print("audio is around " + str(length) + " seconds")
    repeatPlayCount = int(combo_repeat.get())
    for x in range(repeatPlayCount):
        playingProgressbar["value"] = 0
        playingSeconds = 0
        totalSeconds = int(a.length())
        playing_timer = threading.Timer(1, playingUpdateTimerHandler)
        playing_timer.start()
        a.play()
        playingProgressbar["value"] = 0
        if (autoPlayNext.get() != 1):
            time.sleep(int((length * 0.1)))
    if (autoPlayNext.get() == 1):
        selectedTuple = currentSessionListBox.curselection()
        if (len(selectedTuple) > 0):
            selected = selectedTuple[0]
            print("selected index " + str(selected))
            currentSessionListBox.selection_clear(selected)
            currentSessionListBox.select_set(selected + 1)
            currentSessionListBox.see(selected+1)
            button_playtarget.invoke()


def playCurrentSessionAudioFileHandler(event=None):
    global currentSessionFolderPath
    print("playCurrentSessionAudioFileHandler")
    filename = getCurrentSessionFileName()
    if (filename != ""):
        print("playing folder " + currentSessionFolderPath)
        print("playing file " + filename)
        filepath = os.path.join(currentSessionFolderPath, filename)
        playing = threading.Thread(
            target=currentSessionPlayingThread, args=(filepath,))
        playing.start()
    else:
        utils.displayErrorMessage("Please select audio file to play!")


def playingTTSAudioThread():
    language = str(combo_tts_language.get())
    ttsname = language.rsplit("-", 1)[0].strip()
    voices = ttsEngine.getProperty('voices')
    for voice in voices:
        if (voice.name.find(ttsname) > 0):
            ttsEngine.setProperty("voice", voice.id)
    ttsrate = int(combo_tts_rate.get())
    ttsEngine.setProperty("rate", ttsrate)
    speechtext = speechtextEditArea.get('0.0', tk.END).strip()
    print("Speaking " + language + " [" + speechtext + "]")
    ttsEngine.say(speechtext)
    ttsEngine.runAndWait()
    ttsEngine.stop()
    print("Speaking done")


def playTTSAudioHandler(event=None):
    print("playTTSAudioHandler")
    playing = threading.Thread(target=playingTTSAudioThread)
    playing.start()


def loadAppDataFileHandler(event=None):
    global currentSessionFolderPath
    global currentSessionFolderName
    global speechTextConfig
    global currentPdfFile
    global mangaImage
    filename = getAppDataFileName()
    if (filename != ""):
        pathparts = filename.rsplit(".", 1)
        foldername = pathparts[0]
        fileformat = "." + pathparts[1]
        print("loading " + filename)

        folderpath = os.path.join(appDataFolderPath, foldername)
        if not os.path.exists(folderpath):
            os.makedirs(folderpath)

        # If we have current opening session, save the last index
        if (currentSessionFolderPath != ""):
            print("currentSessionFolderPath " + currentSessionFolderPath)
            speechfilepath = os.path.join(currentSessionFolderPath,
                                          currentSessionFolderName + "_speechtext.txt")
            lastSelection = currentSessionListBox.curselection()
            if (len(lastSelection) > 0):
                lastindex = lastSelection[0]
                speechTextConfig["DEFAULT"]["lastindex"] = str(lastindex)
                speechTextConfig.write(open(speechfilepath, "w"))

        # Open new session
        speechfilepath = os.path.join(
            folderpath, foldername + "_speechtext.txt")
        if (os.path.exists(speechfilepath)):
            speechTextConfig.read(speechfilepath)
        else:
            speechTextConfig.add_section(foldername)
            speechTextConfig.add_section(foldername + "_zh")
            speechTextConfig["DEFAULT"]["format"] = ".mp3"
            speechTextConfig["DEFAULT"]["lastindex"] = str(0)
            speechTextConfig.write(open(speechfilepath, "w"))

        if (speechTextConfig.has_option("DEFAULT", "lastindex")):
            lastindex = int(speechTextConfig["DEFAULT"]["lastindex"])
        else:
            lastindex = 0

        # Save current active folder path and folder name
        currentSessionFolderPath = folderpath
        currentSessionFolderName = foldername

        if (fileformat == ".mp3" or fileformat == ".mp4" or fileformat == ".wav"):
            mangaImageFrame.grid_forget()  # hide manga frame
            # show speech info frame
            speechinfoTextFrame.grid(row=1, column=0, padx=0, pady=0)
            loading = threading.Thread(
                target=loadCurrentSessionAudioListThread, args=(folderpath, lastindex))
            loading.start()
        elif (fileformat == ".pdf"):
            speechinfoTextFrame.grid_forget()  # hide speech info frame
            # show manga frame
            mangaImageFrame.grid(row=0, column=0, padx=0, pady=0)
            currentSessionListBox.delete(0, currentSessionListBox.size())
            filepath = os.path.join(appDataFolderPath, filename)
            currentPdfFile = pdfplumber.open(filepath)
            numpages = len(currentPdfFile.pages)
            for p in range(numpages):
                displayname = filename + " - page " + str(p + 1)
                currentSessionListBox.insert("end", displayname)
                currentSessionListBox.see(currentSessionListBox.size())
            # Default to show 1st page
            if (lastindex >= numpages):
                lastindex = 0
            currentSessionListBox.select_set(lastindex)
            currentSessionListBox.see(lastindex)
            page = currentPdfFile.pages[lastindex]
            imagepath = os.path.join(
                currentSessionFolderPath, "last_viewed_manga.png")
            page.to_image().save(imagepath, format="png")
            if (mangaImage != None):
                mangaImage.destroy()
                mangaImage = None
            mangaImage = CanvasImage(
                mangaImageFrame, imagepath)  # create widget
            mangaImage.grid(row=0, column=0)  # show widget
            speechtext = page.extract_text()
            speechtextEditArea.insert("end-1c", speechtext)
    else:
        utils.displayErrorMessage("Please select origin data file to load!")


def appDataFilePlayingThread(filepath):
    global repeatPlayCount
    global playingSeconds
    global totalSeconds
    global playing_timer
    a = AudioFile.audiofile(filepath)
    length = a.length()
    print("audio is around " + str(length) + " seconds")
    playingProgressbar["value"] = 0
    playingSeconds = 0
    totalSeconds = int(a.length())
    playing_timer = threading.Timer(1, playingUpdateTimerHandler)
    playing_timer.start()
    a.play()
    playingProgressbar["value"] = 0


def playAppDataFileHandler(event=None):
    global currentSessionFolderPath
    print("playAppDataFileHandler")
    filename = getAppDataFileName()
    if (filename != ""):
        print("playing folder " + appDataFolderPath)
        print("playing file " + filename)
        filepath = os.path.join(appDataFolderPath, filename)
        playing = threading.Thread(
            target=appDataFilePlayingThread, args=(filepath,))
        playing.start()
    else:
        utils.displayErrorMessage("Please select audio file to play!")


def getMangaOCRPageThread():
    global currentPdfFile
    global currentSessionFolderPath
    global currentSessionFolderName

    pdfpath = os.path.join(currentSessionFolderPath,
                           currentSessionFolderName + "-ocr.pdf")
    item = currentSessionListBox.curselection()[0]
    page = currentPdfFile.pages[item]
    image = page.to_image(resolution=100)
    pdf = pytesseract.image_to_pdf_or_hocr(image.original, extension='pdf')
    with open(pdfpath, 'w+b') as f:
        f.write(pdf)  # pdf type is bytes by default
        f.close()
    pdf = pdfplumber.open(pdfpath)
    ocrPage = pdf.pages[0]
    ocrText = ocrPage.extract_text()
    speechtextEditArea.delete("1.0", tk.END)
    speechtextEditArea.insert("end-1c", ocrText)


def getMangaOCRPageHandler(event=None):
    loading = threading.Thread(target=getMangaOCRPageThread)
    loading.start()


def getMangaOCRTextThread():
    global mangaOCR
    if mangaOCR == None:
        try:
            mangaOCR = MangaOcr()
        except ValueError:
            print("MangaOcr ValueError")
    if mangaOCR != None:
        img = ImageGrab.grabclipboard()
        text = mangaOCR(img)
        speechtextEditArea.delete("1.0", tk.END)
        speechtextEditArea.insert("end-1c", text)


def getMangaOCRTextHandler(event=None):
    loading = threading.Thread(target=getMangaOCRTextThread)
    loading.start()


def translateTextThread():
    speechtext = speechtextEditArea.get('0.0', tk.END).strip()
    if (speechtext != ""):
        translater = TranslateText.TranslateText(cfgfile="config.ini")
        speechtext = translater.translate(speechtext)
        if (len(speechtext) > 0):
            speechinfoEditArea.delete("1.0", tk.END)
            speechinfoEditArea.insert("end-1c", speechtext)
            mangaImageFrame.grid_forget()  # hide manga frame
            # show speech info frame
            speechinfoTextFrame.grid(row=1, column=0, padx=0, pady=0)


def translateTextHandler(event=None):
    translating = threading.Thread(target=translateTextThread)
    translating.start()


def playRecordedAudioHandler(event=None):
    if noRecorderRunning():
        filename = getRecordedAudioFileName()
        if (filename != ""):
            filepath = os.path.join(recordedAudioFolderPath, filename)
            if os.path.exists(filepath):
                print("playing " + filepath)
                a = AudioFile.audiofile(filepath)
                a.play()
            else:
                utils.displayErrorMessage("You must record audio first")
        else:
            utils.displayErrorMessage("You must record audio first")


def playBothAudioHandler(event=None):
    if noRecorderRunning():
        playCurrentSessionAudioFileHandler()
        playRecordedAudioHandler()


def startRecordingHandler(event=None):
    global activeAudioRecorder
    if noRecorderRunning():
        filename = getRecordedAudioFileName()
        if (filename != ""):
            activeAudioRecorder = AudioRecorder.open(
                os.path.join(recordedAudioFolderPath, filename), 'wb')
            activeAudioRecorder.start_recording()
        else:
            utils.displayErrorMessage("Set audio recording file name!")


def stopRecordingHandler(event=None):
    global activeAudioRecorder

    if activeAudioRecorder is not None:
        activeAudioRecorder.stop_recording()
        activeAudioRecorder.close()
        activeAudioRecorder = None
    else:
        utils.displayErrorMessage('Recording Not Running')


def startStopRecordingHandler(event=None):
    global activeAudioRecorder
    if activeAudioRecorder is not None:
        stopRecordingHandler()
    else:
        startRecordingHandler()


def displayHotkeysPopupHandler(event=None):
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


def updateSilenceThreshholdHandler(event=None):
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
if not os.path.exists(appDataFolderPath):
    os.makedirs(appDataFolderPath)
if not os.path.exists(recordedAudioFolderPath):
    os.makedirs(recordedAudioFolderPath)

AudioRecorder = recorder.Recorder(channels=2)
activeAudioRecorder = None

utils.root = tk.Tk()
width = utils.root .winfo_screenwidth()
height = utils.root .winfo_screenheight()
utils.root.geometry("%dx%d+0+0" % (width, height))
utils.root.state('zoomed')
utils.root.title("Speech Shadowing App")

# Create menu bar
menubar = tk.Menu(utils.root)
filemenu = tk.Menu(menubar, tearoff=0)
filemenu.add_command(label="Upload Origin Audio",
                     command=uploadAppDataFileHandler)
filemenu.add_command(label="Delete Selected Target Audio",
                     command=deleteCurrentSessionDataFileHandler)
filemenu.add_command(label="Update Silence Threshold",
                     command=updateSilenceThreshholdHandler)
filemenu.add_separator()

filemenu.add_command(label="Exit", command=utils.root.quit)
menubar.add_cascade(label="File", menu=filemenu)

helpmenu = tk.Menu(menubar, tearoff=0)
helpmenu.add_command(label="Help", command=openHelp)
helpmenu.add_command(label="Hotkeys", command=displayHotkeysPopupHandler)
menubar.add_cascade(label="Help", menu=helpmenu)

utils.root.config(menu=menubar)

# Create app left frame
appLeftFrame = tk.Frame(utils.root, bg='light sky blue')
appLeftFrame.grid(row=0, column=0, pady=5)

# Create app right frame
appRightFrame = tk.Frame(utils.root, bg='light sky blue')
appRightFrame.grid(row=0, column=1, pady=5)

utils.root.columnconfigure(0, weight=3)
utils.root.columnconfigure(1, weight=2)

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

appDataFileListBox = tk.Listbox(
    originAudioListBoxFrame, selectmode="SINGLE", width=30, exportselection=False, bg="#F4F5FF", fg='HotPink1')

originScrollbar = tk.Scrollbar(originAudioListBoxFrame)
originScrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=2)
originScrollbar.config(command=appDataFileListBox.yview)

appDataFileListBox.config(yscrollcommand=originScrollbar.set)
appDataFileListBox.bind('<Double-1>', loadAppDataFileHandler)
appDataFileListBox.pack(pady=2)

# generate list of splited audio
targetAudioFrame = tk.Frame(midFrame, bg='light sky blue')
targetAudioFrame.grid(row=0, column=1, padx=2, pady=2)

# create target audio list
label = tk.Label(targetAudioFrame, text="Target Audio List",
                 bg='light sky blue')
label.pack()

targetAudioListBoxFrame = tk.Frame(targetAudioFrame, bg='light sky blue')
targetAudioListBoxFrame.pack(padx=1)

currentSessionListBox = tk.Listbox(
    targetAudioListBoxFrame, selectmode="SINGLE", width=50, exportselection=False, bg="#F4F5FF", fg='HotPink1')

# create target audio list scroll bar
scrollbar = tk.Scrollbar(targetAudioListBoxFrame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=2)
scrollbar.config(command=currentSessionListBox.yview)

currentSessionListBox.config(yscrollcommand=scrollbar.set)
currentSessionListBox.bind('<Double-1>', playCurrentSessionAudioFileHandler)
currentSessionListBox.pack(pady=2)

midFrame.columnconfigure(0, weight=1, minsize=40)
midFrame.columnconfigure(1, weight=1, minsize=100)

# Generate low frame
lowFrame = tk.Frame(appLeftFrame, bg='light sky blue')
lowFrame.grid(row=2, column=0)

# create low left frame
lowLeftFrame = tk.Frame(lowFrame, bg='light sky blue')
lowLeftFrame.grid(row=0, column=0, padx=1, pady=2)

# create low middle frame
lowMiddleFrame = tk.Frame(lowFrame, bg='light sky blue')
lowMiddleFrame.grid(row=0, column=1, padx=1, pady=2)

# create low right frame
lowRightFrame = tk.Frame(lowFrame, bg='light sky blue')
lowRightFrame.grid(row=0, column=2, padx=1, pady=2)

lowFrame.columnconfigure(0, weight=1)
lowFrame.columnconfigure(1, weight=1)
lowFrame.columnconfigure(2, weight=1)

# create buttons for left frame
lowLeftLoadPlayButtonFrame = tk.Frame(lowLeftFrame, bg='light sky blue')
lowLeftLoadPlayButtonFrame.pack()

button_load_splited = tk.Button(
    lowLeftLoadPlayButtonFrame, text='Load Origin Audio', command=loadAppDataFileHandler, width=15)
button_load_splited.grid(row=0, column=0, pady=2)

button_load_splited = tk.Button(
    lowLeftLoadPlayButtonFrame, text='Play Origin Audio', command=playAppDataFileHandler, width=15)
button_load_splited.grid(row=0, column=1, pady=2)

lowLeftSplitButtonFrame = tk.Frame(lowLeftFrame, bg='light sky blue')
lowLeftSplitButtonFrame.pack()

button_split_origin_audio = tk.Button(
    lowLeftSplitButtonFrame, text='Split Origin Audio', command=splitAppAudioDataHandler)
button_split_origin_audio.grid(row=0, column=0, pady=2)

# separateAudioFileVocalsHandler
splitWithVocals = tk.IntVar()
checkbox_split_with_vocals = tk.Checkbutton(
    lowLeftSplitButtonFrame, text="Vocal Separation", variable=splitWithVocals)
checkbox_split_with_vocals.grid(row=0, column=1, pady=2)

lowLeftDailyWordsFrame = tk.Frame(lowLeftFrame, bg='light sky blue')
lowLeftDailyWordsFrame.pack()

button_daily_text_meanings = tk.Button(
    lowLeftDailyWordsFrame, text='Save Daily Text Meanings', command=saveDailyTextMeaningsHandler)
button_daily_text_meanings.grid(row=0, column=0, pady=2)

button_save_srt = tk.Button(
    lowLeftDailyWordsFrame, text='Save SRT', command=saveSRTHandler)
button_save_srt.grid(row=0, column=1, pady=2)

lowLeftTextButtonFrame = tk.Frame(lowLeftFrame, bg='light sky blue')
lowLeftTextButtonFrame.pack()

button_manga_ocr = tk.Button(
    lowLeftTextButtonFrame, text='OCR Page', command=getMangaOCRPageHandler)
button_manga_ocr.grid(row=0, column=0, padx=1, pady=2)

button_manga_ocr = tk.Button(
    lowLeftTextButtonFrame, text='OCR Text', command=getMangaOCRTextHandler)
button_manga_ocr.grid(row=0, column=1, padx=1, pady=2)

button_translate_text = tk.Button(
    lowLeftTextButtonFrame, text='Translate Text', command=translateTextHandler)
button_translate_text.grid(row=0, column=2, padx=1, pady=2)

lowLeftSilenceLengthCombonFrame = tk.Frame(lowLeftFrame, bg='light sky blue')
lowLeftSilenceLengthCombonFrame.pack()

label = tk.Label(lowLeftSilenceLengthCombonFrame, text="Min Slience (ms)",
                 bg='light sky blue')
label.grid(row=0, column=0)
combo_min_silence_length = ttk.Combobox(
    lowLeftSilenceLengthCombonFrame, width=5)
combo_min_silence_length['values'] = (
    200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000)
combo_min_silence_length.current(4)
combo_min_silence_length.grid(row=0, column=1)

label = tk.Label(lowLeftSilenceLengthCombonFrame, text="Min Vocal (ms)",
                 bg='light sky blue')
label.grid(row=0, column=2)
combo_min_vocal_length = ttk.Combobox(
    lowLeftSilenceLengthCombonFrame, width=5)
combo_min_vocal_length['values'] = (1000, 1500, 2000, 2500, 3000, 3500, 4000)
combo_min_vocal_length.current(4)
combo_min_vocal_length.grid(row=0, column=3)

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
    lowMiddleFrame, text='Play Target Audio (Right Alt Key)', command=playCurrentSessionAudioFileHandler, width=25)
button_playtarget.pack(pady=2)

button_playtts = tk.Button(
    lowMiddleFrame, text='Play TTS Audio (Left Alt Key)', command=playTTSAudioHandler, width=25)
button_playtts.pack(pady=2)

button_rec = tk.Button(
    lowMiddleFrame, text='Toggle Recording (Right Shift Key)', command=startStopRecordingHandler, width=25)
button_rec.pack(pady=2)

button_playboth = tk.Button(
    lowMiddleFrame, text='Play Both Audio (Right Ctrl Key)', command=playBothAudioHandler, width=25)
button_playboth.pack(pady=2)

lowMiddleTTSLanguageCombonFrame = tk.Frame(lowMiddleFrame, bg='light sky blue')
lowMiddleTTSLanguageCombonFrame.pack()

label = tk.Label(lowMiddleTTSLanguageCombonFrame, text="TTS Language",
                 bg='light sky blue')
label.grid(row=0, column=0)
combo_tts_language = ttk.Combobox(
    lowMiddleTTSLanguageCombonFrame, width=14)
combo_tts_language['values'] = (
    "David - English", "Zira - English", "Haruka - Japanese", "Huihui - Chinese")
combo_tts_language.current(2)
combo_tts_language.grid(row=0, column=1)

lowMiddleTTSRateCombonFrame = tk.Frame(lowMiddleFrame, bg='light sky blue')
lowMiddleTTSRateCombonFrame.pack()

label = tk.Label(lowMiddleTTSRateCombonFrame, text="TTS Words per Minute",
                 bg='light sky blue')
label.grid(row=0, column=0)
combo_tts_rate = ttk.Combobox(
    lowMiddleTTSRateCombonFrame, width=5)
combo_tts_rate['values'] = (80, 100, 120, 150, 180, 200, 220, 250, 280, 300)
combo_tts_rate.current(3)
combo_tts_rate.grid(row=0, column=1)

button_convert_speechtext = tk.Button(
    lowRightFrame, text='Convert Speech to Text', command=convertSpeechTextHandler, width=20)
button_convert_speechtext.pack(pady=2)

button_save_speechtext = tk.Button(
    lowRightFrame, text='Save Speech to Text', command=saveSpeechTextHandler, width=20)
button_save_speechtext.pack(pady=2)

button_info_speechtext = tk.Button(
    lowRightFrame, text='Speech Text Meanings', command=speechTextInfoHandler, width=20)
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

mangaImageFrame = tk.Frame(appRightFrame, bg='light sky blue')
mangaImageFrame.grid(row=0, column=0, padx=0, pady=0)

speechinfoTextFrame = tk.Frame(appRightFrame, bg='light sky blue')
speechinfoTextFrame.grid(row=1, column=0, padx=0, pady=0)

label = tk.Label(speechinfoTextFrame, text="Speech Text Meanings",
                 bg="#F4F5FF", fg='Blue2')
label.pack()

# create speech text info area
speechinfoScrollbarY = tk.Scrollbar(speechinfoTextFrame)
ft = tkFont.Font(family="Courier New")
speechinfoEditArea = tk.Text(speechinfoTextFrame, height=27, wrap="word",
                             yscrollcommand=speechinfoScrollbarY.set,
                             borderwidth=0, highlightthickness=0, maxundo=5, font=ft, width=45, bg="#F4F5FF", fg='HotPink1')
speechinfoScrollbarY.config(command=speechinfoEditArea.yview)
speechinfoScrollbarY.pack(side="right", fill="y")
speechinfoEditArea.pack(side="left", fill="both", expand=True)

# Create keybindings
utils.root.bind("<Alt_R>", playCurrentSessionAudioFileHandler)
utils.root.bind("<Alt_L>", playTTSAudioHandler)
utils.root.bind("<Control_R>", playBothAudioHandler)


def currentSessionSelectionDownHandler(event=None):
    selectedTuple = currentSessionListBox.curselection()
    if (len(selectedTuple) > 0):
        i = selectedTuple[0]
        if (i < currentSessionListBox.size()):
            currentSessionListBox.selection_clear(i)
            currentSessionListBox.select_set(i+1)
            currentSessionListBox.see(i+1)
    else:
        currentSessionListBox.select_set(0)
        currentSessionListBox.see(0)
    loadCurrentSessionFileHandler()


def currentSessionSelectionUpHandler(event=None):
    selectedTuple = currentSessionListBox.curselection()
    if (len(selectedTuple) > 0):
        i = selectedTuple[0]
        if (i > 0):
            currentSessionListBox.selection_clear(i)
            currentSessionListBox.select_set(i-1)
            currentSessionListBox.see(i-1)

    else:
        currentSessionListBox.select_set(0)
        currentSessionListBox.see(0)
    loadCurrentSessionFileHandler()


utils.root.bind("<Down>", currentSessionSelectionDownHandler)
utils.root.bind("<Right>", currentSessionSelectionDownHandler)
utils.root.bind("<Up>", currentSessionSelectionUpHandler)
utils.root.bind("<Left>", currentSessionSelectionUpHandler)
utils.root.bind("<Shift_R>", startStopRecordingHandler)
currentSessionListBox.bind("<<ListboxSelect>>", loadCurrentSessionFileHandler)
ttsEngine = pyttsx3.init("sapi5")  # object creation
speechTextConfig = configparser.ConfigParser()
dailyWordsConfig = configparser.ConfigParser()
daily_text_meanings_file_path = os.path.join(
    appDataFolderPath, "DailyWords.txt")
if (os.path.exists(daily_text_meanings_file_path)):
    dailyWordsConfig.read(daily_text_meanings_file_path)


def initLoading():
    # -- load target audio initially. Set info message also has a bonus that it'll start
    # the GUI before the targetAudio list has completed
    utils.displayInfoMessage("Loading Origin Audio...")
    refreshAppDataFileList()
    utils.displayInfoMessage("")


if __name__ == '__main__':
    loading = threading.Thread(target=initLoading)
    loading.start()
    utils.root.mainloop()
