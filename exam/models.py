import datetime
from django.db import models
from django.contrib.auth.models import User

################################################################################
class Profile(models.Model):
    """Profile for a user to store roll number and other details."""
    user = models.OneToOneField(User)
    mobile_number = models.CharField(max_length=20)
    institution = models.CharField(max_length=128)
    semester = models.CharField(max_length=10)
    email = models.EmailField()
    team = models.TextField(null=True, blank=True)


#QUESTION_TYPE_CHOICES = (
#        ("python", "Python"),
#        ("bash", "Bash"),
#        ("mcq", "MultipleChoice"),
#        )

################################################################################
class Question(models.Model):
    """A question in the database."""

    # A one-line summary of the question.
    question = models.CharField(max_length=256)

    # The question text, should be valid HTML.
    description = models.TextField(null=True, blank=True)
    
    # Number of points for the question.
    points = models.FloatField(default=1.0)
    
    # Negative point
    neg_points = models.FloatField(default=0.25)
    
    # Any multiple choice options.  Place one option per line.
    options = models.TextField(blank=True)

    # Test cases for the question in the form of code that is run.
    right_response = models.TextField(blank=True)

    # The type of question.
    #type = models.CharField(max_length=24, choices=QUESTION_TYPE_CHOICES)

    # Is this question active or not.  If it is inactive it will not be used
    # when creating a QuestionPaper.
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return self.question


################################################################################
class Answer(models.Model):
    """Answers submitted by users.
    """
    # The question for which we are an answer.
    question = models.ForeignKey(Question)
    
    # The answer submitted by the user.
    answer = models.TextField(null=True, blank=True)

    # Error message when auto-checking the answer.
    error = models.TextField()

    # attempted
    attempted = models.BooleanField(default=False)

	
    # Marks obtained for the answer.  This can be changed by the teacher if the
    # grading is manual.
    marks = models.FloatField(default=0.0)
    
    # Is the answer correct.
    correct = models.BooleanField(default=False)
        
    def __unicode__(self):
        return self.answer

################################################################################
class Test(models.Model):
    """A test that students will participate in.  One can think of this 
    as the "examination" event.
    """
    
    # The starting/ending date of the test
    start_date = models.DateField("Date of the test")
    
    # This is always in minutes.
    duration = models.IntegerField("Duration of test in minutes", default=20)
    
    # Is the test active.  The admin should deactivate the test once it is 
    # complete.
    active = models.BooleanField(default=True)
    
    # Description of test.
    description = models.CharField(max_length=256)
    
    class Meta:
        verbose_name_plural = "Tests"
    
    def __unicode__(self):
        desc = self.description or 'Test'
        return '%s: on %s for %d minutes'%(desc, self.start_date, self.duration)

    
################################################################################
class QuestionPaper(models.Model):
    """A question paper for a student -- one per student typically.
    """
    # The user taking this question paper.
    user = models.ForeignKey(User)

    # The user's profile, we store a reference to make it easier to access the
    # data.
    profile = models.ForeignKey(Profile)
    
    # The Test to which this question paper is attached to.
    test = models.ForeignKey(Test)
    
    # The time when this paper was started by the user.
    start_time = models.DateTimeField()
    
    # User's IP which is logged.
    user_ip = models.CharField(max_length=15)
    # Unused currently.
    key = models.CharField(max_length=10)

    # used to allow/stop a user from retaking the question paper.
    active = models.BooleanField(default = True)
    
    # The questions (a list of ids separated by '|')
    questions = models.CharField(max_length=128)
    # The questions successfully answered (a list of ids separated by '|')
    questions_answered = models.CharField(max_length=128)
    
    # All the submitted answers.
    answers = models.ManyToManyField(Answer)

    # Teacher comments on the question paper.
    comments = models.TextField()
    
    def current_question(self):
        """Returns the current active question to display."""
        qs = self.questions.split('|')
        if len(qs) > 0:
            return qs[0]
        else:
            return ''
            
    def questions_left(self):
        """Returns the number of questions left."""
        qs = self.questions
        if len(qs) == 0:
            return 0
        else:
            return qs.count('|') + 1
            
    def completed_question(self, question_id):
        """Removes the question from the list of questions and returns
        the next."""
        qa = self.questions_answered
        if len(qa) > 0:
            self.questions_answered = '|'.join([qa, str(question_id)])
        else:
            self.questions_answered = str(question_id)
        qs = self.questions.split('|')
	try:
	    qs.remove(unicode(question_id))
	except Exception:
	    return ''
	self.questions = '|'.join(qs)
        self.save()
	if len(qs) == 0:
            return ''
        else:
            return qs[0]

    def skip(self):
        """Skip the current question and return the next available question."""
        qs = self.questions.split('|')
        if len(qs) == 0:
            return ''
        else:
            # Put head at the end.
            head = qs.pop(0)
            qs.append(head)
            self.questions = '|'.join(qs)
            self.save()
            return qs[0]
            
    def time_left(self):
        """Return the time remaining for the user in seconds."""
        dt = datetime.datetime.now() - self.start_time
        try:
            secs = dt.total_seconds()
        except AttributeError:
            # total_seconds is new in Python 2.7. :(
            secs = dt.seconds + dt.days*24*3600
        total = self.test.duration*60.0
        remain = max(total - secs, 0)
        return int(remain)

    def get_answered_str(self):
        """Returns the answered questions, sorted and as a nice string."""
        qa = self.questions_answered.split('|')
        answered = ', '.join(sorted(qa))
        return answered if answered else 'None'

    def get_total_marks(self):
        """Returns the total marks earned by student for this paper."""
        return sum([x.marks for x in self.answers.filter(marks__gte=-0.25)])

    def get_question_answers(self):
        """Return a dictionary with keys as questions and a list of the corresponding
        answers.
        """
        q_a = {}
        for answer in self.answers.all():
            question = answer.question
            if question in q_a:
                q_a[question].append(answer)
            else:
                q_a[question] = [answer]
        return q_a
    
    def __unicode__(self):
        u = self.user
        return u'Question paper for {0} {1}'.format(u.first_name, u.last_name)

