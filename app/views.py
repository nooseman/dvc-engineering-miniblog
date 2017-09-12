from flask import redirect, url_for, render_template, flash, \
                  g, request, send_from_directory
from flask_login import login_user, logout_user, current_user, login_required
from app import app, models, db
from app.oauth import OAuthSignIn
from app.models import User, Post
from app.forms import PostForm, DeleteForm, EditForm, AdminForm
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from os import listdir
from os.path import isfile, join

@app.route('/')
@app.route('/home')
@app.route('/home/<int:page>')
def index(page=1):
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(page, app.config['POSTS_PER_PAGE'], False)
    users = [User.query.filter_by(id=post.user_id).first() for post in posts.items]

    image_removed = False

    #verify post images still exist
    for post in posts.items:
        for image in post.images:
            if not os.path.isfile(app.config['UPLOAD_FOLDER'] + image.url):
                post.images.remove(image)
                image_removed = True

        if image_removed:
            db.session.add(post)
            db.session.commit()
   

    return render_template('index.html',
                            posts=posts,
                            userposts=zip(users,posts.items))


@app.route('/post', methods=['GET', 'POST'])
@login_required
def post():
    postform = PostForm()

    recentposts = Post.query.order_by(Post.timestamp.desc()).limit(5).all()
    recentusers = [User.query.filter_by(id=recentpost.user_id).first() for recentpost in recentposts]

    def allowed_file(filename):
        return '.' in filename and ',' not in filename and \
            filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    def unique_filename(filename):
        existing = [f for f in listdir(app.config['UPLOAD_FOLDER']) if isfile(join(app.config['UPLOAD_FOLDER'], f))]
        counter = 1

        while filename in existing:
            filename = filename.rsplit('.', 1)[0] + str(counter) + \
                          '.' + filename.rsplit('.', 1)[1] 
            if filename not in existing:
                break
            counter += 1
        return filename

    if not current_user.approved_to_post:
        flash('You are not approved to add new posts.', 'warning')
        return redirect(url_for('index'))

    if request.method == 'POST':
        if postform.validate_on_submit():
            flash('Your post has been submitted.', 'success')
            post = Post(title=postform.title.data, 
                        body=postform.body.data,
                        timestamp=datetime.now(),
                        user_id=current_user.id)
            current_user.posts.append(post)
            db.session.add(post, current_user)
            db.session.commit()

            if 'image' not in request.files:
                flash('No file part', 'danger')
                return redirect(url_for('index'))

            if request.files.getlist('image'):
                imgs=[]
                for file in request.files.getlist('image'):
                    if file and allowed_file(file.filename):
                        filename = secure_filename(unique_filename(file.filename))
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        img = models.Image(url=filename, post_id=post.id)
                        imgs.append(img)
                        db.session.add(img)

            db.session.commit()

            if imgs is not []:
                post.images = imgs

            return redirect(url_for('index'))

    return render_template('post.html',
                            title="Create A New Post",
                            postform=postform,
                            userposts=zip(recentusers, recentposts))


@app.route('/deletepost/<postid>', methods=['GET', 'POST'])
@login_required
def delete_post(postid):
    deleteform = DeleteForm()
    
    post = Post.query.filter_by(id=postid).first()
    user = User.query.filter_by(id=post.user_id).first()

    if current_user.id is not post.user_id and not current_user.is_administrator:
        flash('You are not authorized to other users\' posts.', 'warning')
        return redirect(url_for('index'))

    if not postid:
        flash('Please select a post to delete.', 'info')
        return redirect(url_for('index'))

    if deleteform.validate_on_submit():
        if deleteform.delete.data == 'Delete ' + postid:
            for img in models.Image.query.filter_by(post_id=postid).all():
                try:
                    os.remove(app.config['UPLOAD_FOLDER'] + img.url)
                except FileNotFoundError:
                    pass

            print('attempting to delete Image')
            models.Image.query.filter_by(post_id=postid).delete()   
            print('Image deleted')        

            models.Post.query.filter_by(id=postid).delete()

            db.session.commit()

            flash('Post deleted.', 'success')
            return redirect(url_for('index'))

    post = models.Post.query.filter_by(id=postid).first()
    return render_template('deletepost.html',
                            post=post,
                            user=user,
                            deleteform=deleteform)


