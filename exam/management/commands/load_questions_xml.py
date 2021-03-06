# System library imports.
from os.path import basename
from xml.dom.minidom import parse
from htmlentitydefs import name2codepoint
import re

# Django imports.
from django.core.management.base import BaseCommand

# Local imports.
from exam.models import Question

def decode_html(html_str):
    """Un-escape or decode HTML strings to more usable Python strings.
    From here: http://wiki.python.org/moin/EscapingHtml
    """
    return re.sub('&(%s);' % '|'.join(name2codepoint), 
            lambda m: unichr(name2codepoint[m.group(1)]), html_str)

def clear_questions():
    """Deactivate all questions from the database."""
    for question in Question.objects.all():
        question.active = False
        question.save()

def load_questions_xml(filename):
    """Load questions from the given XML file."""
    q_bank = parse(filename).getElementsByTagName("entry")

    for questions in q_bank:

        question_node = questions.getElementsByTagName("question")[0]
        question = (question_node.childNodes[0].data).strip()

        desc_node = questions.getElementsByTagName("description")[0]
        description = (desc_node.childNodes[0].data).strip()

        points_node = questions.getElementsByTagName("points")[0]
        points = float((points_node.childNodes[0].data).strip()) \
                 if points_node else 1.0

	neg_points_node = questions.getElementsByTagName("neg_points")[0]
        neg_points = float((neg_points_node.childNodes[0].data).strip())\
                 if neg_points_node else 0.25

        right_response_node = questions.getElementsByTagName("right_response")[0]
        right_response = decode_html((right_response_node.childNodes[0].data).strip())

        opt_node = questions.getElementsByTagName("options")[0]
        opt = decode_html((opt_node.childNodes[0].data).strip())

        new_question = Question(question=question,
                                description=description,
                                points=points,
				neg_points=neg_points,
                                options=opt,
                                right_response=right_response)
        new_question.save()
    
class Command(BaseCommand):
    args = '<q_file1.xml q_file2.xml>'
    help = 'loads the questions from given XML files'
    
    def handle(self, *args, **options):
        """Handle the command."""
        # Delete existing stuff.
        clear_questions()
        
        # Load from files.
        for fname in args:
            self.stdout.write('Importing from {0} ... '.format(basename(fname)))
            load_questions_xml(fname)
            self.stdout.write('Done\n')
            
