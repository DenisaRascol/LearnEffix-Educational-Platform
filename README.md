# LearnEffix - Educational Web Platform

LearnEffix is a full-stack web application designed for academic management and automated test evaluation, developed as a Bachelor’s thesis project. The system streamlines classroom management between teachers and students while providing automated content generation and context-aware assessments powered by artificial intelligence.

## Features

### Academic Management & Access Control
* **Role-Based Authentication**: Secure authentication and authorization system with distinct permissions for Teachers and Students.
* **Data Persistence**: Structured database architecture with automated migrations for managing classes, learning materials, and assessments.

### AI Integration & Automated Evaluation
* **Groq AI Content Generation**: Integrates the Groq API (Llama 3.3 model) for context-aware query processing, automated test creation, and grading assistance.
* **Streamlined Workflows**: Structured input validation and RESTful endpoints designed to handle automated evaluation workflows efficiently.

### System Architecture
* **RESTful Endpoints**: Clean API structure ensuring seamless communication between the frontend interface and Django backend.
* **Dedicated Dashboards**: User-friendly interfaces for viewing, uploading, and managing courses, materials, and quizzes.

---

## Tech Stack & Tooling

* **Backend**: Python, Django
* **Frontend**: HTML5, CSS3, JavaScript
* **AI Integration**: Groq API (Llama 3.3)
* **Database**: SQLite / PostgreSQL (Django ORM)
* **Version Control**: Git, GitHub

---

## Getting Started

### Prerequisites
Ensure you have Python (version 3.10 or higher) and `pip` installed on your system.

### 1. Clone the Repository
```bash
git clone [https://github.com/DenisaRascol/LearnEffix-Educational-Platform.git](https://github.com/DenisaRascol/LearnEffix-Educational-Platform.git)
cd LearnEffix-Educational-Platform
