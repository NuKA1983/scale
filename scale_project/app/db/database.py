import json
import datetime # Required for datetime.datetime.utcnow
from sqlalchemy import create_engine, inspect, text, or_ 
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from .models import Base, Truck, AggregateType, DeliveryLocation, WeightTicket, AuditLog

DATABASE_URL = "sqlite:///./scale_project.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def migrate_and_create_db_and_tables():
    inspector = inspect(engine)
    if 'trucks' in inspector.get_table_names():
        columns = inspector.get_columns('trucks')
        if not any(c['name'] == 'last_used_timestamp' for c in columns):
            print("Migrating 'trucks' table: Adding 'last_used_timestamp' column.")
            try:
                with engine.connect() as connection:
                    connection.execute(text('ALTER TABLE trucks ADD COLUMN last_used_timestamp DATETIME'))
                    connection.commit()
                print("'last_used_timestamp' column added successfully.")
            except Exception as e:
                print(f"Error adding 'last_used_timestamp' column: {e}")
    else:
        print("'trucks' table not found, will be created.")

    Base.metadata.create_all(bind=engine)
    print("Database tables ensured/created.")

create_db_and_tables = migrate_and_create_db_and_tables

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Generic Model to Dict ---
# Though models have to_dict(), a generic one might be useful if to_dict() isn't on all models
# For now, relying on individual to_dict() methods.

# --- Truck CRUD Operations ---
def add_truck(db_session: Session, unit_id: str, company_name: str, tare_weight: float, max_allowed_weight: float, asga_id: str = None) -> Truck | None:
    if not unit_id or not company_name:
        print("Error: Unit ID and Company Name cannot be empty."); return None
    try:
        new_truck = Truck(
            unit_id=unit_id, company_name=company_name, tare_weight=tare_weight,
            max_allowed_weight=max_allowed_weight, asga_id=asga_id if asga_id else None
        )
        db_session.add(new_truck); db_session.commit(); db_session.refresh(new_truck)
        add_audit_log_entry(db_session, "Trucks", new_truck.id, "INSERT", new_values=new_truck.to_dict())
        return new_truck
    except IntegrityError:
        db_session.rollback(); print(f"Error: Truck with Unit ID '{unit_id}' or ASGA ID '{asga_id}' already exists."); return None
    except Exception as e:
        db_session.rollback(); print(f"Unexpected error adding truck: {e}"); return None

def update_truck(db_session: Session, truck_id: int, **kwargs) -> Truck | None:
    try:
        truck_to_update = db_session.query(Truck).filter(Truck.id == truck_id).first()
        if not truck_to_update:
            print(f"Error: Truck with ID {truck_id} not found for update."); return None

        old_values = truck_to_update.to_dict() # Capture state before update

        for key, value in kwargs.items():
            if hasattr(truck_to_update, key):
                # Ensure None for optional fields if empty string is passed from UI
                if key == 'asga_id' and value == '':
                    value = None
                setattr(truck_to_update, key, value)
            else:
                print(f"Warning: Attribute {key} not found on Truck model.")
        
        # updated_at should be handled by SQLAlchemy's onupdate
        db_session.commit()
        db_session.refresh(truck_to_update)

        add_audit_log_entry(db_session, "Trucks", truck_to_update.id, "UPDATE", 
                            old_values=old_values, new_values=truck_to_update.to_dict())
        return truck_to_update
    except IntegrityError: # Catch issues like unique constraint violation on unit_id or asga_id
        db_session.rollback()
        print(f"Error updating truck ID {truck_id}: Data integrity issue (e.g., duplicate Unit ID or ASGA ID).")
        return None
    except Exception as e:
        db_session.rollback(); print(f"Unexpected error updating truck ID {truck_id}: {e}"); return None


def get_all_trucks_mru_ordered(db_session: Session) -> list[Truck]:
    try:
        return db_session.query(Truck).order_by(
            Truck.last_used_timestamp.desc().nullslast(), Truck.company_name, Truck.unit_id
        ).all()
    except Exception as e: print(f"Error retrieving MRU trucks: {e}"); return []

