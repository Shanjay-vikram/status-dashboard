# HardwareCare – Hardware Problem Tracking Dashboard

A Flask + SQLite web application with Admin and Client roles, issue tracking, rectification progress, charts and print-to-PDF reports.

## Requirements
- Python 3.9+
- pip

## Run on Windows
1. Extract the ZIP.
2. Open PowerShell in the extracted `hardware_problem_dashboard` folder.
3. Create a virtual environment (recommended):
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
5. Start the application:
   ```powershell
   python app.py
   ```
6. Open http://127.0.0.1:5000

## Demo logins
- Admin: `admin` / `Admin@123`
- Client: `client1` / `Client@123`

The first run creates `dashboard.db` and sample issue records. The demo client can only see issues assigned to **Acme Manufacturing**. Admin can see all clients, create/update problems and create client accounts.

## Main features
- Admin dashboard with issue counts and status distribution chart.
- Client dashboard restricted to the client name attached to the account.
- Add and update problem statements, root cause, action taken, status, assigned engineer, target date, verification and remarks.
- Rectification percentage from 0–100.
- Issue detail view.
- Export dashboard or an individual issue as PDF using the browser's **Export PDF** button, then choose **Save as PDF** in the print dialog.
- Search/filter the problem table.

## Important production checklist
This is a runnable starter/demo, not a production security certification. Before internet deployment:
- Set a long random `SECRET_KEY` environment variable.
- Turn off Flask debug mode and run behind a production WSGI server with HTTPS.
- Add CSRF protection, password reset/change workflows, login rate limiting and audit logs.
- Use stronger tenant isolation based on immutable client IDs rather than matching company-name text.
- Configure backups and a managed database.
- Review privacy, access-control and hosting requirements with your IT/security team.

Chart.js and Google Fonts are loaded from public CDNs; an internet connection is needed for those visual assets. The rest of the app runs locally.
