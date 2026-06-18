# ShopNest — Microservices E-Commerce Backend

> A production-ready microservices architecture built with Django, FastAPI, Redis, and Docker. Four independent services communicate through an API Gateway and Redis message queue — demonstrating real-world distributed system design.

---

## The Problem

Monolithic applications scale poorly. When one feature is slow, the entire app suffers. When one part fails, everything goes down.

**ShopNest solves this with microservices.** Each service is independent — deployed, scaled, and maintained separately. A spike in product traffic doesn't affect authentication. A notification failure doesn't bring down the store.

---

## Architecture

```
                        Client
                          │
                          ▼
              ┌───────────────────────┐
              │      API Gateway      │
              │      FastAPI          │
              │      Port: 8000       │
              │  - Single entry point │
              │  - Request routing    │
              │  - Health monitoring  │
              └───────────┬───────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Auth Service │ │Product Serv. │ │Notif. Service│
│   Django     │ │   FastAPI    │ │   FastAPI    │
│  Port: 8001  │ │  Port: 8002  │ │  Port: 8003  │
│  SQLite/PG   │ │  SQLite/PG   │ │  Redis Sub   │
└──────────────┘ └──────┬───────┘ └──────┬───────┘
                        │                │
                        └────────────────┘
                                │
                         ┌──────▼──────┐
                         │    Redis    │
                         │  Pub/Sub    │
                         │  Channel:   │
                         │product-evts │
                         └─────────────┘
```

### Inter-Service Communication

```
User creates product:
1. Client → Gateway (POST /api/products/)
2. Gateway → Product Service
3. Product Service → Auth Service (verify JWT)
4. Product Service → saves to DB
5. Product Service → publishes to Redis "product-events"
6. Notification Service → receives event from Redis
7. Notification Service → sends email to user ✅
```

---

## Services

### 1. API Gateway (FastAPI — Port 8000)
Single entry point for all client requests. Routes to appropriate services, monitors health of all services.

**Endpoints:**
- `GET /` — Gateway info
- `GET /health` — All services health status
- `GET /docs` — Swagger UI

### 2. Auth Service (Django — Port 8001)
Handles all authentication and user management. Issues JWT tokens used by other services.

**Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register/` | Register new user |
| `POST` | `/api/auth/login/` | Login → JWT token |
| `POST` | `/api/auth/token/refresh/` | Refresh JWT |
| `GET` | `/api/auth/profile/` | Get user profile |
| `GET` | `/api/auth/verify/` | Verify JWT token |
| `GET` | `/api/auth/health/` | Service health |

### 3. Product Service (FastAPI — Port 8002)
Full product catalog management. Verifies JWT by calling Auth Service. Publishes events to Redis on product changes.

**Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/products/` | Create product (auth required) |
| `GET` | `/api/products/` | List products (search, filter, paginate) |
| `GET` | `/api/products/{id}` | Get single product |
| `PUT` | `/api/products/{id}` | Update product |
| `DELETE` | `/api/products/{id}` | Soft delete product |
| `PATCH` | `/api/products/{id}/stock` | Update stock + low stock alert |
| `GET` | `/health` | Service health |

### 4. Notification Service (FastAPI — Port 8003)
Listens to Redis Pub/Sub channel. Sends email notifications on product events. Completely decoupled — other services don't wait for it.

**Redis Events handled:**
| Event | Trigger | Action |
|-------|---------|--------|
| `product_created` | New product added | Welcome email to creator |
| `low_stock_alert` | Stock < 10 units | Alert email to creator |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Gateway | FastAPI + httpx |
| Auth Service | Django 4.2 + DRF + SimpleJWT |
| Product Service | FastAPI + SQLAlchemy |
| Notification Service | FastAPI + Redis Pub/Sub |
| Message Broker | Redis |
| Databases | PostgreSQL (prod) / SQLite (dev) |
| Containerization | Docker + Docker Compose |

---

## Local Setup

### Option A — Run with Docker (Recommended)

```bash
git clone https://github.com/sagarkumarr1/shopnest.git
cd shopnest

# Build and start all services
docker-compose up --build
```

All 4 services start with one command. PostgreSQL and Redis included.

