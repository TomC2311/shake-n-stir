import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

cloudinary.config(
    cloud_name=os.environ.get('CLOUD_NAME'),
    api_key=os.environ.get('API_KEY'),
    api_secret=os.environ.get('API_SECRET')
)

mongo = PyMongo(app)


# main home page
@app.route("/")
@app.route("/index")
def index():
    cocktails = list(
        mongo.db.cocktails.find({"created_by": "admin"}).limit(3))
    return render_template("index.html", cocktails=cocktails)


# main cocktail page
@app.route("/view_cocktails")
def view_cocktails():
    cocktails = list(mongo.db.cocktails.find())
    return render_template("cocktails.html", cocktails=cocktails)


# search functionality
@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    cocktails = list(mongo.db.cocktails.find({"$text": {"$search": query}}))
    return render_template("cocktails.html", cocktails=cocktails)


# register user functionality
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if username already exists in the database
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists. Please choose another username.")
            return redirect(url_for('register'))

        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        # prevents user from creating account if passwords do not match
        if password != confirm_password:
            flash("Please ensure that your passwords match.")
            return redirect(url_for("register"))
        # if passwords match account will be created
        if password == confirm_password:
            register = {
                "username": request.form.get("username").lower(),
                "password": generate_password_hash(
                    request.form.get("password"))
                    }
        mongo.db.users.insert_one(register)

        # put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("Registration Successful!")
        return redirect(url_for('profile', username=session["user"]))
    return render_template("register.html")


# login functionality
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                existing_user["password"], request.form.get(
                    "password")):
                session["user"] = request.form.get("username").lower()
                flash("Welcome, {}".format(request.form.get("username")))
                return redirect(
                        url_for('profile', username=session["user"]))
            else:
                # incorrect password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # username doesn't exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


# user profile
@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    # redirects non-users to login if attempted to go to a user's profile
    if session.get("user") is None:
        return redirect(url_for("login"))
    # grabs the session user's username from the database
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    cocktails = mongo.db.cocktails.find({'created_by': session['user']})
    if session["user"]:
        return render_template(
            "profile.html", username=username, cocktails=cocktails)

    return redirect(url_for("login"))


# logs user out of profile
@app.route("/logout")
def logout():
    # remove user from session cookies to allow for logout
    flash("You have successfully logged out!")
    session.pop("user")
    return redirect(url_for("login"))


# deletes users profile
@app.route("/delete_profile/<username>")
def delete_profile(username):
    mongo.db.users.remove({"username": username.lower()})
    flash("Profile Successfuly Deleted")
    session.pop("user")
    return redirect(url_for('index'))


# individual cocktail page
@app.route("/cocktail/<cocktail_id>")
def view_cocktail(cocktail_id):
    cocktail = mongo.db.cocktails.find_one({"_id": ObjectId(cocktail_id)})

    return render_template(
        "cocktail.html", cocktail=cocktail)


# functionality to add new cocktail to db
@app.route("/add_cocktail", methods=["GET", "POST"])
def add_cocktail():
    # checks to see if user is logged before allowing to add cocktail
    if session.get("user") is None:
        return render_template("login.html")

    if request.method == "POST":
        cocktail = {
            "category_name": request.form.get("category_name"),
            "cocktail_name": request.form.get("cocktail_name"),
            "cocktail_description": request.form.get("cocktail_description"),
            "cocktail_ingredients": request.form.get("cocktail_ingredients"),
            "cocktail_instructions": request.form.get("cocktail_instructions"),
            "cocktail_serving": request.form.get("cocktail_serving"),
            "created_by": session["user"],
            "cocktail_img": request.form.get("cocktail_img")
        }
        mongo.db.cocktails.insert_one(cocktail)
        flash("Cocktail Successfully Added")
        return redirect(url_for('view_cocktails'))

    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template("add_cocktail.html", categories=categories)


