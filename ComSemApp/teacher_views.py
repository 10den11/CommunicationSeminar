from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import View
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView, CreateView, DeleteView

from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Prefetch
from django.http import JsonResponse
from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe
from django.core.serializers import serialize
from django.contrib import messages
from django.conf import settings

from ComSemApp import teacher_constants
from ComSemApp.libs.mixins import RoleViewMixin, CourseViewMixin, WorksheetViewMixin

import json, math, datetime, os
from .models import *


class TeacherViewMixin(RoleViewMixin):

    role_class = Teacher

    def _set_role_obj(self):
        # role_obj self in RoleViewMixin
        self.teacher = self.role_obj

    def _check_valid_course(self, course_id):
        courses = Course.objects.filter(teachers=self.request.user.teacher, id=course_id)
        if not courses.exists():
            return False
        return courses.first()


class TeacherCourseViewMixin(TeacherViewMixin, CourseViewMixin):

    def _get_invalid_course_redirect(self):
        return HttpResponseRedirect(reverse("teacher"))


class TeacherWorksheetViewMixin(TeacherViewMixin, WorksheetViewMixin):

    def _get_invalid_worksheet_redirect(self):
        return HttpResponseRedirect(reverse("teacher_course", kwargs={"course_id": self.course.id}))


class CourseListView(TeacherViewMixin, ListView):
    # teacher home page
    model = Course
    template_name = 'ComSemApp/teacher/course_list.html'
    context_object_name = 'courses'

    def get_queryset(self):
        return Course.objects.filter(teachers=self.request.user.teacher)

    def get_context_data(self, **kwargs):
        context = super(CourseListView, self).get_context_data(**kwargs)
        context['teacher_view'] = True
        return context


class CourseDetailView(TeacherCourseViewMixin, DetailView):
    context_object_name = 'course'
    template_name = "ComSemApp/teacher/course.html"

    def get_object(self):
        return self.course


class WorksheetListView(TeacherCourseViewMixin, ListView):
    model = Worksheet
    template_name = 'ComSemApp/teacher/worksheet_list.html'
    context_object_name = 'worksheets'

    def get_queryset(self):
        return self.course.get_visible_worksheets()


class WorksheetDetailView(TeacherWorksheetViewMixin, DetailView):
    template_name = 'ComSemApp/teacher/view_worksheet.html'
    context_object_name = 'worksheet'

    def get_object(self):
        return self.worksheet


class WorksheetCreateView(TeacherCourseViewMixin, UpdateView):
    model = Worksheet
    fields = ["topic", "display_original", "display_reformulation_text",
                "display_reformulation_audio", "display_all_expressions"]
    template_name = "ComSemApp/teacher/edit_worksheet.html"

    # technically an UpdateView since a worksheet object with status PENDING is created in the get_object method
    def get_object(self):
        worksheet, created = Worksheet.objects.get_or_create_pending(self.teacher, self.course)
        return worksheet

    def form_valid(self, form):
        self.object.status = teacher_constants.WORKSHEET_STATUS_UNRELEASED
        return super(WorksheetCreateView,self).form_valid(form)

    def get_success_url(self):
        return reverse("teacher_course", kwargs={'course_id': self.course.id })


class WorksheetUpdateView(TeacherWorksheetViewMixin, UpdateView):
    model = Worksheet
    fields = ["topic", "display_original", "display_reformulation_text",
                "display_reformulation_audio", "display_all_expressions"]
    template_name = "ComSemApp/teacher/edit_worksheet.html"
    context_object_name = 'worksheet'

    def get_object(self):
        return self.worksheet

    def get_success_url(self):
        return reverse("teacher_course", kwargs={'course_id': self.course.id })


class WorksheetReleaseView(TeacherWorksheetViewMixin, View):
    model = Worksheet

    def get_object(self):
        return get_object_or_404(Worksheet, id=self.worksheet.id)

    def post(self, *args, **kwargs):
        worksheet = self.get_object()
        worksheet.release()
        return HttpResponse(status=204)


class WorksheetDeleteView(TeacherWorksheetViewMixin, DeleteView):
    model = Worksheet

    def get_object(self):
        return get_object_or_404(Worksheet, id=self.worksheet.id, status=teacher_constants.WORKSHEET_STATUS_UNRELEASED)

    def post(self, *args, **kwargs):
        worksheet = self.get_object()
        worksheet.delete()
        return HttpResponse(status=204)


class ExpressionListView(TeacherWorksheetViewMixin, ListView):
    model = Expression
    template_name = "ComSemApp/teacher/expressions.html"
    context_object_name = 'expressions'

    def get_queryset(self):
        return Expression.objects.filter(worksheet=self.worksheet)

    def get_context_data(self, **kwargs):
        context = super(ExpressionListView, self).get_context_data(**kwargs)
        context['course'] = self.course
        context['worksheet'] = self.worksheet
        return context


