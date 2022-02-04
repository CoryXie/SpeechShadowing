# Import the AudioSegment class for processing audio and the
# split_on_silence function for separating out silent chunks.
# code taken from https://stackoverflow.com/a/46001755 and modified for use here
from pydub import AudioSegment
from pydub.silence import split_on_silence, detect_silence
from spleeter.separator import Separator
import os
import utils


class AudioSplitter(object):

    def __init__(self, filedirectory, filename, outdirectory, minsilencelen=1000, silencethresh=-36):
        self.filedirectory = filedirectory
        self.filename = filename
        self.outdirectory = outdirectory
        self.minsilencelen = minsilencelen
        self.silencethresh = silencethresh
        self.silencepaddinglen = 500

    # Define a function to normalize a chunk to a target amplitude.
    def match_target_amplitude(self, aChunk, target_dBFS):
        ''' Normalize given audio chunk '''
        change_in_dBFS = target_dBFS - aChunk.dBFS
        return aChunk.apply_gain(change_in_dBFS)

    def split(self):
        utils.displayInfoMessage("Starting Split")
        # Load your audio.
        song = AudioSegment.from_mp3(
            os.path.join(self.filedirectory, self.filename))

        # Split track where the silence is the min silence length or more and get chunks using
        # the imported function.
        chunks = split_on_silence(
            # Use the loaded audio.
            song,
            # Specify that a silent chunk must be at least minsilencelen long, in milliseconds
            min_silence_len=self.minsilencelen,
            # Consider a chunk silent if it's quieter than the silence threshhold dBFS.
            # (You may want to adjust this parameter.)
            silence_thresh=self.silencethresh,
            keep_silence=300,
            seek_step=250
        )

        numwidth = len(str(len(chunks)))
        # Process each chunk with your parameters
        for i, chunk in enumerate(chunks):
            # Create a silence chunk that's 0.5 seconds (or 500 ms) long for padding.
            silence_chunk = AudioSegment.silent(
                duration=self.silencepaddinglen)

            # Add the padding chunk to beginning and end of the entire chunk.
            audio_chunk = silence_chunk + chunk + silence_chunk

            # Normalize the entire chunk.
            normalized_chunk = self.match_target_amplitude(audio_chunk, -20.0)

            # Export the audio chunk with new bitrate.
            mp3path = self.outdirectory + "//{0}-chunk{1}.mp3".format(
                self.filename[0:len(self.filename)-4], str(i).zfill(numwidth))
            wavpath = self.outdirectory + "//{0}-chunk{1}.wav".format(
                self.filename[0:len(self.filename)-4], str(i).zfill(numwidth))
            display = "{0}-chunk{1}.mp3".format(
                self.filename[0:len(self.filename)-4], str(i).zfill(numwidth))

            utils.displayInfoMessage("Exporting " + display)
            normalized_chunk.export(mp3path, format="mp3")
            normalized_chunk = normalized_chunk.set_sample_width(
                2).set_frame_rate(16000).set_channels(1)
            normalized_chunk.export(wavpath, format="wav")

        utils.displayInfoMessage("Splitting Complete!")

    def splitVocals(self):

        utils.displayInfoMessage("Starting Split Vocals")

        filepath = os.path.join(self.filedirectory, self.filename)
        wavepath = os.path.join(self.outdirectory, "vocals.wav")

        separator = Separator('spleeter:2stems')
        separator.separate_to_file(filepath, self.filedirectory)

        utils.displayInfoMessage("Starting Detecting Silence from Vocals")

        # Load your audio.
        song = AudioSegment.from_mp3(filepath)
        vocals = AudioSegment.from_wav(wavepath)

        # Split track where the silence is the min silence length or more and get chunks using
        # the imported function.
        chunks = detect_silence(vocals, min_silence_len=self.minsilencelen,
                                silence_thresh=self.silencethresh, seek_step=1)

        numwidth = len(str(len(chunks)))
        numchunks = len(chunks)

        mlist = []

        for i in range(numchunks):
            if i == (numchunks - 1):
                data = chunks[i][1]
            else:
                data = chunks[i][1] - self.silencepaddinglen
            mlist.append(data)

        # Make it friendly for STT
        vocals = vocals.set_sample_width(
            2).set_frame_rate(16000).set_channels(1)

        # Process each chunk with your parameters
        for i in range(numchunks):
            if i == 0:
                start = 0
            else:
                start = mlist[i - 1]
            end = mlist[i]

            # Export the audio chunk with new bitrate.
            mp3path = self.outdirectory + "//{0}-chunk{1}.mp3".format(
                self.filename[0:len(self.filename)-4], str(i).zfill(numwidth))
            wavpath = self.outdirectory + "//{0}-chunk{1}.wav".format(
                self.filename[0:len(self.filename)-4], str(i).zfill(numwidth))
            display = "{0}-chunk{1}.mp3".format(
                self.filename[0:len(self.filename)-4], str(i).zfill(numwidth))

            utils.displayInfoMessage("Exporting " + display)

            song[start:end].export(mp3path, format="mp3")
            vocals[start:end].export(wavpath, format="wav")

        utils.displayInfoMessage("Splitting Complete!")
