from django.db import models
from usermgmt.models import CustomUser
from textmgmt.models import Text
from .storages import OverwriteStorage
from .utils import create_textrecording_stm

#May be needed in a future version
def text_rec_upload_path(instance, filename):
    sf_path = instance.recording.text.shared_folder.sharedfolder.get_path()
    return sf_path + '/AudioData/' + instance.text.id + '_' + instance.speaker.id + '.wav'


class TextRecording(models.Model):
    speaker = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    text = models.ForeignKey(Text, on_delete=models.CASCADE)

    TTS_permission = models.BooleanField(default=True)
    SR_permission = models.BooleanField(default=True)
    # is the audiofile really needed?
    audiofile = models.FileField(upload_to=text_rec_upload_path, null=True, blank=True)

    def active_sentence(self):
        return SenctenceRecording.objects.filter(recording=self).count()


def sentence_rec_upload_path(instance, filename):
    sf_path = instance.recording.text.shared_folder.sharedfolder.get_path()
    return sf_path + '/TempAudio/' + str(instance.recording.id) + '_' + str(instance.index) + '.wav'


class SenctenceRecording(models.Model):
    recording = models.ForeignKey(TextRecording, on_delete=models.CASCADE)
    index = models.IntegerField(default=0)
    audiofile = models.FileField(upload_to=sentence_rec_upload_path, storage=OverwriteStorage())

    def save(self, *args, **kwargs):
        # This should work, but I'm not 100% sure. 
        # Alternative: self.recording.active_sentence() == self.recording.text.sentence_count()
        is_update = self.pk
        super().save(*args, **kwargs)
        # check is this is the last sentence recording in a text or if this sentence recording is being updated
        if self.index == self.recording.text.sentence_count() or is_update:
            # trigger stm creation
            create_textrecording_stm(self.recording.pk)

