from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_cors import CORS
import bcrypt
from bson import ObjectId
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Fix CORS - Allow all origins for development
CORS(app, origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:5000", "http://127.0.0.1:5000"], supports_credentials=True)

# MongoDB connection
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")

if not app.config["MONGO_URI"]:
    print("❌ MONGO_URI not found!")
    mongo = None
else:
    try:
        mongo = PyMongo(app)
        mongo.db.command('ping')
        print("✅ MongoDB connected successfully!")
    except Exception as e:
        print(f"❌ MongoDB connection error: {e}")
        mongo = None

@app.route('/')
def home():
    return "LinkHub API is running"

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    if mongo is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        data = request.json
        
        if not data.get('email') or not data.get('password') or not data.get('username'):
            return jsonify({"error": "All fields are required"}), 400
        
        if mongo.db.users.find_one({"email": data['email']}):
            return jsonify({"error": "Email already registered"}), 400
        
        if mongo.db.users.find_one({"username": data['username']}):
            return jsonify({"error": "Username already taken"}), 400
        
        hashed_pw = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
        
        user_data = {
            "username": data['username'],
            "email": data['email'],
            "password": hashed_pw,
            "displayName": data.get('displayName', data['username']),
            "bio": "",
            "avatar": "",
            "website": "",
            "location": "",
            "created_at": datetime.datetime.now()
        }
        
        result = mongo.db.users.insert_one(user_data)
        
        return jsonify({
            "message": "Account created successfully",
            "user": {
                "id": str(result.inserted_id),
                "username": user_data['username'],
                "email": user_data['email'],
                "displayName": user_data['displayName']
            }
        }), 201
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    if mongo is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        data = request.json
        
        if not data.get('email') or not data.get('password'):
            return jsonify({"error": "Email and password required"}), 400
        
        user = mongo.db.users.find_one({"email": data['email']})
        
        if user and bcrypt.checkpw(data['password'].encode('utf-8'), user['password']):
            return jsonify({
                "id": str(user['_id']),
                "username": user['username'],
                "email": user['email'],
                "displayName": user.get('displayName', user['username']),
                "avatar": user.get('avatar', ''),
                "bio": user.get('bio', ''),
                "website": user.get('website', ''),
                "location": user.get('location', '')
            })
        
        return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/links', methods=['POST'])
def create_link():
    if mongo is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        data = request.json
        
        link = {
            "userId": data['userId'],
            "username": data['username'],
            "title": data['title'],
            "url": data['url'],
            "description": data.get('description', ''),
            "order": data.get('order', 0),
            "clicks": 0,
            "created_at": datetime.datetime.now()
        }
        
        result = mongo.db.links.insert_one(link)
        link['_id'] = str(result.inserted_id)
        
        return jsonify({"message": "Link created", "link": link}), 201
    except Exception as e:
        print(f"Create link error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/links/user/<user_id>', methods=['GET'])
def get_links(user_id):
    if mongo is None:
        return jsonify([]), 200
    
    try:
        links = list(mongo.db.links.find({"userId": user_id}))
        
        for link in links:
            link['_id'] = str(link['_id'])
        
        links.sort(key=lambda x: x.get('order', 0))
        
        return jsonify(links)
    except Exception as e:
        print(f"Error fetching links: {e}")
        return jsonify([]), 200

@app.route('/api/links/<link_id>', methods=['DELETE'])
def delete_link(link_id):
    if mongo is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        mongo.db.links.delete_one({"_id": ObjectId(link_id)})
        return jsonify({"message": "Link deleted"})
    except Exception as e:
        print(f"Delete link error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/links/<link_id>/click', methods=['POST'])
def track_click(link_id):
    if mongo is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        mongo.db.links.update_one(
            {"_id": ObjectId(link_id)},
            {"$inc": {"clicks": 1}}
        )
        return jsonify({"message": "Click tracked"})
    except Exception as e:
        print(f"Track click error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/by-username/<username>', methods=['GET'])
def get_user_by_username(username):
    if mongo is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        user = mongo.db.users.find_one(
            {"username": username},
            {"password": 0}
        )
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user['_id'] = str(user['_id'])
        
        return jsonify(user)
    except Exception as e:
        print(f"Get user error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user_profile(user_id):
    if mongo is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        # Try to convert to ObjectId, if it fails, it's a string ID
        try:
            obj_id = ObjectId(user_id)
            user = mongo.db.users.find_one({"_id": obj_id}, {"password": 0})
        except:
            # If not valid ObjectId, try as string
            user = mongo.db.users.find_one({"_id": user_id}, {"password": 0})
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user['_id'] = str(user['_id'])
        
        return jsonify(user)
    except Exception as e:
        print(f"Get user profile error: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/users/<user_id>/profile', methods=['PUT'])
def update_profile(user_id):
    if mongo is None:
        return jsonify({"error": "Database not connected"}), 500
    
    try:
        data = request.json
        print("Incoming:", data)

        # Try to convert to ObjectId
        try:
            user_obj_id = ObjectId(user_id)
        except:
            user_obj_id = user_id

        allowed_fields = ['displayName', 'bio', 'avatar', 'website', 'location']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        if not update_data:
            return jsonify({"error": "No valid fields to update"}), 400

        result = mongo.db.users.update_one(
            {"_id": user_obj_id},
            {"$set": update_data}
        )

        print("Modified:", result.modified_count)

        return jsonify({"message": "Profile updated"})

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<user_id>/stats', methods=['GET'])
def get_stats(user_id):
    if mongo is None:
        return jsonify({"totalLinks": 0, "totalClicks": 0}), 200
    
    try:
        total_links = mongo.db.links.count_documents({"userId": user_id})
        
        pipeline = [
            {"$match": {"userId": user_id}},
            {"$group": {"_id": None, "totalClicks": {"$sum": "$clicks"}}}
        ]
        
        result = list(mongo.db.links.aggregate(pipeline))
        total_clicks = result[0]['totalClicks'] if result else 0
        
        return jsonify({
            "totalLinks": total_links,
            "totalClicks": total_clicks
        })
    except Exception as e:
        print(f"Stats error: {e}")
        return jsonify({"totalLinks": 0, "totalClicks": 0}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)