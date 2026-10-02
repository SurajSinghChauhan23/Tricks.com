from app.database.connections import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Add user_type column if it doesn't exist
    try:
        conn.execute(text("ALTER TABLE register_user ADD COLUMN user_type VARCHAR(20) NOT NULL DEFAULT 'person'"))
        print('Added user_type column')
    except Exception as e:
        print(f'user_type: {e}')
    
    # Add company_payment_status column if it doesn't exist
    try:
        conn.execute(text("ALTER TABLE register_user ADD COLUMN company_payment_status VARCHAR(20) DEFAULT 'unpaid'"))
        print('Added company_payment_status column')
    except Exception as e:
        print(f'company_payment_status: {e}')

    # Create payment_transactions table
    try:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS payment_transactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                transaction_id VARCHAR(100) NOT NULL,
                source_type VARCHAR(50) NOT NULL,
                source_id INT,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        print('payment_transactions table ready')
    except Exception as e:
        print(f'payment_transactions: {e}')
    
    conn.commit()
    print('DB migration complete')
