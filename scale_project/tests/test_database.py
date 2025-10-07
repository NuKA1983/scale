import unittest
import os
import datetime
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# It's better to use absolute imports from the project root for testing
# This requires running pytest from the root of the `scale_project` directory
from app.db.models import Base, WeightTicket, Truck, AggregateType, DeliveryLocation
from app.db.db_hybrid import create_ticket_locally, sync_pending_tickets, get_recent_local_tickets
from app.db.database import add_truck, add_aggregate_type, add_delivery_location

# Use in-memory SQLite databases for testing to avoid file I/O
LOCAL_TEST_DB_URL = "sqlite:///:memory:"
REMOTE_TEST_DB_URL = "sqlite:///:memory:"

class TestHybridDatabase(unittest.TestCase):

    def setUp(self):
        """Set up in-memory databases for each test."""
        # Setup local DB
        self.local_engine = create_engine(LOCAL_TEST_DB_URL)
        Base.metadata.create_all(self.local_engine)
        self.LocalSession = sessionmaker(autocommit=False, autoflush=False, bind=self.local_engine)

        # Setup "remote" DB
        self.remote_engine = create_engine(REMOTE_TEST_DB_URL)
        Base.metadata.create_all(self.remote_engine)
        self.RemoteSession = sessionmaker(autocommit=False, autoflush=False, bind=self.remote_engine)

        # Create some master data in both databases for consistency
        self.setup_master_data()

    def setup_master_data(self):
        """Pre-populates the databases with necessary master data (trucks, etc.)."""
        # We need to add this data to both the local and "remote" test DBs
        for session_maker in [self.LocalSession, self.RemoteSession]:
            db = session_maker()
            try:
                # Add a truck
                add_truck(db, "TEST01", "Test Corp", 5000, 15000)
                # Add an aggregate type
                add_aggregate_type(db, "Gravel")
                # Add a delivery location
                add_delivery_location(db, "Test Site")
            finally:
                db.close()

    def tearDown(self):
        """Tear down the in-memory databases."""
        Base.metadata.drop_all(self.local_engine)
        Base.metadata.drop_all(self.remote_engine)

    def test_01_create_ticket_locally(self):
        """Test that a ticket is created in the local database correctly."""
        local_db = self.LocalSession()
        try:
            ticket = create_ticket_locally(
                local_db=local_db,
                truck_id=1,
                aggregate_type_id=1,
                delivery_location_id=1,
                gross_weight=10000,
                tare_weight_at_weighing=5000,
                net_weight=5000,
                operator_name="Test Operator"
            )
            self.assertIsNotNone(ticket)
            self.assertEqual(ticket.id, 1)
            self.assertEqual(ticket.operator_name, "Test Operator")
            self.assertFalse(ticket.synced_to_remote) # Should be False initially

            # Verify it's in the DB
            retrieved_ticket = local_db.query(WeightTicket).filter(WeightTicket.id == 1).first()
            self.assertIsNotNone(retrieved_ticket)
            self.assertEqual(retrieved_ticket.net_weight, 5000)

        finally:
            local_db.close()

    def test_02_get_recent_local_tickets(self):
        """Test retrieving tickets created in the last 24 hours."""
        local_db = self.LocalSession()
        try:
            # Create a recent ticket
            create_ticket_locally(local_db, 1, 1, 1, 10000, 5000, 5000)
            # Create an old ticket
            old_ticket = WeightTicket(
                truck_id=1, aggregate_type_id=1, delivery_location_id=1,
                gross_weight=9000, tare_weight_at_weighing=5000, net_weight=4000,
                timestamp=datetime.datetime.utcnow() - datetime.timedelta(days=2)
            )
            local_db.add(old_ticket)
            local_db.commit()

            # Patch get_local_db to use our test session
            with patch('app.db.db_hybrid.get_local_db') as mock_get_local_db:
                mock_get_local_db.return_value = iter([self.LocalSession()])
                recent_tickets = get_recent_local_tickets(hours=24)

            self.assertEqual(len(recent_tickets), 1)
            self.assertEqual(recent_tickets[0].net_weight, 5000)

        finally:
            local_db.close()

    @patch('app.db.db_hybrid.get_remote_db')
    @patch('app.db.db_hybrid.get_local_db')
    def test_03_sync_pending_tickets_success(self, mock_get_local_db, mock_get_remote_db):
        """Test the successful synchronization of a pending ticket."""
        # Mock the DB getters to return our test sessions
        mock_get_local_db.return_value = iter([self.LocalSession()])
        mock_get_remote_db.return_value = iter([self.RemoteSession()])

        # 1. Create a ticket in the local DB
        local_db = self.LocalSession()
        create_ticket_locally(local_db, 1, 1, 1, 12000, 5000, 7000)
        local_db.close()

        # 2. Run the sync process
        successful, failed = sync_pending_tickets()
        self.assertEqual(successful, 1)
        self.assertEqual(failed, 0)

        # 3. Verify the ticket is marked as synced in local DB
        local_db = self.LocalSession()
        synced_ticket_local = local_db.query(WeightTicket).filter(WeightTicket.id == 1).first()
        self.assertTrue(synced_ticket_local.synced_to_remote)
        self.assertIsNotNone(synced_ticket_local.last_sync_timestamp)
        local_db.close()

        # 4. Verify the ticket exists in the remote DB
        remote_db = self.RemoteSession()
        synced_ticket_remote = remote_db.query(WeightTicket).filter(WeightTicket.id == 1).first()
        self.assertIsNotNone(synced_ticket_remote)
        self.assertEqual(synced_ticket_remote.net_weight, 7000)
        remote_db.close()

    @patch('app.db.db_hybrid.get_remote_db')
    @patch('app.db.db_hybrid.get_local_db')
    def test_04_sync_pending_tickets_remote_failure(self, mock_get_local_db, mock_get_remote_db):
        """Test that sync fails gracefully if the remote DB is down."""
        # Mock get_remote_db to raise an OperationalError
        mock_get_local_db.return_value = iter([self.LocalSession()])
        mock_remote_session = MagicMock()
        mock_remote_session.query.side_effect = Exception("Connection failed!")
        mock_get_remote_db.return_value = iter([mock_remote_session])

        # 1. Create a local ticket
        local_db = self.LocalSession()
        create_ticket_locally(local_db, 1, 1, 1, 12000, 5000, 7000)
        local_db.close()

        # 2. Run sync, expecting it to fail
        successful, failed = sync_pending_tickets()
        self.assertEqual(successful, 0)
        self.assertEqual(failed, 1)

        # 3. Verify the local ticket is still marked as not synced
        local_db = self.LocalSession()
        local_ticket = local_db.query(WeightTicket).filter(WeightTicket.id == 1).first()
        self.assertFalse(local_ticket.synced_to_remote)
        local_db.close()

if __name__ == "__main__":
    unittest.main()