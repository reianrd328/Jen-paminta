# 🍇 Jen & Albert Paminta - Inventory & Sales Management System

A full-stack, enterprise-grade web system for **Jen & Albert Paminta** featuring **Python (Flask)**, **HTML5/CSS3/JavaScript**, and **MySQL / TiDB Cloud**, featuring an aesthetic crafted to match the circular gold & forest-green emblem.

---

## 🌟 Key Features

### 1. 📦 Beginning & Ending Inventory Reconciliation Ledger
- **Beginning Inventory**: Records opening stock per item for any accounting period.
- **Stock-In (+ Restock / Add Stock)**: Dedicated modal to add inventory with batch numbers, supplier info, and notes.
- **Stock-Out (- Less / Adjust Stock)**: Deduct stock for damage, spoilage, shrinkage, sampling, or count corrections.
- **Ending Inventory**: Live formula calculation:
  $$\text{Ending Stock} = \text{Beginning Stock} + \text{Stock Added} - \text{Sales Deductions} - \text{Less Adjustments}$$
- **Audit Movements Trail**: Complete historical ledger recording every addition, deduction, sale, and adjustment with timestamps and user notes.

### 2. 🛒 Sales Module & POS Connected to Inventory
- **Automated Stock Deduction**: Every sale placed through the POS terminal or online store immediately deducts from available inventory in real time (`SALE_DEDUCTION`).
- **Insufficient Stock Prevention**: Prevents overselling with real-time stock validations.
- **Thermal & Standard Printable Receipts**: Generates branded customer invoices with invoice numbers (`INV-PAM-YYYYMMDD-XXXX`).
- **Void / Restock Option**: Voiding a transaction automatically restores items back to inventory (`ADJUSTMENT_ADD`).

### 3. 🎨 Bespoke Luxury Design Matching Logo
- Directly adopts the **Jen & Albert Paminta** emblem:
  - **Vineyard Deep Forest Green** (`#1A382B`)
  - **Antique Heritage Gold** (`#C5A059`)
  - **Warm Parchment / Linen** (`#FAF6F0`)
  - **Royal Berry / Grape Accent** (`#4A154B`)
- High-resolution logo integrated across topbar, hero section, modals, login screen, and receipts.

### 4. 🌐 Public Customer Storefront
- Mobile-responsive product catalog with real-time stock badges.
- Interactive shopping basket and online order checkout.
- Customer order tracking lookup by invoice number.

---

## 🚀 Quick Start (Local Run)

### 1. Prerequisites
- Python 3.10+ installed.

### 2. Setup Virtual Environment
```bash
# In project folder:
python -m venv venv
.\venv\Scripts\activate

# Install dependencies:
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python run.py
```
Open your browser:
- **Public Storefront**: [http://localhost:5000/](http://localhost:5000/)
- **Admin Management Portal**: [http://localhost:5000/admin](http://localhost:5000/admin)
- **Staff Login**: [http://localhost:5000/login](http://localhost:5000/login) (Default credentials: `admin` / `admin123`)

*(Note: If TiDB credentials are not yet set in `.env`, the system automatically runs on local SQLite `backend/data.db` with all seed data populated, so you can test immediately without setup!)*

---

## ☁️ Live Cloud Deployment (GitHub + Render + TiDB Cloud)

### Step 1: Create a Free TiDB Serverless Database
1. Go to [TiDB Cloud](https://tidbcloud.com) and create a free account.
2. Click **Create Cluster** and select **Serverless** (Free forever).
3. Once the cluster is created, click **Connect**:
   - Choose connection method: **General** or **Python**.
   - Copy your **Host**, **Port (4000)**, **User**, and **Password**.
   - Note down the database name (default: `test` or create `jen_paminta`).

### Step 2: Push Your Project to GitHub
Initialize your Git repository and push:
```bash
git init
git add .
git commit -m "Initial commit: Jen & Albert Paminta Inventory & Sales System"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/jen-paminta.git
git push -u origin main
```

### Step 3: Deploy to Render.com
1. Sign in to [Render](https://render.com).
2. Click **New +** -> **Web Service**.
3. Connect your GitHub repository `jen-paminta`.
4. Configure the settings:
   - **Name**: `jen-paminta`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `gunicorn --chdir backend wsgi:app -b 0.0.0.0:$PORT`
5. In **Environment Variables**, add:
   | Key | Value | Note |
   | :--- | :--- | :--- |
   | `DB_HOST` | `gateway01.ap-southeast-1.prod.aws.tidbcloud.com` | From TiDB Cloud |
   | `DB_PORT` | `4000` | TiDB Default |
   | `DB_USER` | `xxxxxx.root` | From TiDB Cloud |
   | `DB_PASSWORD` | `your_tidb_password` | From TiDB Cloud |
   | `DB_NAME` | `jen_paminta` | Target database |
   | `DB_USE_SSL` | `true` | Required for TiDB Serverless |
   | `SECRET_KEY` | *(generate a random string)* | Security secret |
   | `ADMIN_USERNAME` | `admin` | Admin username |
   | `ADMIN_PASSWORD` | `your_secure_password` | Admin password |

6. Click **Deploy Web Service**!
   Render will build the app, connect to TiDB Cloud over SSL, automatically initialize all database tables (`init_db()`), and launch your live URL: `https://jen-paminta.onrender.com`.

---

## 🛠 Project Structure

```
Jen-paminta/
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   │   ├── auth.py          # Login, logout, session
│   │   │   ├── products.py      # Products CRUD & stock status
│   │   │   ├── inventory.py     # Beginning/Ending ledger, add-stock, less-stock
│   │   │   ├── sales.py         # POS checkout with automatic stock deduction
│   │   │   ├── dashboard.py     # Metrics, KPIs, top selling, low stock
│   │   │   └── settings.py      # TiDB connection health check & estate settings
│   │   ├── __init__.py          # Flask factory & static routing
│   │   ├── config.py            # Environment configuration
│   │   └── db.py                # TiDB Cloud & MySQL connector with SSL & auto-seed
│   ├── schema.sql               # Relational SQL schema
│   ├── requirements.txt         # Python dependencies
│   └── wsgi.py                  # Gunicorn WSGI runner
├── frontend/
│   ├── assets/
│   │   ├── css/
│   │   │   ├── theme.css        # Luxury estate theme (Forest green & gold)
│   │   │   └── style.css        # Layout, POS, inventory ledger, print styles
│   │   ├── js/
│   │   │   ├── api.js           # REST API client & toast notifications
│   │   │   ├── admin.js         # Management portal, POS, modals, ledger
│   │   │   └── app.js           # Public storefront, cart, order tracking
│   │   └── images/
│   │       └── logo.jpg         # Jen & Albert Paminta circular emblem
│   ├── index.html               # Public storefront & catalog
│   ├── admin.html               # Executive management portal
│   └── login.html               # Luxury staff login page
├── .env.example                 # Template for TiDB credentials
├── .gitignore                   # Git ignore specifications
├── Procfile                     # Deployment process definition
├── render.yaml                  # Render blueprint configuration
├── requirements.txt             # Root requirements
├── run.py                       # Local development runner
└── README.md                    # Project documentation
```

---

## 🍇 License
© 2026 Jen & Albert Paminta Estate. All rights reserved.

