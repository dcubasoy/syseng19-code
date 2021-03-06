from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone
from match.models import Cohort,Participant,Programme,Tag
from match.serializers import ParticipantSerializer,UserSerializer
from rest_framework.serializers import ValidationError
from datetime import timedelta
import json

class ParticipantSerializerTests(TestCase):

    def setUp(self):
        user_s = UserSerializer(data={
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Smith',
            'password': 'hunter2',
            'profile': {
                'position': 'Consultant',
                'department': 'HR',
                'dateOfBirth': '2000-11-30',
                'joinDate': '2016-01-03',
                'bio': 'I like people, places and things'
            }
        })
        user_s.is_valid()
        self.user = user_s.save()

        user_s = UserSerializer(data={
            'email': 'test2@example.com',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'password': 'hunter2',
            'profile': {
                'position': 'IT Specialist',
                'department': 'Tech',
                'dateOfBirth': '1990-10-30',
                'joinDate': '2014-01-03',
                'bio': 'I like people, places and things'
            }
        })
        user_s.is_valid()
        self.other_user = user_s.save()

        self.programme = Programme.objects.create(
            name = 'Test Programme',
            description = 'This is a test programme.',
            defaultCohortSize = 100,
            createdBy = self.user)
        self.cohort = Cohort.objects.create(
            programme = self.programme,
            createdBy = self.user,
            cohortSize = self.programme.defaultCohortSize
        )

    def test_serializer_valid_participant(self):
        data = {
            'isMentor': False
        }
        serializer = ParticipantSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        participant = serializer.save(user=self.user, cohort=self.cohort)
        self.assertFalse(participant.isMatched)
        self.assertTrue(participant.signUpDate <= timezone.now())

    def test_serializer_include_existing_tags(self):
        data = {
            'isMentor': True,
            'tags': [
                'node.js',
                'sports'
            ]
        }
        Tag.objects.create(name="node.js")
        Tag.objects.create(name="sports")
        serializer = ParticipantSerializer(data=data)
        if not serializer.is_valid():
            self.fail(serializer.errors)
        participant = serializer.save(user=self.user, cohort=self.cohort)
        self.assertEqual(len(participant.tags.all()), 2)

    def test_serializer_include_nonexisting_tags(self):
        data = {
            'isMentor': True,
            'tags': [
                'node.js',
                'sports',
                'something'
            ]
        }
        Tag.objects.create(name="node.js")
        Tag.objects.create(name="sports")
        serializer = ParticipantSerializer(data=data)
        if not serializer.is_valid():
            self.fail(serializer.errors)
        participant = serializer.save(user=self.user, cohort=self.cohort)
        self.assertEqual(len(participant.tags.all()), 3)

    def test_serializer_ignore_duplicate_tags(self):
        data = {
            'isMentor': True,
            'tags': [
                'node.js',
                'sports',
                'sports'
            ]
        }
        Tag.objects.create(name="node.js")
        Tag.objects.create(name="sports")
        serializer = ParticipantSerializer(data=data)
        if not serializer.is_valid():
            self.fail(serializer.errors)
        participant = serializer.save(user=self.user, cohort=self.cohort)
        self.assertEqual(len(participant.tags.all()), 2)

    def test_serializer_ignore_same_tag_slug(self):
        data = {
            'isMentor': True,
            'tags': [
                'node.js',
                'Node JS',
                'sports',
                'Sports'
            ]
        }
        Tag.objects.create(name="node.js")
        Tag.objects.create(name="sports")
        serializer = ParticipantSerializer(data=data)
        if not serializer.is_valid():
            self.fail(serializer.errors)
        participant = serializer.save(user=self.user, cohort=self.cohort)
        self.assertEqual(len(participant.tags.all()), 2)

    def test_serializer_is_mentor_not_set(self):
        data = {}
        serializer = ParticipantSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_serializer_cant_apply_for_same_cohort_twice(self):
        data = { 'isMentor': True }
        serializer = ParticipantSerializer(data=data)
        serializer.is_valid()
        participant = serializer.save(user=self.user, cohort=self.cohort)

        data = { 'isMentor': False }
        serializer = ParticipantSerializer(data=data)
        serializer.is_valid()
        with self.assertRaises(IntegrityError):
            participant = serializer.save(user=self.user, cohort=self.cohort)

    def test_serializer_cant_apply_for_full_cohort(self):
        smol_programme = Programme.objects.create(
            name = 'Smaller Programme',
            description = 'This is a test programme.',
            defaultCohortSize = 1,
            createdBy = self.user)
        smol_cohort = Cohort.objects.create(
            programme = smol_programme,
            createdBy = self.user,
            cohortSize = smol_programme.defaultCohortSize
        )

        data = { 'isMentor': True }
        serializer = ParticipantSerializer(data=data)
        serializer.is_valid()
        participant = serializer.save(user=self.user, cohort=smol_cohort)

        data = { 'isMentor': False}
        serializer = ParticipantSerializer(data=data)
        serializer.is_valid()
        with self.assertRaises(ValidationError):
            participant = serializer.save(user=self.other_user, cohort=smol_cohort)