# functionality to edit cocktails in db
@app.route("/edit_cocktail/<cocktail_id>", methods=["GET", "POST"])
def edit_cocktail(cocktail_id):

    cocktail = mongo.db.cocktails.find_one({"_id": ObjectId(cocktail_id)})
    categories = mongo.db.categories.find().sort("category_name", 1)

    # prevents non-user from editing cocktails
    if session.get("user") is None:
        return render_template("login.html")

    if request.method == "POST":
        submit = {
            "category_name": request.form.get("category_name"),
            "cocktail_name": request.form.get("cocktail_name"),
            "cocktail_description": request.form.get("cocktail_description"),
            "cocktail_ingredients": request.form.get("cocktail_ingredients"),
            "cocktail_instructions": request.form.get("cocktail_instructions"),
            "cocktail_serving": request.form.get("cocktail_serving"),
            "created_by": session["user"],
            "cocktail_img": request.form.get("cocktail_img")
        }
        mongo.db.cocktails.update({"_id": ObjectId(cocktail_id)}, submit)
        flash("Cocktail Successfully Updated")
        return redirect(url_for('view_cocktails'))

    # allows access to admin or cocktail creator to edit cocktail
    if session.get("user") == cocktail["created_by"] or (
                                session["user"] == "admin".lower()):
        return render_template(
                "edit_cocktail.html", cocktail=cocktail, categories=categories)

    # prevents users from gaining access to editing other cocktails
    else:
        flash("You can only edit cocktails that you created.")
        return render_template("cocktails.html")

    cocktail = mongo.db.cocktails.find_one({"_id": ObjectId(cocktail_id)})
    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template(
        "edit_cocktail.html", cocktail=cocktail, categories=categories)


# allows users to delete their submitted cocktails
@app.route("/delete_cocktail/<cocktail_id>")
def delete_cocktail(cocktail_id):
    mongo.db.cocktails.remove({"_id": ObjectId(cocktail_id)})
    flash("Cocktail Successfully Deleted")
    return redirect(url_for("view_cocktails"))


@app.route("/get_categories")
def get_categories():
    # ensures that a user cannot access page without an account
    if session.get("user") is None:
        flash("You must have an admin account to manage categories")
        return render_template("login.html")

    categories = list(mongo.db.categories.find().sort("category_name", 1))

    # prevents users from accessing page without admin account
    if session["user"] == "admin".lower():
        return render_template("categories.html", categories=categories)
    else:
        flash("You must have an admin account to manage categories")
        return redirect(url_for("view_cocktails"))


# functionality to add categories to db
@app.route("/add_category", methods=["GET", "POST"])
def add_category():
    # prevents non-users from accessing page
    if session.get("user") is None:
        flash("You must have an admin account to add categories")
        return render_template("login.html")
    # restricts access of category crud functionality to admin only
    if session["user"] == "admin".lower():
        if request.method == "POST":
            category = {
                "category_name": request.form.get("category_name")
            }
            mongo.db.categories.insert_one(category)
            flash("New Category Added")
            return redirect(url_for('get_categories'))

        return render_template("add_category.html")
    else:
        flash("You must have an admin account to add categories")
        return redirect(url_for("view_cocktails"))


# functionality to edit categories in db
@app.route("/edit_category/<category_id>", methods=["GET", "POST"])
def edit_category(category_id):
    # prevents non-users from accessing page
    if session.get("user") is None:
        flash("You must have an admin account to edit categories")
        return render_template("login.html")

    # provides access for admin accounts to edit categories
    if session["user"] == "admin".lower():
        if request.method == "POST":
            submit = {
                "category_name": request.form.get("category_name")
            }
            mongo.db.categories.update({"_id": ObjectId(category_id)}, submit)
            flash("Category Successfully Updated")
            return redirect(url_for("get_categories"))

    # prevents non admin users from editing cocktails
    else:
        flash("You must have an admin account to edit categories")
        return redirect(url_for("view_cocktails"))

    category = mongo.db.categories.find_one({"_id": ObjectId(category_id)})
    return render_template("edit_category.html", category=category)


# allows user to delete categories
@app.route("/delete_category/<category_id>")
def delete_category(category_id):
    if session.get("user") is None:
        flash("You must have an admin account to edit categories")
        return render_template("login.html")

    # allows admin account to delete categories
    if session["user"] == "admin".lower():
        mongo.db.categories.remove({"_id": ObjectId(category_id)})
        flash("Category Successfully Deleted")
        return redirect(url_for("get_categories"))

    # prevents non admin accounts from deleting categories
    else:
        flash("You must have an admin account to delete categories")
        return redirect(url_for("view_cocktails"))


# Functionality to render 404.html if error 404 occurs
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# Functionality to render 500.html if error 500 occurs
@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=False)
