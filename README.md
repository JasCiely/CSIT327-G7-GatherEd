# GatherEd: School Event & Club Management 

**Tired of lost sign-up sheets and chaotic communication?** **GatherEd** is a centralized web-based platform designed to simplify event organization and attendance tracking for your entire school community. We help schools improve efficiency and boost student engagement in extracurricular activities.

| 📚 **Course** | **IT317-G1 / CSIT327-G7** |
| :--- | :--- |

---

## 🚀 Core Features & Benefits

GatherEd moves beyond manual processes, providing a seamless experience for students, club leaders, and administrators.

| Feature | Description | Benefit |
| :--- | :--- | :--- |
| **Digital Sign-Ups** | Reliable, paperless system for event and club registration. | Automatically records participation and eliminates manual tracking. |
| **Attendance Tracking** | Effortlessly log attendance for any event or meeting. | Gives administrators **accurate data and insights** into student involvement. |
| **Club Management** | Dedicated dashboard for club leaders to manage events and members. | **Empowers** leaders and centralizes club operations. |
| **Data Centralization** | Attendance and participation records are automatically stored. | Provides a **transparent and structured history** for better coordination. |

---

## 💡 How GatherEd Works

1.  **Create an Event:** Administrators or empowered club leaders can quickly create and publish a new event with all the necessary details.
2.  **Students Sign Up:** Students easily discover and sign up for events and clubs from a single, intuitive dashboard.
3.  **Gathered Data:** Attendance and participation records are automatically stored, providing a transparent and structured history.

---

## 🏗️ Technical Architecture (The Stack)

GatherEd is built for performance, scalability, and maintainability using the following technologies:

| **Layer** | **Technology** |
| :---- | :---------- |
| **Backend** | Django (Python) |
| **Database** | Supabase |
| **Frontend** | Django Templates + HTML + CSS |
| **Deployment** | Render (Backend + Frontend) + Supabase (Database) |

---

## 🛠️ Environment Setup

Follow these steps to get GatherEd running on your local machine. **We recommend using Python 3.13.**

### 1. Configure the `.env` File

In the project root directory (same level as `manage.py`), create a file named `.env` and add your Supabase credentials:

### 2. Set Up Virtual Environment

It is crucial to use a virtual environment to manage dependencies.

* **Activate virtual environment (Windows):**
    ```bash
    venv\Scripts\activate
    ```
* **Troubleshooting:** If the virtual environment (`.venv`) causes issues, delete the folder and create a new one:
    ```bash
    # Delete existing .venv folder
    rm -r .venv
    # Create new .venv
    python -m venv .venv
    # Then re-activate
    venv\Scripts\activate
    ```

### 3. Install Python Dependencies

With your virtual environment active, install all necessary project libraries and packages. This step ensures that your local environment has the exact versions of tools (like **Django** and its dependencies) required to run **GatherEd**.

* **Command:**
    ```bash
    pip install -r requirements.txt
    ```

### 4. Run Local Server

Start the Django development server to access the application in your browser.

* **Command:**
    ```bash
    python manage.py runserver
    ```

---

## 👥 Project Team

| Role | Name | Contact |
| :--- | :--- | :--- |
| **Product Owner** | Yabao, Christian Ken | [christianken.yabao@cit.edu]() |
| **Business Analyst** | Villarta, John Hector | [johnhector.villarta@cit.edu]() |
| **Scrum Master** | Villas, Ervin Louis | [ervinlouis.villas@cit.edu]() |
| **Lead Developer** | Palicte, Jasmine Ciely | [jasminciely.palicte@cit.edu]() |
| **Backend Developer** | Ruperez, Raymart | [raymart.ruperez@cit.edu]() |
| **Frontend Developer** | Rosel, Patricia | [patriciamae.rosel@cit.edu]() |
