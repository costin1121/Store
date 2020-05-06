from flask import Flask, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from flask_uploads import UploadSet, configure_uploads, IMAGES
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, HiddenField, SelectField
from wtforms.validators import InputRequired
from flask_wtf.file import FileField, FileAllowed
import random


#de adaugat login pe admin si o tabela cu useri pentru mai mare dezvoltare

app = Flask(__name__)

photos = UploadSet('photos', IMAGES)

app.config['UPLOADED_PHOTOS_DEST'] = 'images'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trendy.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'mysecret'

configure_uploads(app, photos)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)

def handle_cart():
    products = []
    grand_total = 0
    index = 0
    quantity_total = 0
    for item in session['cart']:
        #facem query pentru ce este in sessiune pentru fiecare  item
        product = Product.query.filter_by(id = item['id']).first()
        quantity = int(item['quantity'])
        quantity_total += quantity
        total = quantity * product.price
        tax = 0
        grand_total += total
        products.append({'id' : product.id , 'name' : product.name, 'price' : product.price, 'image' : product.image, 'quantity' : quantity, 'total' : total, 'index' : index})
        index += 1


    return products , grand_total, quantity_total



class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    price = db.Column(db.Integer()) #in bani
    stock = db.Column(db.Integer())
    decription = db.Column(db.String(500))
    image = db.Column(db.String(100))

    orders = db.relationship('Order_Items', backref='product', lazy=True)


class AddProduct(FlaskForm):
    name = StringField('Nume Produs', validators=[InputRequired('Numele este obligatoriu!')])
    price = IntegerField('Pret', validators=[InputRequired('Pretul este obligatoriu')])
    stock = IntegerField('Stoc', validators=[InputRequired('Stocul este obligatoriu')])
    description = TextAreaField('Descriere', validators=['Descrierea este obligatorie'])
    image = FileField('Imagine', validators=[FileAllowed(IMAGES, 'Doar imaginile sunt acceptate')])



class Order(db.Model):
    id = db.Column(db.Integer(), primary_key = True)
    reference = db.Column(db.String(5)) 
    first_name = db.Column(db.String(25)) 
    last_name = db.Column(db.String(25)) 
    phone_number = db.Column(db.Integer())
    email = db.Column(db.String(50))
    adress = db.Column(db.String(150))  
    city  = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(50))
    status = db.Column(db.String(10))
    payment_type = db.Column(db.String(10))

    items = db.relationship('Order_Items', backref='order', lazy=True)

    def order_total(self):
        return db.session.query(db.func.sum(Order_Items.quantity * Product.price)).join(Product).filter(Order_Items.order_id == self.id).scalar() + 1000 # intorc totalul

    def quantity_total(self):
        return db.session.query(db.func.sum(Order_Items.quantity)).filter(Order_Items.order_id == self.id).scalar() 




class Order_Items(db.Model):
    id = db.Column(db.Integer(), primary_key = True)
    order_id = db.Column(db.Integer(), db.ForeignKey('order.id'))
    product_id = db.Column(db.Integer(), db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer())



class AddToCart(FlaskForm):
    quantity = IntegerField('Cantitate', validators=[InputRequired('Cantitatea este obligatorie')])
    id = HiddenField('ID')


class Checkout(FlaskForm):
    first_name = StringField('Nume' , validators=[InputRequired('Numele este obligatoriu')])
    last_name = StringField('Prenume', validators=[InputRequired('Prenumele este obligatoriu')])
    phone_number = StringField('Telefon', validators=[InputRequired('Telefonul este obligatoriu')])
    email = StringField('Email', validators=[InputRequired('Email-ul este obligatoriu')])
    adress = StringField('Adresa', validators=[InputRequired('Adresa este obligatorie')])
    city = StringField('Oras', validators=[InputRequired('Orasul este obligatorie')])
    state = SelectField('Judet', choices=[('B', 'Bucuresti'), ('TM','Timisoara'), ('CJ' ,'Cluj')])
    country = SelectField('Tara', choices=[('RO','Romania')])
    payment_type = SelectField('Metoda de Plata', choices=[('C', 'Card'), ('csh', 'Cash')])



