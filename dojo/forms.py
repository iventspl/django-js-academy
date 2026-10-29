from django import forms

from .models import DIFFICULTY_CHOICES, Question, Topic


class QuizSetupForm(forms.Form):
    topic = forms.ModelChoiceField(
        queryset=Topic.objects.all(),
        required=False,
        empty_label="All topics",
        label="Topic",
    )
    difficulty = forms.ChoiceField(
        choices=[("", "Mixed levels")] + DIFFICULTY_CHOICES,
        required=False,
        label="Difficulty",
    )
    length = forms.TypedChoiceField(
        choices=[(5, "5 questions"), (10, "10 questions"), (15, "15 questions"), (20, "20 questions")],
        coerce=int,
        initial=10,
        label="Length",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["topic"].queryset = Topic.objects.all()
        self.fields["topic"].label_from_instance = lambda topic: topic.name

    def clean(self):
        cleaned = super().clean()
        topic = cleaned.get("topic")
        difficulty = cleaned.get("difficulty")
        length = cleaned.get("length")
        if not length:
            return cleaned

        questions = Question.objects.filter(is_active=True)
        if topic:
            questions = questions.filter(topic=topic)
        if difficulty:
            questions = questions.filter(difficulty=difficulty)
        available = questions.count()
        cleaned["available_count"] = available

        if available < length:
            label = topic.name if topic else "all topics"
            if difficulty:
                label += f" · {dict(DIFFICULTY_CHOICES)[difficulty]}"
            self.add_error(
                "length",
                f"Only {available} questions are available for {label}. "
                "Choose a shorter run or widen the filters.",
            )
        return cleaned
