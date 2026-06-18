from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from database import engine, Base, get_db
from models import Product
from schemas import ProductCreate, ProductUpdate, ProductResponse
from auth import verify_token
import redis
import json
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ShopNest Product Service",
    description="Product management microservice",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


@app.get("/health")
def health():
    return {"status": "healthy", "service": "product-service"}


@app.post("/api/products/", response_model=ProductResponse, status_code=201)
async def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # Redis pe publish karo — notification service sun raha hai
    redis_client.publish('product-events', json.dumps({
        'event': 'product_created',
        'product_id': db_product.id,
        'product_name': db_product.name,
        'user_email': current_user.get('email'),
        'user_id': current_user.get('user_id'),
    }))

    return db_product


@app.get("/api/products/", response_model=List[ProductResponse])
async def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Product).filter(Product.is_active == True)

    if category:
        query = query.filter(Product.category == category)

    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    return query.offset(skip).limit(limit).all()


@app.get("/api/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.put("/api/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


@app.delete("/api/products/{product_id}")
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = False
    db.commit()
    return {"message": "Product deleted successfully"}


@app.patch("/api/products/{product_id}/stock")
async def update_stock(
    product_id: int,
    quantity: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.stock + quantity < 0:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    product.stock += quantity
    db.commit()
    db.refresh(product)

    # Low stock alert
    if product.stock < 10:
        redis_client.publish('product-events', json.dumps({
            'event': 'low_stock_alert',
            'product_id': product.id,
            'product_name': product.name,
            'stock': product.stock,
            'user_email': current_user.get('email'),
        }))

    return {"product_id": product_id, "new_stock": product.stock}