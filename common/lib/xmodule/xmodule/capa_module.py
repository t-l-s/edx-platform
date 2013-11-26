"""Implements basics of Capa, including class CapaModule."""
import json
import logging
import sys

from pkg_resources import resource_string

from .capa_base import CapaMixin, CapaFields, ComplexEncoder
from .progress import Progress
from xmodule.x_module import XModule, module_attr
from xmodule.raw_module import RawDescriptor
from xmodule.exceptions import NotFoundError, ProcessingError

log = logging.getLogger("edx.courseware")


class CapaModule(CapaMixin, XModule):
    """
    An XModule implementing LonCapa format problems, implemented by way of
    capa.capa_problem.LoncapaProblem

    CapaModule.__init__ takes the same arguments as xmodule.x_module:XModule.__init__
    """
    icon_class = 'problem'

    js = {'coffee': [resource_string(__name__, 'js/src/capa/display.coffee'),
                     resource_string(__name__, 'js/src/collapsible.coffee'),
                     resource_string(__name__, 'js/src/javascript_loader.coffee'),
                     ],
          'js': [resource_string(__name__, 'js/src/capa/imageinput.js'),
                 resource_string(__name__, 'js/src/capa/schematic.js')
                 ]}

    js_module_name = "Problem"
    css = {'scss': [resource_string(__name__, 'css/capa/display.scss')]}

    def __init__(self, *args, **kwargs):
        """
        Accepts the same arguments as xmodule.x_module:XModule.__init__
        """
        super(CapaModule, self).__init__(*args, **kwargs)

    def handle_ajax(self, dispatch, data):
        """
        This is called by courseware.module_render, to handle an AJAX call.

        `data` is request.POST.

        Returns a json dictionary:
        { 'progress_changed' : True/False,
          'progress' : 'none'/'in_progress'/'done',
          <other request-specific values here > }
        """
        handlers = {
            'problem_get': self.get_problem,
            'problem_check': self.check_problem,
            'problem_reset': self.reset_problem,
            'problem_save': self.save_problem,
            'problem_show': self.get_answer,
            'score_update': self.update_score,
            'input_ajax': self.handle_input_ajax,
            'ungraded_response': self.handle_ungraded_response
        }

        _ = self.runtime.service(self, "i18n").ugettext

        generic_error_message = _(
            "We're sorry, there was an error with processing your request. "
            "Please try reloading your page and trying again."
        )

        not_found_error_message = _(
            "The state of this problem has changed since you loaded this page. "
            "Please refresh your page."
        )

        if dispatch not in handlers:
            return 'Error: {} is not a known capa action'.format(dispatch)

        before = self.get_progress()

        try:
            result = handlers[dispatch](data)

        except NotFoundError as err:
            _, _, traceback_obj = sys.exc_info()  # pylint: disable=redefined-outer-name
            raise ProcessingError, (not_found_error_message, err), traceback_obj

        except Exception as err:
            _, _, traceback_obj = sys.exc_info()  # pylint: disable=redefined-outer-name
            raise ProcessingError, (generic_error_message, err), traceback_obj

        after = self.get_progress()

        result.update({
            'progress_changed': after != before,
            'progress_status': Progress.to_js_status_str(after),
            'progress_detail': Progress.to_js_detail_str(after),
        })

        return json.dumps(result, cls=ComplexEncoder)

    def is_past_due(self):
        """
        Is it now past this problem's due date, including grace period?
        """
        return (self.close_date is not None and
                datetime.datetime.now(UTC()) > self.close_date)

    def closed(self):
        """
        Is the student still allowed to submit answers?
        """
        if self.max_attempts is not None and self.attempts >= self.max_attempts:
            return True
        if self.is_past_due():
            return True

        return False

    def is_submitted(self):
        """
        Used to decide to show or hide RESET or CHECK buttons.

        Means that student submitted problem and nothing more.
        Problem can be completely wrong.
        Pressing RESET button makes this function to return False.
        """
        # used by conditional module
        return self.lcp.done

    def is_attempted(self):
        """
        Has the problem been attempted?

        used by conditional module
        """
        return self.attempts > 0

    def is_correct(self):
        """
        True iff full points
        """
        score_dict = self.get_score()
        return score_dict['score'] == score_dict['total']

    def answer_available(self):
        """
        Is the user allowed to see an answer?
        """
        if self.showanswer == '':
            return False
        elif self.showanswer == "never":
            return False
        elif self.system.user_is_staff:
            # This is after the 'never' check because admins can see the answer
            # unless the problem explicitly prevents it
            return True
        elif self.showanswer == 'attempted':
            return self.attempts > 0
        elif self.showanswer == 'answered':
            # NOTE: this is slightly different from 'attempted' -- resetting the problems
            # makes lcp.done False, but leaves attempts unchanged.
            return self.lcp.done
        elif self.showanswer == 'closed':
            return self.closed()
        elif self.showanswer == 'finished':
            return self.closed() or self.is_correct()

        elif self.showanswer == 'past_due':
            return self.is_past_due()
        elif self.showanswer == 'always':
            return True

        return False

    def update_score(self, data):
        """
        Delivers grading response (e.g. from asynchronous code checking) to
            the capa problem, so its score can be updated

        'data' must have a key 'response' which is a string that contains the
            grader's response

        No ajax return is needed. Return empty dict.
        """
        queuekey = data['queuekey']
        score_msg = data['xqueue_body']
        self.lcp.update_score(score_msg, queuekey)
        self.set_state_from_lcp()
        self.publish_grade()

        return dict()  # No AJAX return is needed

    def handle_ungraded_response(self, data):
        """
        Delivers a response from the XQueue to the capa problem

        The score of the problem will not be updated

        Args:
            - data (dict) must contain keys:
                            queuekey - a key specific to this response
                            xqueue_body - the body of the response
        Returns:
            empty dictionary

        No ajax return is needed, so an empty dict is returned
        """
        queuekey = data['queuekey']
        score_msg = data['xqueue_body']

        # pass along the xqueue message to the problem
        self.lcp.ungraded_response(score_msg, queuekey)
        self.set_state_from_lcp()
        return dict()

    def handle_input_ajax(self, data):
        """
        Handle ajax calls meant for a particular input in the problem

        Args:
            - data (dict) - data that should be passed to the input
        Returns:
            - dict containing the response from the input
        """
        response = self.lcp.handle_input_ajax(data)

        # save any state changes that may occur
        self.set_state_from_lcp()
        return response

    def get_answer(self, _data):
        """
        For the "show answer" button.

        Returns the answers: {'answers' : answers}
        """
        event_info = dict()
        event_info['problem_id'] = self.location.url()
        self.system.track_function('showanswer', event_info)
        if not self.answer_available():
            raise NotFoundError('Answer is not available')
        else:
            answers = self.lcp.get_question_answers()
            self.set_state_from_lcp()

        # answers (eg <solution>) may have embedded images
        #   but be careful, some problems are using non-string answer dicts
        new_answers = dict()
        for answer_id in answers:
            try:
                new_answer = {answer_id: self.system.replace_urls(answers[answer_id])}
            except TypeError:
                log.debug(u'Unable to perform URL substitution on answers[%s]: %s',
                          answer_id, answers[answer_id])
                new_answer = {answer_id: answers[answer_id]}
            new_answers.update(new_answer)

        return {'answers': new_answers}

    # Figure out if we should move these to capa_problem?
    def get_problem(self, _data):
        """
        Return results of get_problem_html, as a simple dict for json-ing.
        { 'html': <the-html> }

        Used if we want to reconfirm we have the right thing e.g. after
        several AJAX calls.
        """
        return {'html': self.get_problem_html(encapsulate=False)}

    @staticmethod
    def make_dict_of_responses(data):
        """
        Make dictionary of student responses (aka "answers")

        `data` is POST dictionary (webob.multidict.MultiDict).

        The `data` dict has keys of the form 'x_y', which are mapped
        to key 'y' in the returned dict.  For example,
        'input_1_2_3' would be mapped to '1_2_3' in the returned dict.

        Some inputs always expect a list in the returned dict
        (e.g. checkbox inputs).  The convention is that
        keys in the `data` dict that end with '[]' will always
        have list values in the returned dict.
        For example, if the `data` dict contains {'input_1[]': 'test' }
        then the output dict would contain {'1': ['test'] }
        (the value is a list).

        Some other inputs such as ChoiceTextInput expect a dict of values in the returned
        dict  If the key ends with '{}' then we will assume that the value is a json
        encoded dict and deserialize it.
        For example, if the `data` dict contains {'input_1{}': '{"1_2_1": 1}'}
        then the output dict would contain {'1': {"1_2_1": 1} }
        (the value is a dictionary)

        Raises an exception if:

        -A key in the `data` dictionary does not contain at least one underscore
          (e.g. "input" is invalid, but "input_1" is valid)

        -Two keys end up with the same name in the returned dict.
          (e.g. 'input_1' and 'input_1[]', which both get mapped to 'input_1'
           in the returned dict)
        """
        answers = dict()

        # webob.multidict.MultiDict is a view of a list of tuples,
        # so it will return a multi-value key once for each value.
        # We only want to consider each key a single time, so we use set(data.keys())
        for key in set(data.keys()):
            # e.g. input_resistor_1 ==> resistor_1
            _, _, name = key.partition('_')  # pylint: disable=redefined-outer-name

            # If key has no underscores, then partition
            # will return (key, '', '')
            # We detect this and raise an error
            if not name:
                raise ValueError(u"{key} must contain at least one underscore".format(key=key))

            else:
                # This allows for answers which require more than one value for
                # the same form input (e.g. checkbox inputs). The convention is that
                # if the name ends with '[]' (which looks like an array), then the
                # answer will be an array.
                # if the name ends with '{}' (Which looks like a dict),
                # then the answer will be a dict
                is_list_key = name.endswith('[]')
                is_dict_key = name.endswith('{}')
                name = name[:-2] if is_list_key or is_dict_key else name

                if is_list_key:
                    val = data.getall(key)
                elif is_dict_key:
                    try:
                        val = json.loads(data[key])
                    # If the submission wasn't deserializable, raise an error.
                    except(KeyError, ValueError):
                        raise ValueError(
                            u"Invalid submission: {val} for {key}".format(val=data[key], key=key)
                        )
                else:
                    val = data[key]

                # If the name already exists, then we don't want
                # to override it.  Raise an error instead
                if name in answers:
                    raise ValueError(u"Key {name} already exists in answers dict".format(name=name))
                else:
                    answers[name] = val

        return answers

    def publish_grade(self):
        """
        Publishes the student's current grade to the system as an event
        """
        score = self.lcp.get_score()
        self.system.publish({
            'event_name': 'grade',
            'value': score['score'],
            'max_value': score['total'],
        })

        return {'grade': score['score'], 'max_grade': score['total']}

    def check_problem(self, data):
        """
        Checks whether answers to a problem are correct

        Returns a map of correct/incorrect answers:
          {'success' : 'correct' | 'incorrect' | AJAX alert msg string,
           'contents' : html}
        """
        event_info = dict()
        event_info['state'] = self.lcp.get_state()
        event_info['problem_id'] = self.location.url()

        answers = self.make_dict_of_responses(data)
        # hack ipdb - temp line
        event_info['answers'] = convert_files_to_filenames(answers)

        # Too late. Cannot submit
        if self.closed():
            event_info['failure'] = 'closed'
            self.system.track_function('problem_check_fail', event_info)
            raise NotFoundError('Problem is closed')

        # Problem submitted. Student should reset before checking again
        if self.done and self.rerandomize == "always":
            event_info['failure'] = 'unreset'
            self.system.track_function('problem_check_fail', event_info)
            raise NotFoundError('Problem must be reset before it can be checked again')

        # Problem queued. Students must wait a specified waittime before they are allowed to submit
        if self.lcp.is_queued():
            current_time = datetime.datetime.now(UTC())
            prev_submit_time = self.lcp.get_recentmost_queuetime()
            waittime_between_requests = self.system.xqueue['waittime']
            if (current_time - prev_submit_time).total_seconds() < waittime_between_requests:
                msg = u'You must wait at least {wait} seconds between submissions'.format(
                    wait=waittime_between_requests)
                return {'success': msg, 'html': ''}  # Prompts a modal dialog in ajax callback

        try:
            correct_map = self.lcp.grade_answers(answers)
            self.attempts = self.attempts + 1
            self.lcp.done = True
            self.set_state_from_lcp()

        except (StudentInputError, ResponseError, LoncapaProblemError) as inst:
            log.warning("StudentInputError in capa_module:problem_check",
                        exc_info=True)

            # Save the user's state before failing
            self.set_state_from_lcp()

            # If the user is a staff member, include
            # the full exception, including traceback,
            # in the response
            if self.system.user_is_staff:
                msg = u"Staff debug info: {tb}".format(tb=cgi.escape(traceback.format_exc()))

            # Otherwise, display just an error message,
            # without a stack trace
            else:
                msg = u"Error: {msg}".format(msg=inst.message)

            return {'success': msg}

        except Exception as err:
            # Save the user's state before failing
            self.set_state_from_lcp()

            if self.system.DEBUG:
                msg = u"Error checking problem: {}".format(err.message)
                msg += u'\nTraceback:\n{}'.format(traceback.format_exc())
                return {'success': msg}
            raise

        published_grade = self.publish_grade()

        # success = correct if ALL questions in this problem are correct
        success = 'correct'
        for answer_id in correct_map:
            if not correct_map.is_correct(answer_id):
                success = 'incorrect'

        # NOTE: We are logging both full grading and queued-grading submissions. In the latter,
        #       'success' will always be incorrect
        event_info['grade'] = published_grade['grade']
        event_info['max_grade'] = published_grade['max_grade']
        event_info['correct_map'] = correct_map.get_dict()
        event_info['success'] = success
        event_info['attempts'] = self.attempts
        # The logged data uses the native, non-shuffled names of answer choices.
        self.translate_to_native(event_info['answers'])
        #import ipdb
        #ipdb.set_trace()
        self.system.track_function('problem_check', event_info)

        if hasattr(self.system, 'psychometrics_handler'):  # update PsychometricsData using callback
            self.system.psychometrics_handler(self.get_state_for_lcp())

        # render problem into HTML
        html = self.get_problem_html(encapsulate=False)

        return {'success': success,
                'contents': html,
                }

    def translate_to_native(self, answers):
        """
        Translate the given answers so names like choice_0 reflect the
        "native" (not-shuffled) name of each choice.
        This only does anything for shuffled multiple choice responses.
        """
        # answers is like: {u'i4x-Stanford-CS99-problem-dada976e76f34c24bc8415039dee1300_2_1': u'choice_1'}
        # self.lcp.responders is like {<Element multiplechoiceresponse at 0x109ba6b40>: <capa.responsetypes.MultipleChoiceResponse object at 0x109bb8bd0>}
        # value of above has answer_id which matches the key in answers
        for response in self.lcp.responders.values():
            if hasattr(response, 'is_shuffled') and response.answer_id in answers:
                name = answers[response.answer_id]
                answers[response.answer_id] = response.native_name(name)
    
    
    
    def rescore_problem(self):
        """
        Checks whether the existing answers to a problem are correct.

        This is called when the correct answer to a problem has been changed,
        and the grade should be re-evaluated.

        Returns a dict with one key:
            {'success' : 'correct' | 'incorrect' | AJAX alert msg string }

        Raises NotFoundError if called on a problem that has not yet been
        answered, or NotImplementedError if it's a problem that cannot be rescored.

        Returns the error messages for exceptions occurring while performing
        the rescoring, rather than throwing them.
        """
        event_info = {'state': self.lcp.get_state(), 'problem_id': self.location.url()}

        if not self.lcp.supports_rescoring():
            event_info['failure'] = 'unsupported'
            self.system.track_function('problem_rescore_fail', event_info)
            raise NotImplementedError("Problem's definition does not support rescoring")

        if not self.done:
            event_info['failure'] = 'unanswered'
            self.system.track_function('problem_rescore_fail', event_info)
            raise NotFoundError('Problem must be answered before it can be graded again')

        # get old score, for comparison:
        orig_score = self.lcp.get_score()
        event_info['orig_score'] = orig_score['score']
        event_info['orig_total'] = orig_score['total']

        try:
            correct_map = self.lcp.rescore_existing_answers()

        except (StudentInputError, ResponseError, LoncapaProblemError) as inst:
            log.warning("Input error in capa_module:problem_rescore", exc_info=True)
            event_info['failure'] = 'input_error'
            self.system.track_function('problem_rescore_fail', event_info)
            return {'success': u"Error: {0}".format(inst.message)}

        except Exception as err:
            event_info['failure'] = 'unexpected'
            self.system.track_function('problem_rescore_fail', event_info)
            if self.system.DEBUG:
                msg = u"Error checking problem: {0}".format(err.message)
                msg += u'\nTraceback:\n' + traceback.format_exc()
                return {'success': msg}
            raise

        # rescoring should have no effect on attempts, so don't
        # need to increment here, or mark done.  Just save.
        self.set_state_from_lcp()

        self.publish_grade()

        new_score = self.lcp.get_score()
        event_info['new_score'] = new_score['score']
        event_info['new_total'] = new_score['total']

        # success = correct if ALL questions in this problem are correct
        success = 'correct'
        for answer_id in correct_map:
            if not correct_map.is_correct(answer_id):
                success = 'incorrect'

        # NOTE: We are logging both full grading and queued-grading submissions. In the latter,
        #       'success' will always be incorrect
        event_info['correct_map'] = correct_map.get_dict()
        event_info['success'] = success
        event_info['attempts'] = self.attempts
        self.system.track_function('problem_rescore', event_info)

        # psychometrics should be called on rescoring requests in the same way as check-problem
        if hasattr(self.system, 'psychometrics_handler'):  # update PsychometricsData using callback
            self.system.psychometrics_handler(self.get_state_for_lcp())

        return {'success': success}

    def save_problem(self, data):
        """
        Save the passed in answers.
        Returns a dict { 'success' : bool, 'msg' : message }
        The message is informative on success, and an error message on failure.
        """
        event_info = dict()
        event_info['state'] = self.lcp.get_state()
        event_info['problem_id'] = self.location.url()

        answers = self.make_dict_of_responses(data)
        event_info['answers'] = answers

        # Too late. Cannot submit
        if self.closed() and not self.max_attempts == 0:
            event_info['failure'] = 'closed'
            self.system.track_function('save_problem_fail', event_info)
            return {'success': False,
                    'msg': "Problem is closed"}

        # Problem submitted. Student should reset before saving
        # again.
        if self.done and self.rerandomize == "always":
            event_info['failure'] = 'done'
            self.system.track_function('save_problem_fail', event_info)
            return {'success': False,
                    'msg': "Problem needs to be reset prior to save"}

        self.lcp.student_answers = answers

        self.set_state_from_lcp()

        self.system.track_function('save_problem_success', event_info)
        msg = "Your answers have been saved"
        if not self.max_attempts == 0:
            msg += " but not graded. Hit 'Check' to grade them."
        return {'success': True,
                'msg': msg}

    def reset_problem(self, _data):
        """
        Changes problem state to unfinished -- removes student answers,
        and causes problem to rerender itself.

        Returns a dictionary of the form:
          {'success': True/False,
           'html': Problem HTML string }

        If an error occurs, the dictionary will also have an
        `error` key containing an error message.
        """
        event_info = dict()
        event_info['old_state'] = self.lcp.get_state()
        event_info['problem_id'] = self.location.url()

        if self.closed():
            event_info['failure'] = 'closed'
            self.system.track_function('reset_problem_fail', event_info)
            return {'success': False,
                    'error': "Problem is closed"}

        if not self.done:
            event_info['failure'] = 'not_done'
            self.system.track_function('reset_problem_fail', event_info)
            return {'success': False,
                    'error': "Refresh the page and make an attempt before resetting."}

        if self.rerandomize in ["always", "onreset"]:
            # Reset random number generator seed.
            self.choose_new_seed()

        # Generate a new problem with either the previous seed or a new seed
        self.lcp = self.new_lcp(None)

        # Pull in the new problem seed
        self.set_state_from_lcp()

        event_info['new_state'] = self.lcp.get_state()
        self.system.track_function('reset_problem', event_info)

        return {'success': True,
                'html': self.get_problem_html(encapsulate=False)}


