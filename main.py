# Import the appropriate modules to project. The requirements.txt file should have all the latest versions installed.
from flask import Flask, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
from flask import abort


# Create the app object utilizing flask.
app = Flask(__name__)
# Configure the app with a secret key.
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
# Create object from CKEditor with the input of the app.
ckeditor = CKEditor(app)
# Apply the bootstrap template to the app.
Bootstrap(app)

# Apply gravatar to app.
gravatar = Gravatar(
    app,
    size=100,
    rating="g",
    default="retro",
    force_default=False,
    force_lower=False,
    use_ssl=False,
    base_url=None
)

# Configure the app settings to utilize SQLAlchemy.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Create a database object utilizing SQLAlchemy and connect to it.
db = SQLAlchemy(app)

# Create a Login Manager object so that certain pages require a login, and it keeps users logged in.
login_manager = LoginManager()
# Initiate the login manager for the app.
login_manager.init_app(app)


# Allow the app and login manager to work together. User_id allows to display unique data for each user at a website.
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Create a table in the database for the users.
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    # Add parent relationship to comments.
    comments = relationship("Comment", back_populates="comment_author")


# Create a class that creates and configures a table for the database with the appropriate columns.
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts property in the User class.
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    # Parent Relationship
    comments = relationship("Comment", back_populates="parent_post")


# Create table for comments.
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    # Child relationship
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    # Add child relationship to user table.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    parent_post = relationship("BlogPost", back_populates="comments")
    text = db.Column(db.Text, nullable=False)


# Commented out after the first run as the database and table have already been created.
# Utilize app.app_context to create the tables in the database.
with app.app_context():
    db.create_all()


# Create admin only decorator so that only the user with ID equal to 1 can access edit and create pages.
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If ID is not equal to 1 then return abort with 403 error.
        if current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function.
        return f(*args, **kwargs)
    return decorated_function


# Route to home page.
@app.route('/')
def get_all_posts():
    # Create JSON (Dictionary) for all blog posts. This will be displayed over HTML as a for loop.
    posts = BlogPost.query.all()
    # Render the index page and inputting posts and current_user variable.
    return render_template("index.html", all_posts=posts, current_user=current_user)


# Route to "register" page and to register new users.
@app.route('/register', methods=["GET", "POST"])
def register():
    # Create a new form from the Register Form Class imported from forms.py.
    form = RegisterForm()
    # If the submit button is pushed then the password input will be hashed/salted and a new user will be created.
    if form.validate_on_submit():

        # Check to see if the users inputted email address is already in the database and redirect them to login page.
        if User.query.filter_by(email=form.email.data).first():
            # Send flash message notifying user that email is already in use and to sign in instead.
            flash(
                message="You've already signed up with that email, log in instead."
            )
            # Redirect the user to the login page.
            return redirect(url_for("login"))

        # Hash and salt the password given by the user.
        hash_salted_pw = generate_password_hash(
            form.password.data,
            method="pbkdf2:sha256",
            salt_length=8
        )
        # Create new user object.
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_salted_pw,
        )
        # Add the new user to the database table for users.
        db.session.add(new_user)
        # Commit the changes to the user table.
        db.session.commit()
        # Authenticate the user with Flask-Login
        login_user(new_user)
        # Redirect the user to the home page after registering.
        return redirect(url_for("get_all_posts"))
    # Render the register page and input the form and current_user as a variable into the HTML page.
    return render_template("register.html", form=form, current_user=current_user)


# Route to "login" page.
@app.route('/login', methods=["GET", "POST"])
def login():
    # Create form from the class for login forms.
    form = LoginForm()
    # If the user clicks on the submit button the info from the forms will be inputted and verified to log in.
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        # Set a user variable based on the email inputted by user.
        user = User.query.filter_by(email=email).first()
        # Check that the email inputted into the form matches an email in the database. If not, then redirect to log in.
        if not user:
            # Flash the user a message to let them know email was incorrect.
            flash(message="That email does not exist, please try again.")
            # Redirect to login page for the user to try again.
            return redirect(url_for("login"))
        # Confirm password inputted (salted and hashed) matches the hashed password in the email database.
        elif not check_password_hash(pwhash=user.password, password=password):
            flash(message="Password incorrect, please try again.")
        # The else statement means the login was correct. Login user and redirect to home page logged in.
            login_user(user)
            # Redirect user back to home page.
            return redirect(url_for("get_all_posts"))
    # Render the login page and input the form for logging into the HTML.
    return render_template("login.html", form=form, current_user=current_user)


