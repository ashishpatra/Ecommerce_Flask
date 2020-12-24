from flask import Flask, render_template, request, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from werkzeug.utils import secure_filename
import json
import os
import math
from datetime import datetime


with open('config.json', 'r') as c:
    params = json.load(c) ["params"]

local_server = True
app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = params['upload_location']
app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = '465',
    MAIL_USE_SSL = True,
    MAIL_USERNAME = params['gmail-user'],
    MAIL_PASSWORD = params['gmail-password']
)
mail = Mail(app)

if(local_server):
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']

db = SQLAlchemy(app)

class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)

class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(30), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    tagline = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(50), nullable=True)

class Stores(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    prodName = db.Column(db.String(100), nullable=False)

class Orders(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(30), nullable=False)
    phone = db.Column(db.String(12), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(12), nullable=True)

@app.route("/")
def home():
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts) / int(params['no_of_posts']))
    #Pagination Logic
    page = request.args.get('page')
    if(not str(page).isnumeric()):
        page = 1
    page = int(page)
    posts = posts[(page-1)*int(params['no_of_posts']) : (page-1)*int(params['no_of_posts']) + int(params['no_of_posts'])]
    if(page == 1):
        prev = "#"
        next = "/?page=" + str(page+1)
    elif(page == last):
        prev = "/?page=" + str(page - 1)
        next = "#"
    else:
        prev = "/?page=" + str(page - 1)
        next = "/?page=" + str(page+1)

    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)


@app.route("/order", methods = ['GET', 'POST'])
def order():
    prods = Stores.query.all()
    if(request.method == 'POST'):
        '''Add entry to the database'''
        item_list = request.form.getlist('product')
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')

        # Converting list to strings
        seperator = ', '
        item = (seperator.join(item_list))

        entry = Orders(item=item, name=name, phone=phone, address=address, date= datetime.now())
        db.session.add(entry)
        db.session.commit()
        mail.send_message('New order from ' + name,
                          sender = address,
                          recipients = [params['gmail-user']],
                          body = item + "\n\n" + address + "\n\n" + phone
                          )
        flash("Your order has been placed successfully.", "success")
    return render_template('order.html', params=params, prods=prods)



@app.route("/post/<string:post_slug>", methods=['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params=params, post=post)

@app.route("/about")
def about():
    return render_template('about.html', params=params)

@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if ('user' in session and session['user'] == params['admin_user']):
        posts = Posts.query.all()
        prods = Stores.query.all()
        return render_template('dashboard.html', params=params, posts=posts, prods=prods)

    if request.method == 'POST':
        username = request.form.get('uname')
        userpass = request.form.get('pass')
        if (username == params['admin_user'] and userpass == params['admin_password']):
            #Set the session variable
            session['user'] = username
            posts = Posts.query.all()
            prods = Stores.query.all()
            return render_template('dashboard.html', params=params, posts=posts, prods=prods)

    return render_template('login.html', params=params)


@app.route("/edit/<string:sno>", methods = ['GET', 'POST'])
def edit(sno):
    if ('user' in session and session['user'] == params['admin_user']):
        if request.method == 'POST':
            box_title = request.form.get('title')
            tline = request.form.get('tline')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('img_file')
            date = datetime.now()

            if sno == '0':
                post = Posts(title=box_title, tagline=tline, slug=slug, content=content, img_file=img_file, date=date)
                db.session.add(post)
                db.session.commit()
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = box_title
                post.tagline = tline
                post.slug = slug
                post.content = content
                post.img_file = img_file
                post.date = date
                db.session.commit()
                return redirect('/edit/'+sno)
        post = Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html', params=params, post=post, sno=sno)


@app.route("/delete/<string:sno>", methods = ['GET', 'POST'])
def delete(sno):
    if ('user' in session and session['user'] == params['admin_user']):
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect('/dashboard')


@app.route("/addItem/<string:sno>", methods = ['GET', 'POST'])
def addItem(sno):
    if ('user' in session and session['user'] == params['admin_user']):
        if request.method == 'POST':
            prodName = request.form.get('item')

            if sno == '0':
                prod = Stores(prodName=prodName)
                db.session.add(prod)
                db.session.commit()
            else:
                prod = Stores.query.filter_by(sno=sno).first()
                prod.prodName = prodName
                db.session.commit()
                return redirect('/addItem/'+sno)
        prod = Stores.query.filter_by(sno=sno).first()
        return render_template('add.html', params=params, prod=prod, sno=sno)


@app.route("/removeItem/<string:sno>", methods = ['GET', 'POST'])
def removeItem(sno):
    if ('user' in session and session['user'] == params['admin_user']):
        prod = Stores.query.filter_by(sno=sno).first()
        db.session.delete(prod)
        db.session.commit()
    return redirect('/dashboard')


@app.route("/viewOrder", methods = ['GET', 'POST'])
def viewOrder():
    if ('user' in session and session['user'] == params['admin_user']):
        orders = Orders.query.all()
        return render_template('viewOrder.html', params=params, orders=orders)


@app.route("/removeOrder/<string:sno>", methods = ['GET', 'POST'])
def removeOrder(sno):
    if ('user' in session and session['user'] == params['admin_user']):
        order = Orders.query.filter_by(sno=sno).first()
        db.session.delete(order)
        db.session.commit()
    return redirect('/viewOrder')



@app.route("/uploader", methods = ['GET', 'POST'])
def uploader():
    if ('user' in session and session['user'] == params['admin_user']):
        if request.method == 'POST':
            f = request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename) ))
            return 'Your file has been uploaded successfully'


@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/dashboard')


@app.route("/contact", methods = ['GET', 'POST'])
def contact():
    if(request.method == 'POST'):
        '''Add entry to the database'''
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        entry = Contacts(name=name, email=email, phone=phone, msg=message, date= datetime.now())
        db.session.add(entry)
        db.session.commit()
        mail.send_message('New message from ' + name,
                          sender = email,
                          recipients = [params['gmail-user']],
                          body = message + "\n\n" + phone
                          )
        flash("Thanks for contact. We will get back to you soon.", "success")
    return render_template('contact.html', params=params)

app.run(debug=True)

