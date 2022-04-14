from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required

from .models import Group, Post, User, Follow
from .forms import CommentForm, PostForm
from .page_separation import get_page_obj


def index(request):
    posts = Post.objects.select_related(
        'author',
        'group'
    )
    template = 'posts/index.html'
    page_number = request.GET.get('page')
    page_obj = get_page_obj(posts, page_number)
    context = {
        'posts': posts,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('author')
    page_number = request.GET.get('page')
    page_obj = get_page_obj(posts, page_number)
    template = 'posts/group_list.html'
    context = {
        'group': group,
        'posts': posts,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.select_related('group')
    posts_count = posts.count()
    page_number = request.GET.get('page')
    page_obj = get_page_obj(posts, page_number)
    template = 'posts/profile.html'
    following = (request.user != author
                 and request.user.is_authenticated
                 and Follow.objects.filter(
                     user=request.user,
                     author=author
                 ).exists())
    context = {
        'author': author,
        'page_obj': page_obj,
        'posts_count': posts_count,
        'following': following,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    author_posts_count = post.author.posts.count()
    template = 'posts/post_detail.html'
    comments = post.comments.all()
    form = CommentForm()
    following = (request.user != post.author
                 and request.user.is_authenticated
                 and Follow.objects.filter(
                     user=request.user,
                     author=post.author
                 ).exists())
    context = {
        'post': post,
        'post_id': post_id,
        'author_posts_count': author_posts_count,
        'form': form,
        'comments': comments,
        'following': following,
        'author': post.author,
    }
    return render(request, template, context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'
    form = PostForm(request.POST or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', username=request.user.username)
    return render(request, template, {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    template = 'posts/create_post.html'
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post.pk)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post)
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post.pk)
    context = {
        'form': form,
        'post': post,
        'is_edit': True,
    }
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    template = 'posts:post_detail'
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect(template, post_id=post_id)


@login_required
def follow_index(request):
    username = request.user
    posts = Post.objects.filter(author__following__user=username)
    page_number = request.GET.get('page')
    page_obj = get_page_obj(posts, page_number)
    template = 'posts/follow.html'
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if username != request.user.username:
        # author = get_object_or_404(User, username=username)
        Follow.objects.get_or_create(
            user=request.user,
            author=author
        )
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    get_object_or_404(
        Follow,
        user=request.user,
        author__username=username
    ).delete()
    return redirect('posts:profile', username=username)
