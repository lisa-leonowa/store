import os

import requests
from flask import Flask, render_template, request, make_response, jsonify, abort, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from werkzeug.utils import redirect
from wtforms import PasswordField, StringField, TextAreaField, SubmitField, BooleanField
from wtforms.fields.html5 import EmailField
import sqlite3
import shutil

# noinspection PyUnresolvedReferences
from wtforms.validators import DataRequired
# noinspection PyUnresolvedReferences
from data import db_session
# noinspection PyUnresolvedReferences
from data.users import User
# noinspection PyUnresolvedReferences
from data.goods import Goods
# noinspection PyUnresolvedReferences
from data.orders import Orders

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)


class RegisterForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    name = StringField('Имя пользователя', validators=[DataRequired()])
    submit = SubmitField('Войти')


class LoginForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


@login_manager.user_loader
def load_user(user_id):
    sessions = db_session.create_session()
    return sessions.query(User).get(user_id)


def main():
    app.run(port=8080, host='127.0.0.1')


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route("/", methods=['GET', 'POST'])
def index():
    lis = []
    sessions = db_session.create_session()
    goods = sessions.query(Goods).all()
    if request.method == 'POST':
        for i in request.form.getlist('model'):
            good = sessions.query(Goods).filter(Goods.id == int(i)).first()
            lis.append(good)
        return render_template("index.html", title='Отфильтрованные товары', goods=lis)
    return render_template("index.html", title='Интернет-магазин', goods=goods)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html', title='Авторизация',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


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
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        session = db_session.create_session()
        if session.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        session.add(user)
        session.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route("/info/<int:goods_id>")
def info(goods_id):
    sessions = db_session.create_session()
    goods = sessions.query(Goods).filter(Goods.id == goods_id).first()
    return render_template("info.html", title='Информация о товаре', goods=goods)


@app.route("/add/<int:goods_id>")
def add(goods_id):
    sessions = db_session.create_session()
    goods = sessions.query(Goods).filter(Goods.id == goods_id).first()
    if goods.value > 0:
        if 'add' in session:
            zn = session['add']
        else:
            zn = []
        conn = sqlite3.connect('db/shop.sqlite')
        cur = conn.cursor()
        sql = f"""
        UPDATE orders 
        SET value = value + 1
        WHERE id = {goods.id}
        """
        cur.execute(sql)
        conn.commit()
        ok, sp = True, 0
        for i in range(len(zn)):
            if goods.id in zn[i]:
                ok = False
                sp = i
        if ok:
            zn.append([goods.id, goods.name, goods.image, goods.coast, goods.value])
            conn = sqlite3.connect('db/shop.sqlite')
            cur = conn.cursor()
            sql = f"""
                INSERT INTO orders 
                VALUES ({goods.id}, '{goods.name}', '{goods.content}', '{goods.image}', {goods.coast}, 1)
                """
            cur.execute(sql)
            conn.commit()
        else:
            zn[sp][-1] += 1

        session['add'] = zn
        return render_template("add.html", title='Добавление товара', goods=goods)
    else:
        return render_template("add.html", title='Добавление товара', goods=goods, message='нет на скаладе')


@app.route("/basket", methods=['GET', 'POST'])
def basket():
    if current_user.is_authenticated == True:
        if request.method == 'POST':
            button = request.form['button']
            but = int(button.split()[1])
            sessions = db_session.create_session()
            orders = sessions.query(Orders).filter(Orders.id == but).first()
            goods = sessions.query(Goods).filter(Goods.id == but).first()
            if button.split()[0] == '2':
                if orders.value + 1 <= goods.value:
                    conn = sqlite3.connect('db/shop.sqlite')
                    cur = conn.cursor()
                    sql = f"""
                        UPDATE orders 
                        SET value = value + 1
                        WHERE id = {orders.id}
                        """
                    cur.execute(sql)
                    conn.commit()
            if button.split()[0] == '1':
                conn = sqlite3.connect('db/shop.sqlite')
                cur = conn.cursor()
                if orders.value - 1 > 0:
                    sql = f"""
                        UPDATE orders 
                        SET value = value - 1
                        WHERE id = {orders.id}
                        """
                    cur.execute(sql)
                    conn.commit()

        if 'add' in session:
            goods = session['add']
        else:
            goods = []
        sessions = db_session.create_session()
        orders = sessions.query(Orders).all()
        for i in range(len(orders)):
            goods[i][-1] = orders[i].value
        return render_template("basket.html", title='Корзина', goods=goods)
    else:
        return render_template("basket.html", title='Корзина', me='Авторизуйтесь, чтобы просматривать корзину!')


@app.route("/clear")
def clear():
    if 'add' in session:
        session['add'] = []
    goods = session['add']

    conn = sqlite3.connect('db/shop.sqlite')
    cur = conn.cursor()
    sql = """DELETE FROM orders"""
    cur.execute(sql)
    conn.commit()
    return render_template("basket.html", title='Корзина', goods=goods, message='Ваша корзина пуста')


@app.route("/order")
def order():
    # нужно создать БД с заказами пользователей
    # вывод общей стоимости товара

    sessions = db_session.create_session()
    order = sessions.query(Orders).all()
    goods = sessions.query(Goods).all()
    total = 0
    for i in order:
        total += i.coast * i.value
    for item in order:
        conn = sqlite3.connect('db/shop.sqlite')
        cur = conn.cursor()
        sql = f"""UPDATE goods SET value = value - {item.value} WHERE id = {item.id}"""
        cur.execute(sql)
        conn.commit()

    if 'add' in session:
        session['add'] = []
    goods = session['add']

    conn = sqlite3.connect('db/shop.sqlite')
    cur = conn.cursor()
    sql = """DELETE FROM orders"""
    cur.execute(sql)
    conn.commit()

    return render_template("order.html", title='Оформление заказа', goods=goods, total=total)


@app.route('/map')
def map():
    mash = 16
    mark = '37.74164199829102,55.78153275636508,pm2rdm'
    mark2 = ''
    map_request = 'https://static-maps.yandex.ru/1.x/?l=map&pt=' + mark + ',' + '&z=' + str(mash)
    response = requests.get(map_request)
    map_file = 'map.png'
    with open(map_file, "wb") as file:
        file.write(response.content)

    sourse = os.getcwd() + '/map.png'
    dest = os.getcwd() + '/static/img/map.png'
    shutil.move(sourse, dest)
    return render_template('map.html', title='Пункт выдачи')


@app.route("/cookie_test")
def cookie_test():
    visits_count = int(request.cookies.get("visits_count", 0))
    if visits_count:
        res = make_response(f"Вы пришли на эту страницу {visits_count + 1} раз")
        res.set_cookie("visits_count", str(visits_count + 1),
                       max_age=60 * 60 * 24 * 365 * 2)
    else:
        res = make_response(
            "Вы пришли на эту страницу в первый раз за последние 2 года")
        res.set_cookie("visits_count", '1',
                       max_age=60 * 60 * 24 * 365 * 2)
    return res


db_session.global_init("db/shop.sqlite")
if __name__ == '__main__':
    main()
