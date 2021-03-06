# System library imports.
from os.path import basename

# Django imports.
from django.core.management.base import BaseCommand

# Local imports.
from exam.models import Question, Test

def clear_exam():
    """Deactivate all questions from the database."""
    for question in Question.objects.all():
        question.active = False
        question.save()
        
    # Deactivate old Tests.
    for test in Test.objects.all():
        test.active = False
        test.save()

def load_exam(filename):
    """Load questions and test from the given Python file.  The Python file 
    should declare a list of name "questions" which define all the questions 
    in pure Python.  It can optionally load a Test from an optional 'test' 
    object.
    """
    # Simply exec the given file and we are done.
    exec(open(filename).read())
    
    if 'questions' not in locals():
        msg = 'No variable named "questions" with the Questions in file.'
        raise NameError(msg)
    
    for question in questions:
        question.save()
        
    if 'test' in locals():
        test.save()
    
class Command(BaseCommand):
    args = '<q_file1.py q_file2.py>'
    help = '''loads the questions from given Python files which declare the 
              questions in a list called "questions".'''
    
    def handle(self, *args, **options):
        """Handle the command."""
        # Delete existing stuff.
        clear_exam()
        
        # Load from files.
        for fname in args:
            self.stdout.write('Importing from {0} ... '.format(basename(fname)))
            load_exam(fname)
            self.stdout.write('Done\n')
            
