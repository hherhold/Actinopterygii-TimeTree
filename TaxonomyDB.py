'''

gbif_species_db.py

This script is designed to interact with GBIF using the pygbif library to fetch taxonomy
data. It provides a function to retrieve species information based on genus and
returns the order and family of the given genus. 

Most importantly, it will cache the results in a SQLite database to avoid redundant API
calls, which is particularly useful for large datasets or repeated queries.

'''

from pygbif import species
import sqlite3
from sqlite3 import Error
import os
from Bio import Entrez
import taxidTools
import sys
# Database file path
DB_FILE = 'local_species.db'

class TaxonomyDB:
    """A class to handle taxonomy data. Some data is cached locally using SQLite."""
    
    def __init__(self, 
                 db_file=DB_FILE):
        self.db_file = db_file
        self.conn = self.create_connection()
        if self.conn:
            self.create_table()

    def create_connection(self):
        """Create a database connection to the SQLite database specified by DB_FILE."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            return conn
        except Error as e:
            print(e)
        return conn

    def create_table(self):
        """Create a table for storing species data if it does not exist."""
        try:
            sql_create_species_table = """
            CREATE TABLE IF NOT EXISTS species (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                genus TEXT NOT NULL,
                order_name TEXT,
                family_name TEXT,
                UNIQUE(genus)
            );
            """
            cursor = self.conn.cursor()
            cursor.execute(sql_create_species_table)
        except Error as e:
            print(e)


    def get_order_and_family_from_edirect(self, genus):
        # Check the local database first
        cursor = self.conn.cursor()
        cursor.execute("SELECT order_name, family_name FROM species WHERE genus = ?", (genus,))
        row = cursor.fetchone()
        if row:
            order_name, family_name = row
            print(f"Cache hit for genus '{genus}': Order: {order_name}, Family: {family_name}")
            return order_name, family_name
        else:
            print(f"Cache miss for genus '{genus}'. Fetching from NCBI...")
            try:
                Entrez.email = "hherhold@amnh.org"  # Always set your email
                handle = Entrez.esearch(db="taxonomy", term=genus, retmode="xml")
                records = Entrez.read(handle)
                handle.close()
                if records['IdList']:
                    tax_id = records['IdList'][0]
                    handle = Entrez.efetch(db="taxonomy", id=tax_id, retmode="xml")
                    tax_records = Entrez.read(handle)
                    handle.close()

                    print(f"Fetched data for genus '{genus}' from NCBI: {tax_records[0]['LineageEx']}")

                    # Grab the LineageEx list to get order and family.
                    lineage_ex = tax_records[0]['LineageEx']
                    # Now go through it and search for a 'Rank' of 'order' and 'family'.
                    for item in lineage_ex:
                        if item['Rank'] == 'order':
                            order_name = item['ScientificName']
                        elif item['Rank'] == 'family':
                            family_name = item['ScientificName']

                    # Insert the new genus into the database
                    cursor.execute("INSERT INTO species (genus, order_name, family_name) VALUES (?, ?, ?)",
                                    (genus, order_name, family_name))
                    self.conn.commit()
                    print(f"Fetched and cached data for genus '{genus}' from NCBI: Order: {order_name}, Family: {family_name}")
                    return order_name, family_name
            except Exception as e:
                print(f"Error fetching data for genus '{genus}' from NCBI: {e}")
                return None, None
            finally:
                cursor.close()


    def get_species_info(self, genus, verbose=True):
        """Fetch species information from GBIF for the given genus."""
        cursor = self.conn.cursor()
        
        # Check if the genus is already in the database
        cursor.execute("SELECT order_name, family_name FROM species WHERE genus = ?", (genus,))
        row = cursor.fetchone()

        if row:
            # If found, return the cached data
            order_name, family_name = row
            if verbose:
                print(f"Cache hit for genus '{genus}': Order: {order_name}, Family: {family_name}")
            return order_name, family_name

        # If not found, fetch from GBIF
        try:
            if verbose:
                print(f"Fetching data for genus '{genus}' from GBIF...")
            result = species.name_suggest(q=genus, rank='genus', limit=1)

            order_name = result[0]['order']
            family_name = result[0]['family']

            if verbose:
                print(f"Fetched data for genus '{genus}': Order: {order_name}, Family: {family_name}")

            # Insert the new genus into the database
            cursor.execute("INSERT INTO species (genus, order_name, family_name) VALUES (?, ?, ?)",
                            (genus, order_name, family_name))
            self.conn.commit()
            if verbose:
                print(f"Fetched and cached data for genus '{genus}': Order: {order_name}, Family: {family_name}")
            return order_name, family_name

        except Exception as e:
            print(f"Error fetching data for genus '{genus}': {e}")

            # Try searching NCBI taxonomy as a fallback
            try:
                from Bio import Entrez
                Entrez.email = "hherhold@amnh.org"  # Always set your email
                handle = Entrez.esearch(db="taxonomy", term=genus, retmode="xml")
                records = Entrez.read(handle)
                handle.close()
                if records['IdList']:
                    tax_id = records['IdList'][0]
                    handle = Entrez.efetch(db="taxonomy", id=tax_id, retmode="xml")
                    tax_records = Entrez.read(handle)
                    handle.close()

                    if verbose:
                        print(f"Fetched data for genus '{genus}' from NCBI: {tax_records[0]['LineageEx']}")

                    # Grab the LineageEx list to get order and family.
                    lineage_ex = tax_records[0]['LineageEx']
                    # Now go through it and search for a 'Rank' of 'order' and 'family'.
                    for item in lineage_ex:
                        if item['Rank'] == 'order':
                            order_name = item['ScientificName']
                        elif item['Rank'] == 'family':
                            family_name = item['ScientificName']

                    # Insert the new genus into the database
                    cursor.execute("INSERT INTO species (genus, order_name, family_name) VALUES (?, ?, ?)",
                                   (genus, order_name, family_name))
                    self.conn.commit()
                    if verbose:
                        print(f"Fetched and cached data for genus '{genus}' from NCBI: Order: {order_name}, Family: {family_name}")
                    return order_name, family_name
            except Exception as ncbi_error:
                print(f"Error fetching data for genus '{genus}' from NCBI: {ncbi_error}")

            return None
        finally:
            cursor.close()

    # Function to add info to the database. This is for taxa not in the GBIF database.
    def add_species_info(self, genus, order_name, family_name):
        """Add species information to the database."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO species (genus, order_name, family_name) VALUES (?, ?, ?)",
                           (genus, order_name, family_name))
            self.conn.commit()
            print(f"Added {genus} to the database with Order: {order_name}, Family: {family_name}")
        except Error as e:
            print(f"Error adding data for genus '{genus}': {e}")
        finally:
            cursor.close()

    # For maintenance, or when I screwed up adding something incorrectly.
    def remove_species_info(self, genus):
        """Remove species information from the database."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("DELETE FROM species WHERE genus = ?", (genus,))
            self.conn.commit()
            print(f"Removed {genus} from the database.")
        except Error as e:
            print(f"Error removing data for genus '{genus}': {e}")
        finally:
            cursor.close()


# Test the GBIFSpeciesDB class
if __name__ == "__main__":
    # If we're on windows, we need to set the data_dir to the correct path.
    gbif_db = TaxonomyDB()

    # Example usage
    genus_list = ['Panthera', 'Ursus', 'Canis', 'Felis', 'Elephas']
    for genus in genus_list:
        order, family = gbif_db.get_species_info(genus)
        if order and family:
            print(f"Genus: {genus}, Order: {order}, Family: {family}")
        else:
            print(f"Failed to retrieve data for genus '{genus}'")
    # Close the database connection
    if gbif_db.conn:
        gbif_db.conn.close()
        print("Database connection closed.")
