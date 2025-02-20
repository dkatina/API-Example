from flask import Flask, jsonify, request
#Flask - gives us all the tools we need to run a flask app by creating an instance of this class
#jsonify - converst data to JSON
#request - allows us to interact with HTTP method requests as objects
from flask_sqlalchemy import SQLAlchemy
#SQLAlchemy = ORM to connect and relate python classes to SQL tables
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
#DeclarativeBase - gives ust the base model functionallity to create the Classes as Model Classes for our db tables
#Mapped - Maps a Class attribute to a table column or relationship
#mapped_column - sets our Column and allows us to add any constraints we need (unique,nullable, primary_key)
from flask_marshmallow import Marshmallow
#Marshmallow - allows us to create a schema to valdite, serialize, and deserialize JSON data
from datetime import date
#date - use to create date type objects
from typing import List
#List - is used to creat a relationship that will return a list of Objects
from marshmallow import ValidationError, fields
#fields - lets us set a schema field which includes datatype and constraints
from sqlalchemy import select, delete
#select - acts as our SELECT FROM query
#delete - acts as our DELET query


app = Flask(__name__) #creating and instance of our flask app
                                                                
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db' #Students should use mysql

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(app, model_class=Base)
ma = Marshmallow(app)

#====================== MODELS ==============================================

class Customer(Base):
    __tablename__ = 'Customer' #Make your class name the same as your table name (trust me)

    #mapping class attributes to database table columns
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(225), nullable=False)
    email: Mapped[str] = mapped_column(db.String(225))
    address: Mapped[str] = mapped_column(db.String(225))
    #creating one-to-many relationship to Orders table
    orders: Mapped[List["Orders"]] = db.relationship(back_populates='customer') #back_populates insures that both ends of the relationship have access to the other

order_products = db.Table(
    "Order_Products",
    Base.metadata, #Allows this table to locate the foreign keys from the other Base class
    db.Column('order_id', db.ForeignKey('orders.id')),
    db.Column('product_id', db.ForeignKey('products.id'))
)


class Orders(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True)
    order_date: Mapped[date] = mapped_column(db.Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey('Customer.id'))
    #creating a many-to-one relationship to Customer table
    customer: Mapped['Customer'] = db.relationship(back_populates='orders')
    #creating a many-to-many relationship to Products through or association table order_products
    products: Mapped[List['Products']] = db.relationship(secondary=order_products, back_populates="orders")

class Products(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(db.String(255), nullable=False )
    price: Mapped[float] = mapped_column(db.Float, nullable=False)

    orders: Mapped[List['Orders']] = db.relationship(secondary=order_products, back_populates="products")

#Initialize the database and create tables
with app.app_context():
#    db.drop_all() 
    db.create_all() #First check which tables already exist, and then create and tables it couldn't find
                    #However if it finds a table with the same name, it doesn't construct or modify




#============================ SCHEMAS ==================================

#Defin Customer Schema
class CustomerSchema(ma.SQLAlchemyAutoSchema): #SQLAlchemyAutoSchemas create schema fields based on the SQLALchemy model passed in
    class Meta:
        model = Customer

class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Products

class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Orders
        include_fk = True #Need this because Auto Schemas don't automatically recognize foreign keys (customer_id)


customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many= True)

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)


@app.route('/')
def home():
    return "If your are Lost welcome to the Sauce!"


#====================Customer CRUD==========================

#Get all customers using a GET method
@app.route("/customers", methods=['GET'])
def get_customers():
    query = select(Customer)
    result = db.session.execute(query).scalars() #Exectute query, and convert row objects into scalar objects (python useable)
    customers = result.all() #packs objects into a list
    return customers_schema.jsonify(customers)

#Get Specific customer using GET method and dynamic route
@app.route("/customers/<int:id>", methods=['GET'])
def get_customer(id):
    
    query = select(Customer).where(Customer.id == id)
    result = db.session.execute(query).scalars().first() #first() grabs the first object return

    if result is None:
        return jsonify({"Error": "Customer not found"}), 404
    
    return customer_schema.jsonify(result)

#Creating customers with POST request
@app.route("/customers", methods=["POST"])
def add_customer():

    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400

    new_customer = Customer(name=customer_data['name'], email=customer_data['email'], address=customer_data['address'])
    db.session.add(new_customer)
    db.session.commit()

    return jsonify({"Message": "New Customer added successfully",
                    "customer": customer_schema.dump(new_customer)}), 201

#Update a user with PUT request
@app.route("/customers/<int:id>", methods=['PUT'])
def update_customer(id):

    query = select(Customer).where(Customer.id == id)
    result = db.session.execute(query).scalars().first()
    if result is None: #Query the database for the user to see if this user even exists
        return jsonify({"Error": "Customer not found"}), 404
    
    customer = result
    
    try:
        customer_data = customer_schema.load(request.json) #Load and validate incloming customer data
    except ValidationError as e:
        return jsonify(e.messages), 400 #return error message if the data is invalid
    
    for field, value in customer_data.items(): #Go through customer data and set the attributes of the customer object
        setattr(customer, field, value)

    db.session.commit() #commit changes
    return jsonify({"Message": "Customer details have been updated!",
                    "customer": customer_schema.dump(customer)})

