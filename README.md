# SFS BusNest
This web application is designed to streamline student registration and bus seat allocation across multiple educational institutions. It provides a centralized platform managed by a central admin, responsible for overseeing bus assignments and routes. Students from various institutions can conveniently register for shared bus services. The primary goal of this project is to improve the efficiency of scheduling and managing buses while offering real-time seat availability and seamless communication for students, parents, and school administrators.

## Features
- **Centralized Bus Management:** Admin can manage buses and routes across multiple institutions.
- **Student Registration:** Simple registration process without the need for account creation.
- **Automated Seat Allocation:** Ensures no overbooking by only displaying available buses.
- **Real-Time Booking:** Students and parents can check seat availability and book buses in advance.
- **Dynamic Route Management:** Central admin can modify routes to accommodate special occasions or emergencies.
- **Special Schedules for KG Students:** Additional timing options for morning-evening or afternoon services.
- **Cancellations & Refunds:** Institutional admins can manage cancellations and communicate updates effectively.
- **Logging Mechanism:** Tracks critical actions for transparency and accountability.

## Technology Stack
- **Backend:** Django (Python)
- **Frontend:** HTML, SCSS, Bootstrap, JavaScript, HTMX
- **Database:** PostgreSQL, Redis
- **Hosting:** Digital Ocean, Railway
- **Email Service:** Mailjet

## Non-Functional Requirements
- **Security:** Secure authentication
- **Scalability:** Designed for expansion across multiple institutions and countries.
- **Usability:** Intuitive user interface for admins and users.
- **Responsiveness:** Fully responsive design for desktop and mobile use.

## Conclusion
This system aims to improve bus route management efficiency, enhance student safety, and offer a seamless booking experience for parents.

## 🚀 Quick Start for Developers

### Prerequisites
- Docker & Docker Compose

### Setup & Run
1. **Clone the Repository:**  
```bash
git clone https://github.com/joisemp/sfs-busnest.git
cd sfs-busnest
```

2. **Add .env file to 'src/config/':**
```
ENVIRONMENT=development
SECRET_KEY=your_secret_key
```

3. **Build & Run Containers:**
```
docker compose build
docker compose up
```
