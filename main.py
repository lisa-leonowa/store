from flask import Flask, render_template, request, make_response, jsonify, abort, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from werkzeug.utils import redirect
from wtforms import PasswordField, StringField, TextAreaField, SubmitField, BooleanField
from wtforms.fields.html5 import EmailField

# noinspection PyUnresolvedReferences
from wtforms.validators import DataRequired
# noinspection PyUnresolvedReferences
from data import db_session
# noinspection PyUnresolvedReferences
from data.users import User
# noinspection PyUnresolvedReferences
from data.goods import Goods
# noinspection PyUnresolvedReferences

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
    db_session.global_init("db/shop.sqlite")
    app.run(port=8071, host='127.0.0.1')


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
        return render_template("index.html", goods=lis)
    return render_template("index.html", goods=goods)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
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
    return render_template("info.html", goods=goods)


@app.route("/add/<int:goods_id>")
def add(goods_id):
    sessions = db_session.create_session()
    goods = sessions.query(Goods).filter(Goods.id == goods_id).first()

    if 'add' in session:
        zn = session['add']
    else:
        zn = []
    zn.append(goods.name)
    session['add'] = zn
    return render_template("add.html", goods=goods)


@app.route("/basket")
def basket():
    if 'add' in session:
        goods = session['add']
        message = 'Вы добавили данные товары'
    else:
        goods = []
        message = 'Ваша карзина пуста'
    return render_template("basket.html", goods=goods, message=message)


@app.route("/clear")
def clear():
    if 'add' in session:
        session['add'] = []
    goods = session['add']
    return render_template("basket.html", goods=goods)


@app.route("/order")
def order():
    # нужно создать БД с заказами пользователей
    # вывод общей стоимости товара
    if 'add' in session:
        session['add'] = []
    goods = session['add']
    return render_template("order.html", goods=goods)
    

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


if __name__ == '__main__':
    main()
