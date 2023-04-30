from flask import Flask, render_template, redirect
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import update
import requests
from numpy import sin, cos, arccos, pi, round

from data import db_session
from data.add_book import AddBookForm
from data.login_form import LoginForm
from data.edit_profile import EditProfileForm
from data.users import User
from data.books import Books
from data.register import RegisterForm
from data.delete_book import DeleteBookForm
from data.radius_form import RadiusForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)


def rad2deg(radians):
    degrees = radians * 180 / pi
    return degrees


def deg2rad(degrees):
    radians = degrees * pi / 180
    return radians


def getDistanceBetweenPointsNew(latitude1, longitude1, latitude2, longitude2):
    theta = longitude1 - longitude2
    distance = 60 * 1.1515 * rad2deg(
        arccos(
            (sin(deg2rad(latitude1)) * sin(deg2rad(latitude2))) +
            (cos(deg2rad(latitude1)) * cos(deg2rad(latitude2)) * cos(deg2rad(theta)))
        )
    )
    return round(distance * 1.609344, 2)


def radius_adr(address1, address2):
    geocoder_request = \
        f"http://geocode-maps.yandex.ru/1.x/?apikey=40d1649f-0493-4b70-98ba-98533de7710b&geocode={address1}&format=json"
    response1 = requests.get(geocoder_request)
    geocoder_request = \
        f"http://geocode-maps.yandex.ru/1.x/?apikey=40d1649f-0493-4b70-98ba-98533de7710b&geocode={address2}&format=json"
    response2 = requests.get(geocoder_request)
    json_response1 = response1.json()["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    json_response2 = response2.json()["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    lon1, lat1 = [float(x) for x in json_response1["Point"]["pos"].split(" ")]
    lon2, lat2 = [float(x) for x in json_response2["Point"]["pos"].split(" ")]
    return getDistanceBetweenPointsNew(lat1, lon1, lat2, lon2)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.username == form.username.data).first()
        if not user:
            return render_template('login.html', message="Неверный логин", form=form)
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html', message="Неверный пароль", form=form)
    return render_template('login.html', title='Вход', form=form)


@app.route("/")
def index():
    return render_template("index.html", title='Главная')


@app.route("/books", methods=['GET', 'POST'])
def books():
    form_rad = RadiusForm()
    db_sess = db_session.create_session()
    users = db_sess.query(User).all()
    books = db_sess.query(Books).filter(Books.is_sold == 0).all()
    if form_rad.radius.data:
        for book in books:
            if radius_adr(users[book.owner - 1].address, current_user.address) > int(form_rad.radius.data):
                books.pop(books.index(book))
    names = {name.id: (name.surname, name.name) for name in users}
    temple = render_template("booklist.html", books=books, names=names, title='Объявления', form=form_rad)
    t = temple.split('/about_book/aa')
    for i in range(len(t) - 1):
        t.insert(i * 2 + 1, f"/about_book/{books[i].id}")
    return ''.join(t)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.username == form.username.data).first():
            return render_template('register.html', title='Регистрация', form=form,
                                   message="К сожалению, такой логин уже используется другим пользователем")
        user = User(
            name=form.name.data,
            surname=form.surname.data,
            telephone=form.telephone.data,
            username=form.username.data,
            address=form.address.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route("/edit", methods=['GET', 'POST'])
def edit():
    form1 = EditProfileForm()
    if form1.validate_on_submit():
        db_sess = db_session.create_session()
        user = current_user.id
        db_sess.execute(update(User).where(User.id == user).values(name=form1.name.data,
                                                                   surname=form1.surname.data,
                                                                   telephone=form1.telephone.data,
                                                                   address=form1.address.data))
        db_sess.commit()
        return redirect('/')
    return render_template("edit.html", title='Изменение аккаунта', form=form1)


@app.route("/account")
def account():
    db_sess = db_session.create_session()
    books = db_sess.query(Books).filter(Books.owner == current_user.id).all()
    users = db_sess.query(User).all()
    names = {name.id: (name.surname, name.name) for name in users}
    temple = render_template("account.html", books=books, title='Аккаунт', names=names)
    t = temple.split('/about_book/aa')
    for i in range(len(t) - 1):
        t.insert(i * 2 + 1, f"/about_book/{books[i].id}")
    return ''.join(t)


@app.route("/about_book/<int:book_id>", methods=['GET', 'POST'])
def about_book(book_id):
    db_sess = db_session.create_session()
    book = db_sess.query(Books).filter(Books.id == book_id).first()
    users = db_sess.query(User).all()
    names = {name.id: (name.surname, name.name) for name in users}
    is_owner = book.owner == current_user.id
    owner = db_sess.query(User).filter(User.id == book.owner).first()
    form_del = DeleteBookForm()
    if is_owner:
        if form_del.submit.data:
            db_sess.execute(update(Books).where(Books.id == book_id).values(is_sold=1))
            db_sess.commit()
            return redirect('/success')
        return render_template("about_book.html", book=book, title='О книге',
                               is_owner=is_owner, form=form_del, names=names, owner=owner)
    else:
        return render_template("about_book.html", book=book, title='О книге',
                               is_owner=is_owner, names=names, owner=owner)


@app.route("/success")
def success():
    return render_template("success.html", title='Успешно')


@app.route('/add_book', methods=['GET', 'POST'])
def addjob():
    add_form = AddBookForm()
    if add_form.validate_on_submit():
        db_sess = db_session.create_session()
        book = Books(
            title=add_form.title.data,
            author=add_form.author.data,
            owner=current_user.id,
            year=add_form.year.data,
            price=add_form.price.data,
            condition=add_form.condition.data,
            is_sold=False
        )
        db_sess.add(book)
        db_sess.commit()
        return redirect('/success')
    return render_template('addbook.html', title='Добавление книги', form=add_form)


def main():
    db_session.global_init("db/book_yard.sqlite")
    app.run()


if __name__ == '__main__':
    main()