def search_trucks(db_session: Session, search_term: str) -> list[Truck]:
    if not search_term: return get_all_trucks_mru_ordered(db_session)
    search_pattern = f"%{search_term.lower()}%"
    try: # Try with ILIKE first (PostgreSQL, etc.)
        return db_session.query(Truck).filter(
            or_(Truck.unit_id.ilike(search_pattern), Truck.company_name.ilike(search_pattern), Truck.asga_id.ilike(search_pattern))
        ).order_by(Truck.last_used_timestamp.desc().nullslast(), Truck.company_name, Truck.unit_id).all()
    except Exception: # Fallback to LOWER for SQLite
        return db_session.query(Truck).filter(
            or_(Truck.unit_id.lower().like(search_pattern), Truck.company_name.lower().like(search_pattern), Truck.asga_id.lower().like(search_pattern))
        ).order_by(Truck.last_used_timestamp.desc().nullslast(), Truck.company_name, Truck.unit_id).all()
    
def get_truck_by_id(db_session: Session, truck_id: int) -> Truck | None:
    try: return db_session.query(Truck).filter(Truck.id == truck_id).first()
    except Exception as e: print(f"Error retrieving truck by ID '{truck_id}': {e}"); return None

# --- AggregateType CRUD ---
def add_aggregate_type(db_session: Session, name: str, description: str = None) -> AggregateType | None:
    if not name: print("Error: Aggregate Type name cannot be empty."); return None
    try:
        new_aggregate = AggregateType(name=name, description=description if description else None)
        db_session.add(new_aggregate); db_session.commit(); db_session.refresh(new_aggregate)
        add_audit_log_entry(db_session, "AggregateTypes", new_aggregate.id, "INSERT", new_values=new_aggregate.to_dict())
        return new_aggregate
    except IntegrityError:
        db_session.rollback(); print(f"Error: Aggregate Type with name '{name}' already exists."); return None
    except Exception as e:
        db_session.rollback(); print(f"Unexpected error adding aggregate type: {e}"); return None

def update_aggregate_type(db_session: Session, aggregate_type_id: int, **kwargs) -> AggregateType | None:
    try:
        agg_type_to_update = db_session.query(AggregateType).filter(AggregateType.id == aggregate_type_id).first()
        if not agg_type_to_update:
            print(f"Error: AggregateType ID {aggregate_type_id} not found."); return None
        
        old_values = agg_type_to_update.to_dict()
        for key, value in kwargs.items():
            if hasattr(agg_type_to_update, key):
                setattr(agg_type_to_update, key, value if value else None) # Ensure empty strings become None for description
            else: print(f"Warning: Attribute {key} not found on AggregateType.")
        
        db_session.commit(); db_session.refresh(agg_type_to_update)
        add_audit_log_entry(db_session, "AggregateTypes", agg_type_to_update.id, "UPDATE",
                            old_values=old_values, new_values=agg_type_to_update.to_dict())
        return agg_type_to_update
    except IntegrityError: # Unique name constraint
        db_session.rollback(); print(f"Error updating AggregateType ID {aggregate_type_id}: Name may already exist."); return None
    except Exception as e:
        db_session.rollback(); print(f"Unexpected error updating AggregateType ID {aggregate_type_id}: {e}"); return None

def get_all_aggregate_types(db_session: Session) -> list[AggregateType]:
    try: return db_session.query(AggregateType).order_by(AggregateType.name).all()
    except Exception as e: print(f"Error retrieving aggregate types: {e}"); return []

# --- DeliveryLocation CRUD ---
def add_delivery_location(db_session: Session, name: str, address: str = None) -> DeliveryLocation | None:
    if not name: print("Error: Delivery Location name cannot be empty."); return None
    try:
        new_location = DeliveryLocation(name=name, address=address if address else None)
        db_session.add(new_location); db_session.commit(); db_session.refresh(new_location)
        add_audit_log_entry(db_session, "DeliveryLocations", new_location.id, "INSERT", new_values=new_location.to_dict())
        return new_location
    except IntegrityError:
        db_session.rollback(); print(f"Error: Delivery Location with name '{name}' already exists."); return None
    except Exception as e:
        db_session.rollback(); print(f"Unexpected error adding delivery location: {e}"); return None

