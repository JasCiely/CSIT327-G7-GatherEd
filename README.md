# GatherEd
**Course**: IT317-G1 CSIT327-G7

**Title**: School Event / Club Management

This project aims to develop a web-based application that centralizes event and club
management for schools. The system will allow students to easily register for events,
view announcements, and provide feedback. Administrators will be able to track
attendance, manage participants, and send reminders. Built using Python
(Flask/Django) for both frontend and backend, and MySQL for data storage, the
prototype will improve coordination, reduce reliance on manual sign-ups, and enhance
student engagement in extracurricular activities.

## Tech Stack
backend: Django (Python)

Database: Supabase

Frontend: Django Templates + HTML + CSS

Deployment: Render (Backend + Forntend), Supabase(database)

# Environment Setup
*1. Create a .env File*

In the project root directory (same level as manage.py), create a file named .env.

*2. Add Supabase Credentials*

Insert your Supabase credentials inside .env:

### env
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-anon-or-service-key

*3. Install Python Dependencies*

*Activate virtual environment (Windows):*

venv\Scripts\activate

*Install requirements:*

pip install -r requirements.txt

*4. Run Local Server*

python manage.py runserver
# Team Members
**Yabao, Christian Ken** – Product Owner - [christianken.yabao@cit.edu]()

**Villarta, John Hector** – Business Analyst  - [johnhector.villarta@cit.edu]()

**Villas, Ervin Louis** – Scrum Master - [ervinlouis.villas@cit.edu]()

**Palicte, Jasmine Ciely** - Lead Developer - [jasminciely.palicte@cit.edu]()

**Ruperez, Raymart** - Backend Developer - [raymart.ruperez@cit.edu]()

**Rosel, Patricia** - Frontend Developer - [patriciamae.rosel@cit.edu]()