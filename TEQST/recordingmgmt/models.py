from django.db import models
from django.conf import settings
from django.contrib import auth
from textmgmt import models as text_models
from . import storages
import os, wave, io



#May be needed in a future version
def text_rec_upload_path(instance, filename):
    sf_path = instance.recording.text.shared_folder.get_path()
    return sf_path + '/AudioData/' + instance.text.id + '_' + instance.speaker.id + '.wav'


class TextRecording(models.Model):
    """
    Acts as a relation between a user and a text and saves all information that are specific to that recording. 
    """
    speaker = models.ForeignKey(auth.get_user_model(), on_delete=models.CASCADE)
    text = models.ForeignKey(text_models.Text, on_delete=models.CASCADE, related_name='textrecording')

    TTS_permission = models.BooleanField(default=True)
    SR_permission = models.BooleanField(default=True)

    rec_time_without_rep = models.FloatField(default=0.0)
    rec_time_with_rep = models.FloatField(default=0.0)
    # is the audiofile really needed?
    audiofile = models.FileField(upload_to=text_rec_upload_path, null=True, blank=True)

    def active_sentence(self):
        sentence_num = SentenceRecording.objects.filter(recording=self).count() + 1
        # if a speaker is finished with a text this number is one higher than the number of sentences in the text
        return sentence_num
    
    def is_finished(self):
        return SentenceRecording.objects.filter(recording=self).count() == self.text.sentence_count()
    
    def get_progress(self):
        """
        returns a tuple of (# sentences completed, # sentences in the text)
        """
        return (self.active_sentence() - 1, self.text.sentence_count())


def sentence_rec_upload_path(instance, filename):
    """
    Delivers the location in the filesystem where the recordings should be stored.
    """
    sf_path = instance.recording.text.shared_folder.get_path()
    return sf_path + '/TempAudio/' + str(instance.recording.id) + '_' + str(instance.index) + '.wav'


class SentenceRecording(models.Model):
    """
    Acts as a 'component' of a TextRecording, that saves audio and information for each sentence in the text
    """
    recording = models.ForeignKey(TextRecording, on_delete=models.CASCADE)
    index = models.IntegerField(default=0)
    audiofile = models.FileField(upload_to=sentence_rec_upload_path, storage=storages.BackupStorage())

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.recording.active_sentence() > self.recording.text.sentence_count():
            create_textrecording_stm(self.recording.id)
    
    def get_audio_length(self):
        wav = wave.open(self.audiofile, 'rb')
        duration = wav.getnframes() / wav.getframerate()
        wav.close()
        self.audiofile.close()
        return duration


def create_textrecording_stm(trec_pk):
    """
    create stm and concatenated audio for one textrecording. These are created upon first completion of a text by a user, 
    and again recreated every time the user rerecords a sentence. The stm does not contain the stm header.
    trec_pk: string = TextRecording pk
    """
    trec = TextRecording.objects.get(pk=trec_pk)
    srecs = SentenceRecording.objects.filter(recording=trec)

    # update logfile
    logpath = settings.MEDIA_ROOT + '/' + trec.text.shared_folder.get_path() + '/log.txt'
    add_user_to_log(logpath, trec.speaker)

    #create string with encoded userdata
    user_str = '<' + trec.speaker.gender + ',' + trec.speaker.education + ','
    if trec.SR_permission:
        user_str += 'SR'
    if trec.TTS_permission:
        user_str += 'TTS'
    user_str += '>'
    username = trec.speaker.username
    current_timestamp = 0
    sentences = trec.text.get_content()

    # create .stm file and open in write mode
    path = settings.MEDIA_ROOT + '/' + trec.text.shared_folder.get_path() + '/STM/' + trec.text.title + '-' + username + '.stm'
    stm_file = io.open(path, 'w+', encoding='utf8')

    # create concatenated wav file and open in write mode (uses 'wave' library)
    wav_path_rel = trec.text.title + '-' + username
    wav_path = settings.MEDIA_ROOT + '/' + trec.text.shared_folder.get_path() + '/AudioData/' + wav_path_rel + '.wav'
    wav_full = wave.open(wav_path, 'wb')

    #Create .stm entries for each sentence-recording and concatenate the recording to the 'large' file
    for srec in srecs:
        wav = wave.open(srec.audiofile, 'rb')

        #On concatenating the first file: also copy all settings
        if current_timestamp == 0:
            wav_full.setparams(wav.getparams())
        duration = wav.getnframes()/wav.getframerate()

        #utterance id
        stm_file.write(wav_path_rel + '_')
        stm_file.write(username + '_')
        stm_file.write(format_timestamp(current_timestamp) + '_')
        stm_file.write(format_timestamp(current_timestamp + duration) + ' ')

        #write .stm file entry
        stm_file.write(wav_path_rel + ' ')
        stm_file.write(str(wav.getnchannels()) + ' ')
        stm_file.write(username + ' ')
        stm_file.write("{0:.2f}".format(current_timestamp) + ' ')
        current_timestamp += duration
        stm_file.write("{0:.2f}".format(current_timestamp) + ' ')
        stm_file.write(user_str + ' ')
        stm_file.write(sentences[srec.index - 1] + '\n')

        #copy audio
        wav_full.writeframesraw(wav.readframes(wav.getnframes()))

        #close sentence-recording file
        wav.close()

    #close files
    stm_file.close()
    wav_full.close()

    #concatenate all .stm files to include the last changes
    concat_stms(trec.text.shared_folder)


def concat_stms(sharedfolder):
    """
    Concatenate all .stm files in the given sharedfolder to include all changes
    """

    #Build paths and open the 'large' stm in read-mode
    sf_path = sharedfolder.get_path()
    stm_path = sf_path + '/STM'
    temp_stm_names = os.listdir(settings.MEDIA_ROOT + '/' + stm_path)  # this lists directories as well, but there shouldnt be any in this directory
    stm_file = io.open(settings.MEDIA_ROOT + '/' + sf_path + '/' + sharedfolder.name + '.stm', 'w', encoding='utf8')

    #Open, concatenate and close the header file
    header_file = io.open(settings.BASE_DIR + '/header.stm', 'r', encoding='utf8')
    stm_file.write(header_file.read())
    header_file.close()

    #concatenate all existing stm files
    for temp_stm_name in temp_stm_names:
        temp_stm_file = io.open(settings.MEDIA_ROOT + '/' + stm_path + '/' + temp_stm_name, 'r', encoding='utf8')
        stm_file.write(temp_stm_file.read())
        temp_stm_file.close()
    
    stm_file.close()


def format_timestamp(t):
    return "{0:0>7}".format(int(round(t*100, 0)))


def log_contains_user(path, username):
    logfile = open(path, 'r')
    lines = logfile.readlines()
    for i in range(len(lines)):
        if lines[i][:8] == 'username':
            if lines[i][10:] == username + '\n':
                return True
    logfile.close()
    return False


def add_user_to_log(path, user):
    if log_contains_user(path, str(user.username)):
        return
    logfile = open(path, 'a')
    logfile.write('username: ' + str(user.username) + '\n')
    logfile.write('birth_year: ' + str(user.birth_year) + '\n')
    logfile.write('gender: ' + str(user.gender) + '\n')
    logfile.write('education: ' + str(user.education) + '\n')
    logfile.write('accent: ' + str(user.accent) + '\n')
    logfile.write('country: ' + str(user.country) + '\n')
    logfile.write('#\n')
    logfile.close()