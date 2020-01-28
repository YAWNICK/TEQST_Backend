from rest_framework import serializers
from .models import TextRecording, SentenceRecording
from textmgmt.models import Text


class TextPKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        queryset = Text.objects.filter(shared_folder__sharedfolder__speaker__id=user.id)
        return queryset


class TextRecordingSerializer(serializers.ModelSerializer):

    active_sentence = serializers.IntegerField(read_only=True)
    text = TextPKField()

    def validate(self, data):
        if TextRecording.objects.filter(speaker=self.context['request'].user, text=data['text']).exists():
            raise serializers.ValidationError("A recording for the given text by the given user already exists")
        return super().validate(data)


    class Meta:
        model = TextRecording
        fields = ['id', 'speaker', 'text', 'TTS_permission', 'SR_permission', 'active_sentence']
        read_only_fields = ['speaker', 'active_sentence']

class RecordingPKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        queryset = TextRecording.objects.filter(speaker__id=user.id)
        return queryset

#Normal serializer
class SentenceRecordingSerializer(serializers.ModelSerializer):

    #def __init__(self, *args, **kwargs):
    #    super().__init__(*args, **kwargs)
    #    try:
    #        if self.context['request'].method == 'PUT':
    #            self.read_only_fields.append('recording').append('index')
    #    except KeyError:
    #        pass

    recording = RecordingPKField()

    def validate(self, data):
        try:
            data['index']
        except KeyError:
            raise serializers.ValidationError("No index provided")
        if SentenceRecording.objects.filter(index=data['index'], recording=data['recording']).exists():
            raise serializers.ValidationError("A recording for the given senctence in the given text already exists")
        if data['index'] > TextRecording.objects.get(pk=data['recording'].pk).active_sentence(): 
            raise serializers.ValidationError("Index too high. You need to record the sentences in order.")
        if data['index'] < 1:
            raise serializers.ValidationError("Invalid index.")
        return super().validate(data)
    
    # def validate_index(self, value):
    #     if value is None:
    #         raise serializers.ValidationError("Must provide sentence index")
    #     return value

    class Meta:
        model = SentenceRecording
        fields = ['recording', 'audiofile', 'index']


class SentenceRecordingUpdateSerializer(serializers.ModelSerializer):

    recording = RecordingPKField(read_only=True)

    class Meta:
        model = SentenceRecording
        fields = ['recording', 'audiofile', 'index']
        read_only_fields = ['recording', 'index']