class CapaDescriptor(CapaFields, RawDescriptor):
    """
    Module implementing problems in the LON-CAPA format,
    as implemented by capa.capa_problem
    """

    module_class = CapaModule

    has_score = True
    template_dir_name = 'problem'
    mako_template = "widgets/problem-edit.html"
    js = {'coffee': [resource_string(__name__, 'js/src/problem/edit.coffee')]}
    js_module_name = "MarkdownEditingDescriptor"
    css = {
        'scss': [
            resource_string(__name__, 'css/editor/edit.scss'),
            resource_string(__name__, 'css/problem/edit.scss')
        ]
    }

    # Capa modules have some additional metadata:
    # TODO (vshnayder): do problems have any other metadata?  Do they
    # actually use type and points?
    metadata_attributes = RawDescriptor.metadata_attributes + ('type', 'points')

    # The capa format specifies that what we call max_attempts in the code
    # is the attribute `attempts`. This will do that conversion
    metadata_translations = dict(RawDescriptor.metadata_translations)
    metadata_translations['attempts'] = 'max_attempts'

    @classmethod
    def filter_templates(cls, template, course):
        """
        Filter template that contains 'latex' from templates.

        Show them only if use_latex_compiler is set to True in
        course settings.
        """
        return (not 'latex' in template['template_id'] or course.use_latex_compiler)

    def get_context(self):
        _context = RawDescriptor.get_context(self)
        _context.update({
            'markdown': self.markdown,
            'enable_markdown': self.markdown is not None,
            'enable_latex_compiler': self.use_latex_compiler,
        })
        return _context

    # VS[compat]
    # TODO (cpennington): Delete this method once all fall 2012 course are being
    # edited in the cms
    @classmethod
    def backcompat_paths(cls, path):
        return [
            'problems/' + path[8:],
            path[8:],
        ]

    @property
    def non_editable_metadata_fields(self):
        non_editable_fields = super(CapaDescriptor, self).non_editable_metadata_fields
        non_editable_fields.extend([
            CapaDescriptor.due,
            CapaDescriptor.graceperiod,
            CapaDescriptor.force_save_button,
            CapaDescriptor.markdown,
            CapaDescriptor.text_customization,
            CapaDescriptor.use_latex_compiler,
        ])
        return non_editable_fields

    # Proxy to CapaModule for access to any of its attributes
    answer_available = module_attr('answer_available')
    check_button_name = module_attr('check_button_name')
    check_problem = module_attr('check_problem')
    choose_new_seed = module_attr('choose_new_seed')
    closed = module_attr('closed')
    get_answer = module_attr('get_answer')
    get_problem = module_attr('get_problem')
    get_problem_html = module_attr('get_problem_html')
    get_state_for_lcp = module_attr('get_state_for_lcp')
    handle_input_ajax = module_attr('handle_input_ajax')
    handle_problem_html_error = module_attr('handle_problem_html_error')
    handle_ungraded_response = module_attr('handle_ungraded_response')
    is_attempted = module_attr('is_attempted')
    is_correct = module_attr('is_correct')
    is_past_due = module_attr('is_past_due')
    is_submitted = module_attr('is_submitted')
    lcp = module_attr('lcp')
    make_dict_of_responses = module_attr('make_dict_of_responses')
    new_lcp = module_attr('new_lcp')
    publish_grade = module_attr('publish_grade')
    rescore_problem = module_attr('rescore_problem')
    reset_problem = module_attr('reset_problem')
    save_problem = module_attr('save_problem')
    set_state_from_lcp = module_attr('set_state_from_lcp')
    should_show_check_button = module_attr('should_show_check_button')
    should_show_reset_button = module_attr('should_show_reset_button')
    should_show_save_button = module_attr('should_show_save_button')
    update_score = module_attr('update_score')