class ExpressionCreateView(TeacherWorksheetViewMixin, CreateView):
    model = Expression
    template_name = "ComSemApp/teacher/expression_form.html"
    fields = ["expression", "student", "all_do", "pronunciation", "context_vocabulary",
                "reformulation_text", "reformulation_audio"]

    def form_invalid(self, form):
        response = super().form_invalid(form)
        return JsonResponse(form.errors, status=400)

    def form_valid(self, form):
        expression = form.save(commit=False)
        expression.worksheet = self.worksheet
        expression.save()
        if expression.reformulation_audio:
            # TODO - audio_file should really be part of the form and can be merged with reformulation_audio
            audio_file = self.request.FILES.get('audio_file', None)
            if audio_file:
                url = create_file_url("ExpressionReformulations", expression.id)
                handle_uploaded_file(audio_file, url)
        return JsonResponse({}, status=200)


class ExpressionUpdateView(TeacherWorksheetViewMixin, UpdateView):
    model = Expression
    template_name = "ComSemApp/teacher/expression_form.html"
    fields = ["expression", "student", "all_do", "pronunciation", "context_vocabulary",
                "reformulation_text", "reformulation_audio"]

    def get_object(self):
        expression_id = self.kwargs.get('expression_id', None)
        expressions = Expression.objects.filter(id=expression_id, worksheet=self.worksheet)
        if not expressions.exists():
            # only ajax right now
            response = JsonResponse({"error": 'Invalid Expression ID.'})
            response.status_code = 403
            return response
        return expressions.first()

    def form_invalid(self, form):
        response = super().form_invalid(form)
        return JsonResponse(form.errors, status=400)

    def form_valid(self, form):
        expression = form.save()
        if expression.reformulation_audio:
            # TODO - audio_file should really be part of the form and can be merged with reformulation_audio
            audio_file = self.request.FILES.get('audio_file', None)
            if audio_file:
                url = create_file_url("ExpressionReformulations", expression.id)
                handle_uploaded_file(audio_file, url)
        return JsonResponse({}, status=200)


class ExpressionDeleteView(TeacherWorksheetViewMixin, DeleteView):
    model = Expression

    def get_object(self):
        expression_id = self.kwargs.get('expression_id', None)
        expressions = Expression.objects.filter(id=expression_id, worksheet=self.worksheet)
        if not expressions.exists():
            # only ajax right now
            response = JsonResponse({"error": 'Invalid Expression ID.'})
            response.status_code = 403
            return response
        return expressions.first()

    def post(self, *args, **kwargs):
        expression = self.get_object()
        reformulation_audio = expression.reformulation_audio
        # delete audio file if it exists
        if reformulation_audio:
            url = create_file_url("ExpressionReformulations", expression.id)
            delete_file(url)
        expression.delete()
        return HttpResponse(status=204)


class SubmissionView(TeacherWorksheetViewMixin, DetailView):
    template_name = "ComSemApp/teacher/view_submission.html"
    context_object_name = "submission"

    def get_object(self):
        submission_id = self.kwargs.get('submission_id', None)
        return get_object_or_404(StudentSubmission, id=submission_id, worksheet=self.worksheet)

    def post(self, *args, **kwargs):
        submission = self.get_object()
        attempts = submission.studentattempt_set.all()

        all_correct = True
        # status of each attempt
        for attempt in attempts:
            correct = self.request.POST.get(str(attempt.id), None) == '1'
            attempt.correct = correct
            attempt.save()

            if not correct:
                all_correct = False

        # handle status of the submission
        # TODO - use constants
        if all_correct:
            submission.status = 'complete'
        else:
            submission.status = 'incomplete'

        submission.save()

        messages.success(self.request, 'Assessment saved ', 'success')
        return redirect('teacher_worksheet_detail', self.course.id, self.worksheet.id)


# TODO - delete
def jsonify_expressions(expression_queryset):
    expressions = list(expression_queryset.values())

    # need to get name of assigned student seperately
    for i in range(len(expressions)):
        student = expression_queryset[i].student
        expressions[i]['student_name'] = str(student) if student else None
        expressions[i]['reformulation_audio'] = False if expressions[i]['reformulation_audio'] == '0' else True

    return json.dumps(expressions)


def create_file_url(directory, e):
    id_floor = int(math.floor(e/1000))
    url = settings.EFS_DIR
    url += directory + '/' + str(id_floor)
    if not os.path.exists(url):
        os.makedirs(url)
    filename = e - (id_floor * 1000)
    url += '/' + str(filename) + ".ogg"
    return url


def handle_uploaded_file(f, url):
    with open(url, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def delete_file(url):
    os.remove(url)