@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first()
    if user == None:
        flash('Unable to find %s.' % username, 'danger')
        return redirect(url_for('index'))

    uposts = Post.query.filter_by(user_id=user.id).all()

    return render_template('user.html',
                            user=user,
                            uposts=uposts)


@app.route('/edit', methods=['GET','POST'])
@login_required
def edit():
    editform = EditForm()

    if editform.validate_on_submit():
        current_user.biography = editform.biography.data

        if editform.nickname.data is not '':
            current_user.nickname = editform.nickname.data

        db.session.add(current_user)
        db.session.commit()

        flash('Your changes have been saved.')
        return redirect(url_for('user', username=current_user.username))

    return render_template('edit.html',
                            editform=editform)


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_administrator:
        flash('You are not allowed to access this page.' , 'warning')
        return redirect(url_for('index'))

    adminform = AdminForm()
    approved_users = User.query.filter_by(approved_to_post=True, is_administrator=False).all()

    if adminform.validate_on_submit():
        approved_emails = adminform.approveemail.data
        disapproved_emails = adminform.disapproveemail.data

        if approved_emails:
            approved_emails = approved_emails.split(',')

            for email in approved_emails:
                user = User.query.filter_by(email=email, is_administrator=False).first()

                if not user:
                    flash('Could not find user with email ' + email + '.' , 'danger')
                    continue

                user.approved_to_post = True
                flash('Added post approval for ' + user.nickname + '.', 'success')
                db.session.add(user)

            db.session.commit()


        if disapproved_emails:
            disapproved_emails = disapproved_emails.split(',')

            for email in disapproved_emails:
                user = User.query.filter_by(email=email, is_administrator=False).first()
                if not user:
                    flash('Could not find user with email ' + email + '.' , 'danger')
                    continue

                user.approved_to_post = False
                flash('Removed post approval for ' + user.nickname + '.', 'success')
                db.session.add(user)

            db.session.commit()

    return render_template('admin.html',
                            adminform=adminform,
                            approved_users=approved_users)

@app.route('/login')
def login():
    if current_user.is_authenticated:
        flash('You\'re already logged in!')
        return redirect(url_for('index'))
    else:
        return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    flash('You\'ve been logged out.')
    return redirect(url_for('index'))


@app.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()


@app.route('/callback/<provider>')
def oauth_callback(provider):

    def check_user_privileges(user):
        administrators = [line.strip() for line in open(app.config['ADMINS_FILE'])]

        approved_users = User.query.filter_by(approved_to_post=True).all()
        approved_to_post = False
        for poster in approved_users:
            if poster.email == user.email:
                approved_to_post = True
                break

        return (user.email in administrators, 
                user.email in administrators or approved_to_post)

    if not current_user.is_anonymous:
        return redirect(url_for('index'))

    oauth = OAuthSignIn.get_provider(provider)
    social_id, username, email, auth_provider, profile_picture_url = oauth.callback()
    user = User.query.filter_by(social_id=social_id).first()

    if social_id is None:
        flash('Authentication failed.', 'danger')
        return redirect(url_for('index'))
    if not user:
        uname = User.make_unique_nickname(username)
        user = User(social_id=social_id, nickname=username,
                    username=uname, email=email,
                    auth_provider=auth_provider,
                    profile_picture_url=profile_picture_url)

    #check if user's privileges have updated
    user.is_administrator, user.approved_to_post = check_user_privileges(user)
    
    db.session.add(user)
    db.session.commit()

    login_user(user, True)
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.errorhandler(401)
def unauthorized_error(error):
    return render_template('401.html'), 401
