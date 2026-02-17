import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_URL = os.getenv('DATABASE_URL', 'postgresql://odoo:npg_izVexEbh8Yu2@kargo-odoo.postgres.database.azure.com/kargo')
