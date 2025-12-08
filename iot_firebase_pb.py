import pyrebase

# 🔹 就放在這裡：import 下面、初始化前
config = {
    "apiKey": "AIzaSyCcnUT8TN1RuiOBifEqEznRlogNrwX-sI0",
    "authDomain": "ntuiot-f7743.firebaseapp.com",
    "databaseURL": "https://ntuiot-f7743-default-rtdb.firebaseio.com",
    "projectId": "ntuiot-f7743",
    "storageBucket": "ntuiot-f7743.appspot.com",
    "messagingSenderId": "224195625096",
    "appId": "1:224195625096:web:a0bcbefcf733f6b8d35f3d"
}

# 初始化 firebase
firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()

# 🔐 用你在 Firebase 建好的管理帳號登入
email = "alecchan1995@gmail.com"
password = "123456789"  # ← 改成你真的設的密碼

user = auth.sign_in_with_email_and_password(email, password)
id_token = user["idToken"]
print("登入成功，uid =", user["localId"])

# ✅ 新增一筆 product
new_product = {
    "table_id": 1,
    "name": "noodled",
    "number": 10,
    "id": 0,
}
db.child("product").push(new_product, id_token)
print("已新增 product")

# ✅ 讀取全部 product
products = db.child("product").get(id_token)
print("目前 product：")
for item in products.each():
    print(item.key(), "=>", item.val())

key_to_update = "-Oe6MUUnY2-Sa_pBKz95"

db.child("product").child(key_to_update).update({
    "name": "noodle",   # 也可以改成別的
    "number": 500,       # 改數量
    "table_id": 1,
    "id": 0
}, id_token)

print("已更新 noodle 這一筆")

# ✅ 讀取全部 product
products = db.child("product").get(id_token)
print("目前 product：")
for item in products.each():
    print(item.key(), "=>", item.val())