#Delete a user with DELETE request
@app.route("/customers/<int:id>", methods=['DELETE'])
def delete_customer(id):
    query = delete(Customer).filter(Customer.id == id)

    result = db.session.execute(query)

    if result.rowcount == 0:
        return jsonify({'Error': 'Customer not found'}), 404
    
    db.session.commit()
    return jsonify({"Message": "Customer removed Successfully!"}), 200


#====================Products CRUD==========================


@app.route('/products', methods=['POST'])
def create_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    new_product = Products(product_name=product_data['product_name'], price=product_data['price'])
    db.session.add(new_product)
    db.session.commit()

    return jsonify({"Messages": "New Product added!",
                    "product": product_schema.dump(new_product)}), 201

@app.route("/products", methods=['GET'])
def get_products():
    query = select(Products)
    result = db.session.execute(query).scalars() #Exectute query, and convert row objects into scalar objects (python useable)
    products = result.all() #packs objects into a list
    return products_schema.jsonify(products)

#Get Specific product using GET method and dynamic route
@app.route("/products/<int:id>", methods=['GET'])
def get_product(id):
    
    query = select(Products).where(Products.id == id)
    result = db.session.execute(query).scalars().first() #first() grabs the first object return

    if result is None:
        return jsonify({"Error": "product not found"}), 404
    
    return product_schema.jsonify(result)

#Update a user with PUT request
@app.route("/products/<int:id>", methods=['PUT'])
def update_product(id):

    query = select(Products).where(Products.id == id)
    result = db.session.execute(query).scalars().first()
    if result is None: #Check if product to be updated exists
        return jsonify({"Error": "product not found"}), 404
    
    product = result
    
    try:
        product_data = product_schema.load(request.json) #validating data from incoming request
    except ValidationError as e:  
        return jsonify(e.messages), 400 #returning error message if data is invalid
    
    for field, value in product_data.items(): #updating specific product with product_data
        setattr(product, field, value)

    db.session.commit() #commiting changes
    return jsonify({"Message": "product details have been updated!",
                    "product": product_schema.dump(product)}), 200

#Delete a product with DELETE request
@app.route("/products/<int:id>", methods=['DELETE'])
def delete_product(id):
    product = db.session.get(Products, id) #Query product using primary key id.

    if product:
        db.session.delete(product) #delete product
        db.session.commit() #save changes
        return jsonify({"message": "Product successfully deleted"}), 200
    return jsonify({"message": "Invlaid product id"}), 200
    
    



#====================Order Operations================================
#CREATE an ORDER
@app.route('/orders', methods=['POST'])
def add_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    new_order = Orders(order_date=order_data['order_date'], customer_id = order_data['customer_id'])

    db.session.add(new_order)
    db.session.commit()

    return jsonify({"Message": "New Order Placed!",
                    "order": order_schema.dump(new_order)}), 201

#ADD ITEM TO ORDER
@app.route('/orders/<int:order_id>/add_product/<int:product_id>', methods=['PUT'])
def add_product(order_id, product_id):
    order = db.session.get(Orders, order_id) #can use .get when querying using Primary Key
    product = db.session.get(Products, product_id)

    if order and product: #check to see if both exist
        if product not in order.products: #Ensure the product is not already on the order
            order.products.append(product) #create relationship from order to product
            db.session.commit() #commit changes to db
            return jsonify({"Message": "Successfully added item to order."}), 200
        else:#Product is in order.products
            return jsonify({"Message": "Item is already included in this order."}), 400
    else:#order or product does not exist
        return jsonify({"Message": "Invalid order id or product id."}), 400
    

#REMOVE ITEM FROM ORDER
@app.route('/orders/<int:order_id>/remove_product/<int:product_id>', methods=['DELETE'])
def remove_product(order_id, product_id):
    order = db.session.get(Orders, order_id) #can use .get when querying using Primary Key
    product = db.session.get(Products, product_id)

    if order and product: #check to see if both exist
        if product in order.products: #Ensure the product is on the order
            order.products.remove(product) #remove relationship from order to product
            db.session.commit() #commit changes to db
            return jsonify({"Message": "Successfully removed item from order."}), 200
        else:#Product is not in order.products
            return jsonify({"Message": "Item is not included in this order."}), 400
    else:#order or product does not exist
        return jsonify({"Message": "Invalid order id or product id."}), 400
    

#GET ORDER USING CUSTOMER ID
@app.route("/orders/user/<int:customer_id>", methods=['GET'])
def customer_orders(customer_id):
    customer = db.session.get(Customer, customer_id)

    if customer: #check if customer exists
        return orders_schema.jsonify(customer.orders), 200 #using the customer's relationship attribute "orders" to return all associated orders
    return jsonify({"message": "Invalid customer id."}), 400

#Return all products on an order
@app.route("/orders/<int:order_id>/products", methods=['GET'])
def order_products(order_id):
    order = db.session.get(Orders, order_id)

    if order: #check if order exists
        return products_schema.jsonify(order.products), 200 #using the order's relationship attribute "products" to return all associated products
    return jsonify({"message": "Invalid order id."}), 400


if __name__ == '__main__':
    app.run(debug=True)