"""
Unit tests for getting the list of courses for a user through iterating all courses and
by reversing group name formats.
"""
from django.contrib.auth.models import Group
from django.http import HttpRequest

from contentstore.views.course import _accessible_courses_list, _accessible_courses_list_from_groups
from contentstore.tests.utils import AjaxEnabledTestClient
from courseware.tests.factories import UserFactory
from student.roles import CourseInstructorRole, CourseStaffRole
from xmodule.modulestore import Location
from xmodule.modulestore.django import loc_mapper
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory

GROUP_NAME_WITH_DOTS = u'group_name_with_dots'
GROUP_NAME_WITH_SLASHES = u'group_name_with_slashes'
GROUP_NAME_WITH_COURSE_NAME_ONLY = u'group_name_with_course_name_only'


class TestCourseListing(ModuleStoreTestCase):
    """
    Unit tests for getting the list of courses for a logged in user
    """
    def setUp(self):
        """
        Add a user and a course
        """
        super(TestCourseListing, self).setUp()
        # create and log in a staff user.
        self.user = UserFactory(is_staff=True)  # pylint: disable=no-member
        self.request = HttpRequest()
        self.request.user = self.user
        self.client = AjaxEnabledTestClient()
        self.client.login(username=self.user.username, password='test')

        # create a course via the view handler to create course groups with new format e.g. 'edX.Course.Run'
        self.course_location = Location(['i4x', 'Org_1', 'Course_1', 'course', 'Run_1'])
        self.course_locator = loc_mapper().translate_location(
            self.course_location.course_id, self.course_location, False, True
        )
        self.client.ajax_post(
            self.course_locator.url_reverse('course'),
            {
                'org': self.course_location.org,
                'number': self.course_location.course,
                'display_name': 'test course',
                'run': self.course_location.name,
            }
        )

    def _create_course_with_access_groups(self, course_location, group_name_format=GROUP_NAME_WITH_DOTS):
        """
        Create dummy course with 'CourseFactory' and role (instructor/staff) groups with provided group_name_format
        """
        course_locator = loc_mapper().translate_location(
            course_location.course_id, course_location, False, True
        )
        course = CourseFactory.create(
            org=course_location.org,
            number=course_location.course,
            display_name=course_location.name
        )

        for role in [CourseInstructorRole, CourseStaffRole]:
            # pylint: disable=protected-access
            groupnames = role(course_locator)._group_names
            if group_name_format == GROUP_NAME_WITH_COURSE_NAME_ONLY:
                # Create role (instructor/staff) groups with course_name only: 'instructor_run'
                group, _ = Group.objects.get_or_create(name=groupnames[2])
            elif group_name_format == GROUP_NAME_WITH_SLASHES:
                # Create role (instructor/staff) groups with format: 'instructor_edX/Course/Run'
                # Since "Group.objects.get_or_create(name=groupnames[1])" would have made group with lowercase name
                # so manually create group name of old type
                if role == CourseInstructorRole:
                    group, _ = Group.objects.get_or_create(name=u'{}_{}'.format('instructor', course_location.course_id))
                else:
                    group, _ = Group.objects.get_or_create(name=u'{}_{}'.format('staff', course_location.course_id))
            else:
                # Create role (instructor/staff) groups with format: 'instructor_edx.course.run'
                group, _ = Group.objects.get_or_create(name=groupnames[0])

            self.user.groups.add(group)
        return course

    def tearDown(self):
        """
        Reverse the setup
        """
        self.client.logout()
        ModuleStoreTestCase.tearDown(self)

    def test_get_course_list(self):
        """
        Test getting courses with new access group format e.g. 'instructor_edx.course.run'
        """
        # get courses through iterating all courses
        courses_list = _accessible_courses_list(self.request)
        self.assertEqual(len(courses_list), 1)

        # get courses by reversing group name formats
        success, courses_list_by_groups = _accessible_courses_list_from_groups(self.request)
        if success:
            self.assertEqual(len(courses_list_by_groups), 1)
            # check both course lists have same courses
            self.assertEqual(courses_list, courses_list_by_groups)

    def test_get_course_list_with_old_group_formats(self):
        """
        Test getting all courses with old course role (instructor/staff) groups
        """
        # create a new course with old group name format e.g. 'instructor_edX/Course/Run'
        old_course_location = Location(['i4x', 'Org_2', 'Course_2', 'course', 'Run_2'])
        self._create_course_with_access_groups(old_course_location, GROUP_NAME_WITH_SLASHES)

        # get courses through iterating all courses
        courses_list = _accessible_courses_list(self.request)
        self.assertEqual(len(courses_list), 2)

        # get courses by reversing group name formats
        success, courses_list_by_groups = _accessible_courses_list_from_groups(self.request)
        self.assertTrue(success)
        self.assertEqual(len(courses_list_by_groups), 2)

        # create a new course with older group name format (with dots in names) e.g. 'instructor_edX/Course.name/Run.1'
        old_course_location = Location(['i4x', 'Org.Foo.Bar', 'Course.number', 'course', 'Run.name'])
        self._create_course_with_access_groups(old_course_location, GROUP_NAME_WITH_SLASHES)
        # get courses through iterating all courses
        courses_list = _accessible_courses_list(self.request)
        self.assertEqual(len(courses_list), 3)
        # get courses by reversing group name formats
        success, courses_list_by_groups = _accessible_courses_list_from_groups(self.request)
        self.assertTrue(success)
        self.assertEqual(len(courses_list_by_groups), 3)

        # create a new course with older group name format e.g. 'instructor_Run'
        old_course_location = Location(['i4x', 'Org_3', 'Course_3', 'course', 'Run_3'])
        self._create_course_with_access_groups(old_course_location, GROUP_NAME_WITH_COURSE_NAME_ONLY)

        # get courses through iterating all courses
        courses_list = _accessible_courses_list(self.request)
        self.assertEqual(len(courses_list), 4)

        # get courses by reversing group name formats
        success, courses_list_by_groups = _accessible_courses_list_from_groups(self.request)
        # check that getting course with this older format of access group fails for this format
        self.assertFalse(success)
        self.assertEqual(courses_list_by_groups, [])
