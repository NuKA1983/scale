from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import datetime

Base = declarative_base()

class Truck(Base):
    __tablename__ = 'trucks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    unit_id = Column(String, nullable=False, unique=True)
    company_name = Column(String, nullable=False)
    asga_id = Column(String, unique=True, nullable=True)
    tare_weight = Column(Float, nullable=False)
    max_allowed_weight = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_used_timestamp = Column(DateTime, nullable=True) 

    weight_tickets = relationship("WeightTicket", back_populates="truck")

    def to_dict(self): 
        return {
            "id": self.id,
            "unit_id": self.unit_id,
            "company_name": self.company_name,
            "asga_id": self.asga_id,
            "tare_weight": self.tare_weight,
            "max_allowed_weight": self.max_allowed_weight,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_timestamp": self.last_used_timestamp.isoformat() if self.last_used_timestamp else None
        }


class AggregateType(Base):
    __tablename__ = 'aggregate_types'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    weight_tickets = relationship("WeightTicket", back_populates="aggregate_type")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class DeliveryLocation(Base):
    __tablename__ = 'delivery_locations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    weight_tickets = relationship("WeightTicket", back_populates="delivery_location")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class WeightTicket(Base):
    __tablename__ = 'weight_tickets'
    id = Column(Integer, primary_key=True, autoincrement=True)
    truck_id = Column(Integer, ForeignKey('trucks.id'), nullable=False)
    aggregate_type_id = Column(Integer, ForeignKey('aggregate_types.id'), nullable=False)
    delivery_location_id = Column(Integer, ForeignKey('delivery_locations.id'), nullable=False)
    gross_weight = Column(Float, nullable=False)
    tare_weight_at_weighing = Column(Float, nullable=False)
    net_weight = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    operator_name = Column(String, nullable=True)
    ticket_printed = Column(Boolean, default=False)

    truck = relationship("Truck", back_populates="weight_tickets")
    aggregate_type = relationship("AggregateType", back_populates="weight_tickets")
    delivery_location = relationship("DeliveryLocation", back_populates="weight_tickets")

    def to_dict(self): # Also useful for WeighTicket if it were to be audited directly for updates
        return {
            "id": self.id,
            "truck_id": self.truck_id,
            "aggregate_type_id": self.aggregate_type_id,
            "delivery_location_id": self.delivery_location_id,
            "gross_weight": self.gross_weight,
            "tare_weight_at_weighing": self.tare_weight_at_weighing,
            "net_weight": self.net_weight,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "operator_name": self.operator_name,
            "ticket_printed": self.ticket_printed
        }


class AuditLog(Base):
    __tablename__ = 'audit_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String, nullable=False)
    record_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False) # INSERT, UPDATE, DELETE
    changed_by = Column(String, nullable=True) # Could be operator_name or a system user
    changed_at = Column(DateTime, default=datetime.datetime.utcnow)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
