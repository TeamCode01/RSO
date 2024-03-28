from rest_framework import serializers
from .models import Question, AnswerOption


class AnswerOptionSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = AnswerOption
        fields = ('id', 'text', 'image')

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url)
        return None


class QuestionSerializer(serializers.ModelSerializer):
    answer_options = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ('id', 'title', 'image', 'answer_options')

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_answer_options(self, obj):
        answer_options = obj.answer_options.all()
        return AnswerOptionSerializer(answer_options, many=True, context=self.context).data

