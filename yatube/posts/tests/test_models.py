from django.conf import settings
from django.test import Client, TestCase

from posts.models import Comment, Follow, Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client()
        cls.user = User.objects.create_user(username='test_user')
        cls.client.force_login(cls.user)
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user
        )

    def test_verbose_name_post(self):
        """verbose_name в полях совпадает с ожидаемым."""
        post = self.post
        field_verboses = {
            'text': 'Текст поста',
            'pub_date': 'Дата публикации',
            'author': 'Автор',
            'group': 'Группа',
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                self.assertEqual(
                    post._meta.get_field(value).verbose_name, expected
                )

    def test_help_text_post(self):
        """help_text в полях совпадает с ожидаемым."""
        post = self.post
        field_help_texts = {
            'text': 'Текст нового поста',
            'group': 'Группа, к которой будет относиться пост',
        }
        for value, expected in field_help_texts.items():
            with self.subTest(value=value):
                self.assertEqual(
                    post._meta.get_field(value).help_text, expected
                )

    def test_str_post(self):
        """правильно ли отображается значение поля __str__ ."""
        post = PostModelTest.post
        self.assertEqual(str(post.text), post.text[:settings.TEST_POST])


class GroupModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            description='Тестовое описание',
            slug='Ссылка',
        )

    def test_verbose_name_group(self):
        """verbose_name в полях совпадает с ожидаемым."""
        group = self.group
        field_verboses = {
            'title': 'Заголовок',
            'slug': 'Адрес',
            'description': 'Описание',
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                self.assertEqual(
                    group._meta.get_field(value).verbose_name, expected
                )

    def test_str_group(self):
        """правильно ли отображается значение поля __str__ ."""
        group = GroupModelTest.group
        self.assertEqual(str(group.title), self.group.title)


class CommentModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый текст комментария',
        )

    def test_str_comment(self):
        """правильно ли отображается значение поля __str__ ."""
        comment = CommentModelTest.comment
        expected_text = comment.text[:25]
        self.assertEqual(str(comment), expected_text)

    def test_verbose_name_comment(self):
        """verbose_name в полях совпадает с ожидаемым."""
        comment = self.comment
        field_verboses = {
            'text': 'Текст комментария',
            'pub_date': 'Дата публикации',
            'author': 'Автор',
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                self.assertEqual(
                    comment._meta.get_field(value).verbose_name, expected
                )


class FollowModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.author = User.objects.create_user(username='Author')
        cls.follow = Follow.objects.create(author=cls.author, user=cls.user)

    def test_str_follow(self):
        """правильно ли отображается значение поля __str__ ."""
        follow = FollowModelTest.follow
        expected_text = f'{self.user} подписан на {self.author}'
        self.assertEqual(str(follow), expected_text)

    def test_verbose_name_follow(self):
        """verbose_name в полях совпадает с ожидаемым."""
        follow = self.follow
        field_verboses = {
            'user': 'Подписчик',
            'author': 'Автор записей',
        }
        for value, expected in field_verboses.items():
            with self.subTest(value=value):
                self.assertEqual(
                    follow._meta.get_field(value).verbose_name, expected
                )
