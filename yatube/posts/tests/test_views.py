import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Follow, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


class PostPagesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_user')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(
            title='Тест',
            slug='12',
        )
        self.post = Post.objects.create(
            text='Тестовый текст',
            author=self.user,
            group=self.group,
        )
        self.form_data = {
            'text': self.post.text,
            'group': self.group.id,
        }
        self.new_post = self.authorized_client.post(
            reverse('posts:post_create'),
            data=self.form_data,
            follow=True
        )

    def test_pages_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username':
                            self.user.username}): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id':
                            self.post.pk}): 'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id':
                            self.post.pk}): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_context_index(self):
        """Проверка контекста домашней страницы index"""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context.get('page_obj')[settings.ZERO_VALUE]
        self.assertEqual(
            first_object.group.title, self.post.group.title, 'Ошибка Title'
        )
        self.assertEqual(first_object.text, self.post.text, 'Ошибка Text')
        self.assertEqual(
            first_object.author, self.post.author, 'Ошибка Author'
        )

    def test_context_post_create(self):
        """Проверка контекста для post_create."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'group': forms.fields.ChoiceField,
            'text': forms.fields.CharField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_context_post_edit(self):
        """Проверка контекста для post_edit."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id},
            ))
        form_fields = {
            'group': forms.fields.ChoiceField,
            'text': forms.fields.CharField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        test_is_edit = response.context['is_edit']
        self.assertTrue(test_is_edit)

    def test_profile_contains_list_of_posts(self):
        """profile содержит посты, отфильтрованные по пользователю."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}
            ))

        for post_example in response.context.get('page_obj'):
            with self.subTest():
                self.assertIsInstance(post_example, Post)
                self.assertEqual(post_example.author, self.user)
        self.assertEqual(response.context['author'], self.user)

    def test_group_contains_list_of_posts(self):
        """group_list содержит посты, отфильтрованные по группе."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug},
            ))
        for post_example in response.context.get('page_obj'):
            with self.subTest():
                self.assertIsInstance(post_example, Post)
                self.assertEqual(post_example.group, self.group)
        self.assertEqual(response.context['group'], self.group)


class PaginatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовая группа',
        )
        cls.post = settings.LIMIT + settings.POST_NUMBER
        for cls.post in range(settings.LIMIT + settings.POST_NUMBER):
            cls.post = Post.objects.create(
                text='Тестовый текст',
                author=cls.user,
                group=cls.group
            )

    def test_firsten_records(self):
        """Проверка паджинатора 10 постов на 1 странице."""
        pages = [
            reverse('posts:index'),
            reverse('posts:group_list',
                    kwargs={'slug': PaginatorTests.group.slug}
                    ),
            reverse('posts:profile',
                    kwargs={'username': PaginatorTests.user.username}
                    )
        ]
        for page in pages:
            with self.subTest(page=page):
                response = self.client.get(page)
                self.assertEqual(
                    len(response.context['page_obj']), settings.LIMIT
                )

    def test_last_page_contains_three_records(self):
        """Проверка паджинатора 3 постов на странице 2."""
        pages = [
            reverse('posts:index'),
            reverse('posts:group_list',
                    kwargs={'slug': PaginatorTests.group.slug}
                    ),
            reverse('posts:profile',
                    kwargs={'username': PaginatorTests.user.username}
                    )
        ]
        for page in pages:
            with self.subTest(page=page):
                response = self.client.get(page + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']), settings.POST_NUMBER
                )


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostImageExistTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовый тайтл',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.user)

    def test_post_with_image_exist(self):
        """Проверка, что пост с изображением существует."""
        self.assertTrue(Post.objects.filter(image='posts/small.gif'))

    def test_index_show_correct_image_in_context(self):
        """Проверка изображения в context на главную страницу."""
        response = self.author_client.get(reverse('posts:index'))
        test_object = response.context['page_obj'][settings.ZERO_VALUE]
        post_image = test_object.image
        self.assertEqual(post_image, 'posts/small.gif')

    def test_post_detail_image_exist(self):
        """Проверка изображения в context на страницу поста."""
        response = self.author_client.get(
            reverse('posts:post_detail', args=[self.post.id])
        )
        test_object = response.context['post']
        post_image = test_object.image
        self.assertEqual(post_image, 'posts/small.gif')

    def test_group_and_profile_image_exist(self):
        """Проверка изображения в context на страницу группы и профайла."""
        templates_pages_name = {
            'posts:group_list': self.group.slug,
            'posts:profile': self.user.username,
        }
        for names, args in templates_pages_name.items():
            with self.subTest(names=names):
                response = self.author_client.get(reverse(names, args=[args]))
                test_object = response.context['page_obj'][settings.ZERO_VALUE]
                post_image = test_object.image
                self.assertEqual(post_image, 'posts/small.gif')


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.follower = User.objects.create_user(username='follower')
        cls.follower_client = Client()
        cls.follower_client.force_login(cls.follower)
        cls.author = User.objects.create_user(username='author')
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый текст',
        )

    def setUp(self):
        self.follow = Follow.objects.get_or_create(
            user=self.follower,
            author=self.author
        )

    def test_user_can_follow(self):
        """Проверка возможности подписаться."""
        self.follower_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.author.username}))
        count_before_follow = Follow.objects.count()
        self.follower_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.author.username}))
        count_after_follow = Follow.objects.count()
        self.assertNotEqual(count_before_follow, count_after_follow)
        self.assertTrue(
            Follow.objects.filter(
                user=self.follower,
                author=self.author
            ).exists()
        )

    def test_user_can_unfollow(self):
        """Проверка возможности отписаться."""
        count_before_unfollow = Follow.objects.count()
        self.follower_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.author.username}))
        count_after_unfollow = Follow.objects.count()
        self.assertNotEqual(count_before_unfollow, count_after_unfollow)
        self.assertFalse(
            Follow.objects.filter(
                user=self.follower,
                author=self.author
            ).exists()
        )

    def test_follow_unique_constrait(self):
        """Проверяем, что нельзя дважды подписаться на одного автора."""
        with self.assertRaises(
            IntegrityError,
        ) as context:
            Follow(
                user=self.follower,
                author=self.author
            ).save()
            Follow(
                user=self.follower,
                author=self.author
            ).save()
        self.assertTrue('UNIQUE constraint failed' in str(context.exception))

    def test_follow_equal_constrait(self):
        """Проверяем, что нельзя подписаться на самого себя."""
        with self.assertRaises(
            IntegrityError,
        ) as context:
            Follow(
                user=self.follower,
                author=self.follower
            ).save()
        self.assertTrue('CHECK constraint failed' in str(context.exception))

    def test_follow_index_context(self):
        """Пост автора появляется в ленте у подписчика."""
        response = self.follower_client.get(reverse('posts:follow_index'))
        first_object = response.context['page_obj'][settings.ZERO_VALUE]
        post_author_0 = first_object.author.username
        self.assertEqual = (post_author_0, 'author')
        post_text_0 = first_object.text
        self.assertEqual = (post_text_0, 'Тестовый текст')

    def test_follow_index_context_no_author(self):
        """Пост автора не появляется в ленте у чужого подписчика."""
        Follow.objects.filter(
            user=self.follower.is_authenticated, author=self.author,
        ).delete()
        response = self.follower_client.get(reverse('posts:follow_index'))
        self.assertEqual = (
            len(response.context['page_obj']),
            settings.ZERO_VALUE
        )


class CommentTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.commentator = User.objects.create_user(username='commentator')
        cls.commentator_client = Client()
        cls.commentator_client.force_login(cls.commentator)
        cls.post = Post.objects.create(
            text='Тестовый текст поста',
            author=cls.author
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.commentator,
            text='Тестовый текст комментария'
        )

    def test_comment_context(self):
        """Проверка перадачи context у комментария."""
        response = self.commentator_client.get(
            reverse('posts:post_detail', args=[self.post.id]))
        comments = response.context['comments'][settings.ZERO_VALUE]
        expected_fields = {
            comments.author.username: 'commentator',
            comments.post.id: self.post.id,
            comments.text: 'Тестовый текст комментария'
        }
        for fields, values in expected_fields.items():
            with self.subTest(expected_fields=expected_fields):
                self.assertEqual(fields, values)


class CacheTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.author_client = Client()
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый текст',
        )

    def test_caching(self):
        """Тестирование кеша главной страницы."""
        cache.clear()
        response = self.author_client.get(reverse('posts:index'))
        posts_count = Post.objects.count()
        self.post.delete
        self.assertEqual(len(response.context['page_obj']), posts_count)
        cache.clear()
        posts_count = Post.objects.count()
        self.assertEqual(len(response.context['page_obj']), posts_count)
