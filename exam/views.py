import random
import string
import os
import stat
from os.path import dirname, pardir, abspath, join, exists
import datetime

from django.contrib.auth import login, logout, authenticate
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.http import Http404
from django.db.models import Sum
from django.views.decorators.cache import cache_control

# Local imports.
from exam.models import Test, Question, QuestionPaper, Profile, Answer, User
from exam.forms import UserRegisterForm
from exam.xmlrpc_clients import code_server
from settings import URL_ROOT

# The directory where user data can be saved.
OUTPUT_DIR = abspath(join(dirname(__file__), pardir, 'output'))


def my_redirect(url):
    """An overridden redirect to deal with URL_ROOT-ing.  See settings.py 
    for details."""
    return redirect(URL_ROOT + url)

def my_render_to_response(template, context=None, **kwargs):
    """Overridden render_to_response.
    """
    if context is None:
        context = {'URL_ROOT': URL_ROOT}
    else:
        context['URL_ROOT'] = URL_ROOT
    return render_to_response(template, context, **kwargs)        


def gen_key(no_of_chars):
    """Generate a random key of the number of characters."""
    allowed_chars = string.digits+string.uppercase
    return ''.join([random.choice(allowed_chars) for i in range(no_of_chars)])
    
def get_user_dir(user):
    """Return the output directory for the user."""
    user_dir = join(OUTPUT_DIR, str(user.username))
    if not exists(user_dir):
        os.mkdir(user_dir)
        # Make it rwx by others.
        os.chmod(user_dir, stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH \
                | stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR \
                | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP)
    return user_dir
    
def index(request):
    """The start page.
    """
    user = request.user
    if user.is_authenticated():
        return my_redirect("/exam/start/")

    return my_redirect("/exam/register/")

def user_register(request):
    """ Register a new user.
    Create a user and corresponding profile and store roll_number also."""

    user = request.user
    if user.is_authenticated():
        return my_redirect("/exam/start/")
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            u_name = form.save()

            new_user = authenticate(username=u_name)
            login(request, new_user)
            return my_redirect("/exam/start/")
                
        else:
            return my_render_to_response('exam/register.html',
                {'form':form},
                context_instance=RequestContext(request))
    else:
        form = UserRegisterForm()
        return my_render_to_response('exam/register.html',
                {'form':form},
                context_instance=RequestContext(request))


"""def user_login(request):
    Take the credentials of the user and log the user in.

    user = request.user
    if user.is_authenticated():
        return my_redirect("/exam/start/")

    if request.method == "POST":
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data
            login(request, user)
            return my_redirect("/exam/start/")
        else:
            context = {"form": form}
            return my_render_to_response('exam/login.html', context,
                        context_instance=RequestContext(request))
    else:
        form = UserLoginForm()
        context = {"form": form}
        return my_render_to_response('exam/login.html', context,
                                     context_instance=RequestContext(request))
"""

def start(request):
    user = request.user
    try:
        # Right now the app is designed so there is only one active test
        # at a particular time.
        test = Test.objects.get(active=True)
    except Test.DoesNotExist:
        msg = 'No active test found, please contact your '\
              'instructor/administrator. Please login again thereafter.'
        return complete(request, reason=msg)
    try:
        old_paper = QuestionPaper.objects.get(user=user, test=test)
        q = old_paper.current_question()
        return show_question(request, q)
    except QuestionPaper.DoesNotExist:
        ip = request.META['REMOTE_ADDR']
        key = gen_key(10)
        try:
            profile = user.get_profile()
        except Profile.DoesNotExist:
            msg = 'You do not have a profile and cannot take the test!'
            raise Http404(msg)

        new_paper = QuestionPaper(user=user, user_ip=ip, key=key, 
                                  test=test, profile=profile)
        new_paper.start_time = datetime.datetime.now()
        
        # Make user directory.
        user_dir = get_user_dir(user)

        questions = [ str(_.id) for _ in Question.objects.filter(active=True) ]
        random.shuffle(questions)
        
        new_paper.questions = "|".join(questions)
        new_paper.save()

	old_paper = QuestionPaper.objects.get(user=user, test=test)
        q = old_paper.current_question()
        return show_question(request, q)
    

def question(request, q_id):
    user = request.user
    if not user.is_authenticated():
        return my_redirect('/exam/register/')
    q = get_object_or_404(Question, pk=q_id)
    try:
        paper = QuestionPaper.objects.get(user=request.user, test__active=True)
    except QuestionPaper.DoesNotExist:
        return my_redirect('/exam/start')
    if not paper.test.active:
        return complete(request, reason='The test has been deactivated!')

    time_left = paper.time_left()
    if time_left == 0:
        return complete(request, reason='Your time is up!')
    test_name = paper.test.description
    context = {'question': q, 'paper': paper, 'user': user, 
               'test_name': test_name, 
               'time_left': time_left}
    ci = RequestContext(request)
    return my_render_to_response('exam/question.html', context, 
                                 context_instance=ci)

