"""Database models for Vigint billing system"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

db = SQLAlchemy()


class PaymentMethod(enum.Enum):
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    DIRECT_DEBIT = "direct_debit"


class PaymentFrequency(enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class Client(db.Model):
    __tablename__ = 'clients'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    api_keys = relationship("APIKey", back_populates="client")
    
    def __repr__(self):
        return f'<Client {self.name}>'


class APIKey(db.Model):
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="api_keys")
    usage_records = relationship("APIUsage", back_populates="api_key")
    payment_details = relationship("PaymentDetails", back_populates="api_key")
    
    def __repr__(self):
        return f'<APIKey {self.name} for client {self.client_id}>'


class APIUsage(db.Model):
    __tablename__ = 'api_usage'
    
    id = Column(Integer, primary_key=True)
    api_key_id = Column(Integer, ForeignKey('api_keys.id'), nullable=False)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, etc.
    status_code = Column(Integer, nullable=False)
    cost = Column(Float, nullable=False, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)
    request_data = Column(String(1000), nullable=True)  # JSON string of request details
    
    # Relationships
    api_key = relationship("APIKey", back_populates="usage_records")
    
    def __repr__(self):
        return f'<APIUsage {self.endpoint} - €{self.cost}>'


class PaymentDetails(db.Model):
    __tablename__ = 'payment_details'
    
    id = Column(Integer, primary_key=True)
    api_key_id = Column(Integer, ForeignKey('api_keys.id'), nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    payment_frequency = Column(Enum(PaymentFrequency), nullable=False, default=PaymentFrequency.MONTHLY)
    auto_pay_enabled = Column(Boolean, default=False)
    
    # Payment method specific fields
    stripe_customer_id = Column(String(255), nullable=True)  # For credit cards
    stripe_payment_method_id = Column(String(255), nullable=True)  # For credit cards
    bank_account_iban = Column(String(255), nullable=True)  # For bank transfers/direct debit
    bank_account_bic = Column(String(255), nullable=True)  # For bank transfers/direct debit
    
    # Billing tracking
    next_payment_date = Column(DateTime, nullable=True)
    last_payment_date = Column(DateTime, nullable=True)
    last_invoice_number = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    api_key = relationship("APIKey", back_populates="payment_details")
    
    def __repr__(self):
        return f'<PaymentDetails {self.payment_method.value} for API key {self.api_key_id}>'