def update_delivery_location(db_session: Session, delivery_location_id: int, **kwargs) -> DeliveryLocation | None:
    try:
        loc_to_update = db_session.query(DeliveryLocation).filter(DeliveryLocation.id == delivery_location_id).first()
        if not loc_to_update:
            print(f"Error: DeliveryLocation ID {delivery_location_id} not found."); return None
        
        old_values = loc_to_update.to_dict()
        for key, value in kwargs.items():
            if hasattr(loc_to_update, key):
                setattr(loc_to_update, key, value if value else None) # Ensure empty strings become None for address
            else: print(f"Warning: Attribute {key} not found on DeliveryLocation.")

        db_session.commit(); db_session.refresh(loc_to_update)
        add_audit_log_entry(db_session, "DeliveryLocations", loc_to_update.id, "UPDATE",
                            old_values=old_values, new_values=loc_to_update.to_dict())
        return loc_to_update
    except IntegrityError: # Unique name constraint
        db_session.rollback(); print(f"Error updating DeliveryLocation ID {delivery_location_id}: Name may already exist."); return None
    except Exception as e:
        db_session.rollback(); print(f"Unexpected error updating DeliveryLocation ID {delivery_location_id}: {e}"); return None

def get_all_delivery_locations(db_session: Session) -> list[DeliveryLocation]:
    try: return db_session.query(DeliveryLocation).order_by(DeliveryLocation.name).all()
    except Exception as e: print(f"Error retrieving delivery locations: {e}"); return []


# --- WeightTicket CRUD ---
def add_weight_ticket(db_session: Session, truck_id: int, aggregate_type_id: int, 
                      delivery_location_id: int, gross_weight: float, 
                      tare_weight_at_weighing: float, net_weight: float, 
                      operator_name: str = None, ticket_printed: bool = False) -> WeightTicket | None:
    try:
        # Validations...
        truck_to_update = db_session.query(Truck).filter(Truck.id == truck_id).first() # Query for truck
        if not truck_to_update:
            print(f"Error: Truck with ID {truck_id} not found for ticket."); return None
        truck_to_update.last_used_timestamp = datetime.datetime.utcnow()
        db_session.add(truck_to_update)

        new_ticket = WeightTicket(
            truck_id=truck_id, aggregate_type_id=aggregate_type_id, delivery_location_id=delivery_location_id,
            gross_weight=gross_weight, tare_weight_at_weighing=tare_weight_at_weighing, net_weight=net_weight,
            operator_name=operator_name if operator_name else None, ticket_printed=ticket_printed
        )
        db_session.add(new_ticket)
        db_session.commit() 
        db_session.refresh(new_ticket); db_session.refresh(truck_to_update)
        # Audit log for weight ticket creation is done in WeighingWindow or similar UI logic
        return new_ticket
    except IntegrityError: 
        db_session.rollback(); print(f"Error adding weight ticket: FK constraint failed."); return None
    except Exception as e:
        db_session.rollback(); print(f"Unexpected error adding weight ticket: {e}"); return None

# --- AuditLog ---
def add_audit_log_entry(db_session: Session, table_name: str, record_id: int, action: str,
                        changed_by: str = None, old_values: dict | None = None, 
                        new_values: dict | WeightTicket | Truck | AggregateType | DeliveryLocation | None = None) -> AuditLog | None:
    try:
        new_values_json = None
        if isinstance(new_values, (Truck, AggregateType, DeliveryLocation, WeightTicket)):
            new_values_json = new_values.to_dict() # Use the to_dict method
        elif isinstance(new_values, dict):
            new_values_json = new_values
        
        old_values_json = old_values if isinstance(old_values, dict) else None

        entry = AuditLog(
            table_name=table_name, record_id=record_id, action=action, 
            changed_by=changed_by if changed_by else None,
            old_values=old_values_json, new_values=new_values_json
        )
        db_session.add(entry)
        # This commit is separate. If called from within another function that commits,
        # it might lead to nested transaction issues or commit prematurely.
        # Consider if audit log should be part of the same transaction as the main operation.
        # For now, let's assume it's fine or the calling function manages the overall session.
        # However, for update functions above, the audit log is called *before* the main commit,
        # so it's part of the same transaction. If add_weight_ticket calls this, it needs session.
        db_session.commit() 
        db_session.refresh(entry)
        return entry
    except Exception as e:
        db_session.rollback() # Rollback this specific audit log commit if it fails
        print(f"Error adding audit log entry: {e}")
        return None
