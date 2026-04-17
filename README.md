# RentalApp (Flask + MySQL)
### Skip to C if you already have a database set.
# A. Create database

Use this from project root:

```bash
bash RentalApp/setup_step1.sh root root
```
Arguments are: `mysql_user mysql_password`.

# B. Set environment variables (example):

```bash
export DATABASE_URL='mysql+pymysql://root:RealPasswordForMsqlServer@localhost/machinerental_flask'
export SECRET_KEY='change-this' --- use from config.py
```
# C. Install dependencies for Windows
## 1. Go to project root:
### for example:
```bash
cd ...\Flask_Project
```
## 2. Create virtual environment:
```bash
py -m venv .venv
```
## 3. Activate virtual environment:
```bash
.venv\Scripts\Activate.ps1
```
## 4. Install dependencies:
```bash
pip install -r RentalApp\requirements.txt
```
## 5. Run Flask app:
```bash
cd RentalApp
py app.py
```
## 6. Open `http://127.0.0.1:5000`.

# D. Install dependencies for MacOS / Linux
## 1. Go to project root:
### for example:
```bash
cd ...\Flask_Project
```
## 2. Create virtual environment:
```bash
python3 -m venv .venv
```
## 3. Activate virtual environment:
```bash
source .venv/bin/activate
```
## 4. Install dependencies:
```bash
pip install -r RentalApp\requirements.txt
```
## 5. Run Flask app:
```bash
cd RentalApp
python app.py
```
## 6 Open `http://127.0.0.1:5000`.

## Test users
```
user:admin pass:admin12345 (with admin rights)
user:hans pass:hans12345 (with user rights)
Use the Admin page in the web app (`/admin/users`) to add/update/delete other users.
```
## Roles
```
- `user`: full customer CRUD, read-only equipment, create/read/update rentals, no rental delete.
- `admin`: full rights.
```
## JSON endpoints
```
- `/rentals/api/active-rentals`
- `/rentals/api/equipment/available`
```