@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products = products)

    

@app.route('/product/<id>')
def product(id):
    product = Product.query.filter_by(id = id).first()
    form = AddToCart()
    return render_template('view-product.html', product = product, form = form)


@app.route('/quick-add/<id>')
def quick_add(id):
    if 'cart' not in session:
        session['cart'] = []

    session['cart'].append({'id' : id, 'quantity' : 1})
    session.modified = True
    return redirect(url_for('index'))




@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    form = AddToCart()
    if 'cart' not in session:
        session['cart'] = []
        
    if form.validate_on_submit():
        #adaugam in sesiune
        session['cart'].append({'id' : form.id.data, 'quantity' : form.quantity.data})
        session.modified = True
    
    return redirect(url_for('index'))

@app.route('/cart')
def cart():
    total = 0

    products , grand_total, quantity_total = handle_cart()

    grand_total_plus_shipping =  grand_total# fara tva
    grand_total_with_vat = grand_total_plus_shipping * 1.19
    tax = grand_total_with_vat - grand_total_plus_shipping
    taxRound = round(tax, 0)
    grand_full = grand_total_plus_shipping + taxRound

    return render_template('cart.html', products = products, total = total, taxRound = taxRound, grand_total = grand_total, grand_total_plus_shipping = grand_total_plus_shipping, grand_full = grand_full, quantity_total = quantity_total)



@app.route('/remove-from-cart/<index>')
def remove_from_cart(index):
    del session['cart'][int(index)]
    session.modified = True
    return redirect(url_for('cart'))


@app.route('/checkout', methods=['GET','POST'])
def checkout():
    form = Checkout()
    total = 0
    
    products, grand_total, quantity_total = handle_cart()
    
    grand_total_plus_shipping =  grand_total# fara tva
    grand_total_with_vat = grand_total_plus_shipping * 1.19
    tax = grand_total_with_vat - grand_total_plus_shipping
    taxRound = round(tax, 0)
    grand_full = grand_total_plus_shipping + taxRound
    

    if form.validate_on_submit():
        #products, grand_total = handle_cart()
        
        order = Order()
        form.populate_obj(order)
        order.reference = ''.join([random.choice('ABCDE') for _ in range(5)])
        order.status = 'PENDING'


        for product in products:
            order_item = Order_Items(quantity= product['quantity'] , product_id= product['id'])
            order.items.append(order_item)

            product = Product.query.filter_by(id = product['id']).update({'stock' : Product.stock - product['quantity']})

        db.session.add(order)
        db.session.commit()

        
        session['cart'] = []
        session.modified = True

        return redirect(url_for('index'))
    

    return render_template('checkout.html', form = form,  products = products, total = total, taxRound = taxRound, grand_total = grand_total, grand_total_plus_shipping = grand_total_plus_shipping, grand_full = grand_full, quantity_total = quantity_total)

@app.route('/admin')
def admin():
    products = Product.query.all()

    orders = Order.query.all()

    product_in_stock = Product.query.filter(Product.stock > 0).count()

    return render_template('admin/index.html', admin=True, products = products,  product_in_stock = product_in_stock, orders = orders)

@app.route('/admin/add', methods=['GET', 'POST'])
def add():
    form = AddProduct()
    if form.validate_on_submit():

       image_filename = photos.save(form.image.data)
       image_url = photos.url(image_filename)

       new_product = Product(name = form.name.data, price = form.price.data, stock = form.stock.data , decription = form.description.data, image = image_url)
       db.session.add(new_product)
       db.session.commit()

       return redirect(url_for('admin'))

    return render_template('admin/add-product.html', admin=True, form = form)

@app.route('/admin/order/<order_id>')
def order(order_id):
    order = Order.query.filter_by(id = int(order_id)).first()

    return render_template('admin/view-order.html', order = order ,admin=True)

if __name__ == '__main__':
    manager.run()