### Option B — Run without Docker (Windows)

Open 4 terminals:

**Terminal 1 — Auth Service:**
```bash
cd auth-service
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8001
```

**Terminal 2 — Product Service:**
```bash
cd product-service
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

**Terminal 3 — Notification Service:**
```bash
cd notification-service
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

**Terminal 4 — API Gateway:**
```bash
cd api-gateway
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

| Service | URL | Docs |
|---------|-----|------|
| API Gateway | http://localhost:8000 | http://localhost:8000/docs |
| Auth Service | http://localhost:8001 | http://localhost:8001/docs |
| Product Service | http://localhost:8002 | http://localhost:8002/docs |
| Notification Service | http://localhost:8003 | http://localhost:8003/docs |

---

## Testing the Full Flow

### Step 1 — Check all services are healthy
```bash
curl http://localhost:8000/health
```
```json
{
  "gateway": "healthy",
  "services": {
    "auth": "healthy",
    "product": "healthy",
    "notification": "healthy"
  },
  "status": "ok"
}
```

### Step 2 — Register a user
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "sagar", "email": "sagar@example.com", "password": "Test1234!"}'
```

### Step 3 — Create a product (with JWT token)
```bash
curl -X POST http://localhost:8000/api/products/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token>" \
  -d '{
    "name": "iPhone 15 Pro",
    "description": "Latest Apple iPhone",
    "price": 129999.00,
    "stock": 50,
    "category": "Electronics"
  }'
```

Notification Service automatically sends a confirmation email via Redis Pub/Sub.

### Step 4 — Trigger low stock alert
```bash
curl -X PATCH http://localhost:8000/api/products/1/stock \
  -H "Authorization: Bearer <your_token>" \
  -d '{"quantity": -45}'
```

Stock drops below 10 → Redis event → Email alert sent automatically.

---

## Key Design Decisions

**Why API Gateway?**
Single entry point simplifies client code. No need to know which service handles what. Centralizes cross-cutting concerns like CORS and logging.

**Why Redis Pub/Sub for notifications?**
Product Service doesn't wait for email to be sent. If Notification Service is down, Product Service still works. When Notification Service comes back up, it processes queued events. This is **loose coupling**.

**Why separate databases per service?**
Each service owns its data. Schema changes in one service don't affect others. Services can choose the right database for their needs.

**Why JWT verification via HTTP call?**
Product Service calls Auth Service to verify tokens — no shared secret between services. Auth Service is the single source of truth for authentication.

---

## Project Structure

```
shopnest/
├── docker-compose.yml          # One-command startup
│
├── api-gateway/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py                 # Proxy routing to all services
│
├── auth-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py
│   ├── config/
│   │   ├── settings.py
│   │   └── urls.py
│   └── users/
│       ├── models.py           # Custom User model
│       ├── serializers.py      # Register + User serializers
│       ├── views.py            # Register, Profile, Verify endpoints
│       └── urls.py
│
├── product-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # All product endpoints + Redis publish
│   ├── database.py             # SQLAlchemy setup
│   ├── models.py               # Product model
│   ├── schemas.py              # Pydantic schemas
│   └── auth.py                 # JWT verify via Auth Service HTTP call
│
└── notification-service/
    ├── Dockerfile
    ├── requirements.txt
    └── main.py                 # Redis subscriber + email sender
```

---

## What I Learned Building This

- Microservices architecture — when to use it and the tradeoffs vs monolith
- API Gateway pattern — single entry point, routing, health monitoring
- Inter-service communication — synchronous (HTTP) vs asynchronous (Redis Pub/Sub)
- Service isolation — each service has its own database and codebase
- Docker Compose — running multiple services with one command
- Loose coupling — Notification Service is completely independent; failures don't cascade
- JWT verification across services — Auth Service as single source of truth
- Health check patterns — monitoring all services from one endpoint

---

## Author

**Sagar Kumar**
- GitHub: [@sagarkumarr1](https://github.com/sagarkumarr1)
- LinkedIn: [linkedin.com/in/imsagar07](https://linkedin.com/in/imsagar07)
- Email: sagarkumar844122@gmail.com
