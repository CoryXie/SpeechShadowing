# Import the AudioSegment class for processing audio and the
# split_on_silence function for separating out silent chunks.
# code taken from https://stackoverflow.com/a/46001755 and modified for use here
import signal
from pydub import AudioSegment
from pydub.silence import split_on_silence, detect_nonsilent
import os
import utils
import psutil


class AudioSplitter(object):

    def __init__(self, filedirectory, filename, outdirectory, config, minsilencelen=1000, silencethresh=-36, minchunklen=3000):
        self.filedirectory = filedirectory
        self.filename = filename
        self.outdirectory = outdirectory
        self.minsilencelen = minsilencelen
        self.silencethresh = silencethresh
        self.silencepaddinglen = 250
        self.minchunklen = minchunklen
        self.config = config

    # Define a function to normalize a chunk to a target amplitude.
    def match_target_amplitude(self, aChunk, target_dBFS):
        ''' Normalize given audio chunk '''
        change_in_dBFS = target_dBFS - aChunk.dBFS
        return aChunk.apply_gain(change_in_dBFS)

    def split(self):
        utils.displayInfoMessage("Starting Split")
        # Load your audio.
        pathparts = self.filename.rsplit(".", 1)
        filebase = pathparts[0]
        fileformat = pathparts[1]
        song = AudioSegment.from_file(
            os.path.join(self.filedirectory, self.filename), format=fileformat)

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
        nonsilent_chunks = [
            [start - 300, end + 300]
            for (start, end)
            in detect_nonsilent(song, self.minsilencelen, self.silencethresh, 250)
        ]
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

            # Generate the time ranges
            start = nonsilent_chunks[i][0]
            end = nonsilent_chunks[i][1]
            chunk_base = "{0}-chunk{1}".format(
                self.filename[0:len(self.filename)-4], str(i).zfill(numwidth))
            self.config[filebase + "_ranges"][chunk_base +
                                              ".mp3"] = str(start) + "," + str(end)
            # Export the audio chunk with new bitrate.
            mp3path = self.outdirectory + "/" + chunk_base + ".mp3"
            wavpath = self.outdirectory + "/" + chunk_base + ".wav"

            utils.displayInfoMessage("Exporting " + chunk_base)
            normalized_chunk.export(mp3path, format="mp3")
            normalized_chunk = normalized_chunk.set_sample_width(
                2).set_frame_rate(16000).set_channels(1)
            normalized_chunk.export(wavpath, format="wav")

        utils.displayInfoMessage("Splitting Complete!")

    def splitVocals(self):

        from spleeter.separator import Separator

        utils.displayInfoMessage("Starting Split Vocals")

        pathparts = self.filename.rsplit(".", 1)
        filebase = pathparts[0]

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
        chunks = detect_nonsilent(vocals, min_silence_len=self.minsilencelen,
                                  silence_thresh=self.silencethresh, seek_step=1)

        numwidth = len(str(len(chunks)))
        numchunks = len(chunks)

        # Make it friendly for STT
        vocals = vocals.set_sample_width(
            2).set_frame_rate(16000).set_channels(1)

        # Process each chunk with your parameters
        for i in range(numchunks):

            start = chunks[i][0]
            end = chunks[i][1]

            if (start > self.silencepaddinglen):
                start = start - self.silencepaddinglen

            end += self.silencepaddinglen

            chunklen = end - start

            if (chunklen < self.minchunklen):
                continue

            # Export the audio chunk with new bitrate.
            chunk_base = "{0}-chunk{1}".format(
                self.filename[0:len(self.filename)-4], str(i).zfill(numwidth))
            self.config[filebase + "_ranges"][chunk_base +
                                              ".mp3"] = str(start) + "," + str(end)
            # Export the audio chunk with new bitrate.
            mp3path = self.outdirectory + "/" + chunk_base + ".mp3"
            wavpath = self.outdirectory + "/" + chunk_base + ".wav"

            utils.displayInfoMessage("Exporting " + mp3path)

            song[start:end].export(mp3path, format="mp3")
            vocals[start:end].export(wavpath, format="wav")

        utils.displayInfoMessage("Splitting Complete!")