def show_question(request, q_id):
    """Show a question if possible."""
    if len(q_id) == 0:
        msg = 'Congratulations!  You have successfully completed the test.'
        return complete(request, msg)
    else:
        return question(request, q_id)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def check(request, q_id):
    user = request.user
    if not user.is_authenticated():
        return my_redirect('/exam/register/')
    question = get_object_or_404(Question, pk=q_id)
    paper = QuestionPaper.objects.get(user=user, test__active=True)
    answer = request.POST.get('answer')
    skip = request.POST.get('skip', None)
    
    if skip is not None:
        next_q = paper.skip()
        return show_question(request, next_q)

    # Add the answer submitted, regardless of it being correct or not.
    new_answer = Answer(question=question, answer=answer, correct=False)
    new_answer.save()
    paper.answers.add(new_answer)

    # If we were not skipped, we were asked to check.  For any non-mcq
    # questions, we obtain the results via XML-RPC with the code executed
    # safely in a separate process (the code_server.py) running as nobody.
    if not new_answer.attempted and answer  :
     	if answer.strip() == question.right_response.strip():
        	new_answer.correct = True
        	new_answer.marks = question.points
        	new_answer.error = 'Correct answer'
    	else:
       		new_answer.correct = False
        	new_answer.marks = -(question.neg_points)
        	new_answer.error = 'Incorrect answer'
        
        
    	new_answer.attempted = True # Only one attempt allowed for MCQ's.
        new_answer.save()


    next_q = paper.completed_question(question.id)
    return show_question(request, next_q)
        
def quit(request):
    return my_render_to_response('exam/quit.html', 
                                 context_instance=RequestContext(request)) 

def complete(request, reason=None):
    user = request.user
    no = False
    message = reason or 'The test has been completed. Thank you.'
    if request.method == 'POST' and 'no' in request.POST:
        no = request.POST.get('no', False)
    if not no:
        # Logout the user and quit with the message given.
        logout(request)
        context = {'message': message}
        return my_render_to_response('exam/complete.html',context,context_instance=RequestContext(request))
    else:
        return my_redirect('/exam/')


def monitor(request, test_id=None):
    """Monitor the progress of the papers taken so far."""
    user = request.user
    if not user.is_authenticated() and not user.is_staff:
        raise Http404('You are not allowed to view this page!')

    if test_id is None:
        tests = Test.objects.all()
        context = {'papers': [], 
                   'test': None, 
                   'tests':tests}
        return my_render_to_response('exam/monitor.html', context,
                                    context_instance=RequestContext(request)) 
    # test_id is not None.
    try:
        test = Test.objects.get(id=test_id)
    except test.DoesNotExist:
        papers = []
        test = None
    else:
        papers = QuestionPaper.objects.all().annotate(
                    total=Sum('answers__marks')).order_by('-total')

    context = {'papers': papers, 'test': test, 'tests': None}
    return my_render_to_response('exam/monitor.html', context,
                                 context_instance=RequestContext(request)) 

def get_user_data(username):
    """For a given username, this returns a dictionary of important data
    related to the user including all the user's answers submitted.
    """
    user = User.objects.get(username=username)
    papers = QuestionPaper.objects.filter(user=user)

    data = {}
    try:
        profile = user.get_profile()
    except Profile.DoesNotExist:
        # Admin user may have a paper by accident but no profile.
        profile = None
    data['user'] = user
    data['profile'] = profile
    data['papers'] = papers 
    return data

def user_data(request, username):
    """Render user data."""
    current_user = request.user
    if not current_user.is_authenticated() and not current_user.is_staff:
        raise Http404('You are not allowed to view this page!')

    data = get_user_data(username)

    context = {'data': data}
    return my_render_to_response('exam/user_data.html', context,
                                 context_instance=RequestContext(request))
"""
def grade_user(request, username):
    Present an interface with which we can easily grade a user's papers
    and update all their marks and also give comments for each paper.
    
    current_user = request.user
    if not current_user.is_authenticated() and not current_user.is_staff:
        raise Http404('You are not allowed to view this page!')

    data = get_user_data(username)
    if request.method == 'POST':
        papers = data['papers']
        for paper in papers:
            for question, answers in paper.get_question_answers().iteritems():
                marks = float(request.POST.get('q%d_marks'%question.id))
                last_ans = answers[-1]
                last_ans.marks = marks
                last_ans.save()
            paper.comments = request.POST.get('comments_%d'%paper.test.id)
            paper.save()

        context = {'data': data}
        return my_render_to_response('exam/user_data.html', context,
                                 context_instance=RequestContext(request))
    else:
        context = {'data': data}
        return my_render_to_response('exam/grade_user.html', context,
                                 context_instance=RequestContext(request))
"""