# Route to the "logout" page.
@app.route('/logout')
def logout():
    logout_user()
    # Redirects the user back to the home page.
    return redirect(url_for('get_all_posts'))


# Route to the post page with the appropriate ID.
@app.route("/post/<int:post_id>")
# This function takes an input of "post_id".
def show_post(post_id):
    # Add form object from comment form class.
    comment_form = CommentForm()
    # Create variable that is a dictionary of the requested post based on the "post_id" input.
    requested_post = BlogPost.query.get(post_id)
    # If the submit button is clicked will authenticate user and let them know if they need to register.
    if comment_form.validate_on_submit():
        flash("You need to login or register to comment.")
        # Redirect user to login page.
        return redirect(url_for("login"))
    # Create object from Comment form.
    new_comment = Comment(
        text=comment_form.comment_text.data,
        comment_author=current_user,
        parent_post=requested_post
    )
    # Add new comment to post and commit.
    db.session.add(new_comment)
    db.session.commit()
    # Render the post page with a variable of "post" for the HTML page.
    return render_template("post.html", post=requested_post, current_user=current_user, form=comment_form)


# Route to the about page.
@app.route("/about")
def about():
    # Render the about page.
    return render_template("about.html", current_user=current_user)


# Route to the contact page.
@app.route("/contact")
def contact():
    # Render the contact page.
    return render_template("contact.html", current_user=current_user)


# Route to a new post page.
@app.route("/new-post", methods=["GET", "POST"])
# Mark with decorator for admin only access.
@admin_only
def add_new_post():
    # Create a form object from the CreatePostForm Class. This class is imported from the form.py.
    form = CreatePostForm()
    # If the submit button is clicked on the form then the following script shall be executed.
    if form.validate_on_submit():
        # Creates a dictionary which "GET"s the information from the form and creates a new table from the Class.
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        # Add the dictionary variable to the existing database table.
        db.session.add(new_post)
        # Commits the changes to the database table.
        db.session.commit()
        # Will then redirect the user to the home page.
        return redirect(url_for("get_all_posts"))
    # Initial routing will take the user to the new post page and will input the form into the HTML page.
    return render_template("make-post.html", form=form, current_user=current_user)


# Route to the edit post page. This will take the "post_id" input from the function.
@app.route("/edit-post/<int:post_id>")
# Mark with decorator for admin only access.
@admin_only
def edit_post(post_id):
    # Create a dictionary object from the Class based on the "post_id" specified.
    post = BlogPost.query.get(post_id)
    # Create a form from the class and input the data from the "post_id" so that the user can see what they are editing.
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    # If the submit button is pushed, the information in the form is submitted as a change to the database.
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        # Commit the changes to the database.
        db.session.commit()
        # Redirect to the "show_post" page with the "post_id" as an input into the HTML.
        return redirect(url_for("show_post", post_id=post.id))
    # Render the make-post page when initially routed with form variable into the HTML page.
    return render_template("make-post.html", form=edit_form, current_user=current_user)


# Route to the delete post with the input "post_id".
@app.route("/delete/<int:post_id>")
# Mark with decorator for admin only access.
@admin_only
def delete_post(post_id):
    # Create an object of the post_id specified utilizing the BlogPost Class.
    post_to_delete = BlogPost.query.get(post_id)
    # Delete the specified blog post from the post_id from the database.
    db.session.delete(post_to_delete)
    # Commit the changes to the database.
    db.session.commit()
    # Redirect to the home page once the script has been completed.
    return redirect(url_for('get_all_posts'))


# Run the app.
if __name__ == "__main__":
    app.run(debug=True)
