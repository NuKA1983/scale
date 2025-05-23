from app.db.database import create_db_and_tables #, get_db, add_truck, get_truck_by_unit_id
from app.ui.main_window import MainApplicationWindow
# from app.scale_reader import ScaleReader # No longer directly used in main

def initialize_database():
    """Initializes the database and creates tables."""
    create_db_and_tables()
    print("Database initialized and tables created (if they didn't exist).")

def main():
    """Main function to start the application."""
    print("Starting Scale Interface Application...")
    
    # Initialize database (can be optional if UI doesn't depend on it immediately)
    # For this task, the UI is the focus and doesn't interact with DB yet.
    # initialize_database() 

    print("Initializing GUI...")
    app = MainApplicationWindow(update_interval_ms=500) # Create the main window
    app.mainloop() # Start the Tkinter event loop

    print("Application closed.")

if __name__ == "__main__":
    main()
