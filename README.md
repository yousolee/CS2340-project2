# CS2340 Project 2: Job Finder

## Overview
This is a Django web app that connects:
- Job seekers looking for opportunities
- Recruiters posting jobs and reviewing candidates
- Administrators managing users and platform content

Core features include account roles, profile management, job postings, job applications, and recommendation scoring.

## Local Setup and Run (Full Rundown)

### 1. Prerequisites
- Python 3.11+ (3.12 also works)
- `pip`
- `git`

### 2. Clone and enter the project
```bash
git clone <your-repo-url>
cd CS2340-project2
```

### 3. Create and activate a virtual environment
macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

Windows (PowerShell):
```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

### 4. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure environment variables
Create a `.env` file in the project root:

```env
# Optional: enables Cohere-powered embeddings when set
COHERE_API_KEY=

# Optional recommender settings (defaults shown)
RECOMMENDER_EMBEDDING_PROVIDER=cohere
RECOMMENDER_EMBEDDING_DIM=1024
RECOMMENDER_COHERE_MODEL=embed-v4.0
RECOMMENDER_COHERE_INPUT_TYPE=search_document
```

Notes:
- If `COHERE_API_KEY` is empty, recommendations still work using a local deterministic embedding fallback.
- SQLite is used by default (`db.sqlite3`).

### 6. Run database migrations
```bash
python manage.py migrate
```

### 7. Create an admin account (optional but recommended)
```bash
python manage.py createsuperuser
```

### 8. Start the development server
```bash
python manage.py runserver
```

Open: `http://127.0.0.1:8000/`

If port 8000 is in use:
```bash
python manage.py runserver 8001
```

### 9. First-time app usage flow
1. Go to `http://127.0.0.1:8000/accounts/signup` to create a user.
2. Choose `Job Seeker` or `Recruiter` during signup.
3. Log in at `http://127.0.0.1:8000/accounts/login/`.
4. For admin features:
   - Log in with a superuser account.
   - Visit `http://127.0.0.1:8000/accounts/admin-dashboard/` or `http://127.0.0.1:8000/admin/`.

### 10. Run tests
```bash
python manage.py test
```


