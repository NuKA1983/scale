import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from .database import get_local_db, get_remote_db
from .models import WeightTicket, Truck, AggregateType, DeliveryLocation

def create_ticket_locally(
    local_db: Session,
    truck_id: int,
    aggregate_type_id: int,
    delivery_location_id: int,
    gross_weight: float,
    tare_weight_at_weighing: float,
    net_weight: float,
    operator_name: str = None,
    ticket_printed: bool = False
) -> WeightTicket | None:
    """
    Creates a new weight ticket in the local database.
    Initially, it is marked as not synced.
    """
    try:
        # First, update the truck's last_used_timestamp in the local DB
        truck_to_update = local_db.query(Truck).filter(Truck.id == truck_id).first()
        if truck_to_update:
            truck_to_update.last_used_timestamp = datetime.datetime.utcnow()
            local_db.add(truck_to_update)

        new_ticket = WeightTicket(
            truck_id=truck_id,
            aggregate_type_id=aggregate_type_id,
            delivery_location_id=delivery_location_id,
            gross_weight=gross_weight,
            tare_weight_at_weighing=tare_weight_at_weighing,
            net_weight=net_weight,
            operator_name=operator_name,
            ticket_printed=ticket_printed,
            synced_to_remote=False,  # Explicitly set as not synced
            last_sync_timestamp=None
        )
        local_db.add(new_ticket)
        local_db.commit()
        local_db.refresh(new_ticket)
        print(f"Successfully created ticket {new_ticket.id} locally.")
        return new_ticket
    except Exception as e:
        local_db.rollback()
        print(f"Error creating weight ticket locally: {e}")
        return None

def sync_pending_tickets() -> tuple[int, int]:
    """
    Finds all tickets in the local database that have not been synced to the remote
    database and attempts to sync them.

    Returns a tuple of (successful_syncs, failed_syncs).
    """
    local_db_gen = get_local_db()
    remote_db_gen = get_remote_db()
    local_db = next(local_db_gen)
    remote_db = next(remote_db_gen)

    successful_syncs = 0
    failed_syncs = 0

    try:
        pending_tickets = local_db.query(WeightTicket).filter(WeightTicket.synced_to_remote == False).all()
        if not pending_tickets:
            print("No pending tickets to sync.")
            return 0, 0

        print(f"Found {len(pending_tickets)} pending tickets to sync.")

        for ticket in pending_tickets:
            try:
                # Check if a ticket with the same local ID already exists on the remote
                # This is a simple check; more complex logic might be needed for conflicts
                existing_remote_ticket = remote_db.query(WeightTicket).filter(WeightTicket.id == ticket.id).first()
                if existing_remote_ticket:
                    print(f"Ticket {ticket.id} already exists on remote. Marking as synced.")
                    ticket.synced_to_remote = True
                    ticket.last_sync_timestamp = datetime.datetime.utcnow()
                    local_db.commit()
                    successful_syncs += 1
                    continue

                # Recreate the ticket object for the new session
                remote_ticket = WeightTicket(
                    id=ticket.id,  # Preserve the same ID
                    truck_id=ticket.truck_id,
                    aggregate_type_id=ticket.aggregate_type_id,
                    delivery_location_id=ticket.delivery_location_id,
                    gross_weight=ticket.gross_weight,
                    tare_weight_at_weighing=ticket.tare_weight_at_weighing,
                    net_weight=ticket.net_weight,
                    timestamp=ticket.timestamp,
                    operator_name=ticket.operator_name,
                    ticket_printed=ticket.ticket_printed,
                    synced_to_remote=True, # It will be synced on the remote
                    last_sync_timestamp=datetime.datetime.utcnow()
                )

                remote_db.add(remote_ticket)
                remote_db.commit()

                # If successful, update the local ticket's status
                ticket.synced_to_remote = True
                ticket.last_sync_timestamp = datetime.datetime.utcnow()
                local_db.commit()

                print(f"Successfully synced ticket {ticket.id} to remote.")
                successful_syncs += 1

            except OperationalError as oe:
                print(f"A database connection error occurred while syncing ticket {ticket.id}: {oe}")
                print("Aborting sync process. Will retry later.")
                remote_db.rollback()
                # Stop the sync process if the remote DB is down
                return successful_syncs, len(pending_tickets) - successful_syncs

            except Exception as e:
                print(f"Failed to sync ticket {ticket.id} to remote: {e}")
                remote_db.rollback()
                failed_syncs += 1

        return successful_syncs, failed_syncs

    finally:
        local_db.close()
        remote_db.close()

def get_recent_local_tickets(hours: int = 24) -> list[WeightTicket]:
    """
    Retrieves all weight tickets from the local database created in the last N hours.

    Args:
        hours (int): The number of hours to look back for tickets.

    Returns:
        A list of WeightTicket objects.
    """
    local_db_gen = get_local_db()
    local_db = next(local_db_gen)
    try:
        time_threshold = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        recent_tickets = local_db.query(WeightTicket).filter(WeightTicket.timestamp >= time_threshold).order_by(WeightTicket.timestamp.desc()).all()
        return recent_tickets
    except Exception as e:
        print(f"Error retrieving recent local tickets: {e}")
        return []
    finally:
        local_db.close()