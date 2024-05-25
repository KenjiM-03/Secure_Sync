#import hashlib
import sqlite3
import time
from pyfingerprint.pyfingerprint import PyFingerprint

DB_PATH = 'attendance.db'

def create_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            fingerprint_template BLOB NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time_in TEXT,
            time_out TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

def get_fingerprint_template(f):
    try:
        print('Waiting for finger...')

        # Wait for finger to read
        while not f.readImage():
            pass

        # Converts read image to characteristics and stores it in charbuffer 1
        f.convertImage(0x01)

        # Remove finger and wait for the same finger again
        print('Remove finger...')
        time.sleep(2)
        print('Waiting for same finger again...')

        # Wait for finger to read again
        while not f.readImage():
            pass

        # Converts read image to characteristics and stores it in charbuffer 2
        f.convertImage(0x02)

        # Compares the charbuffers
        if f.compareCharacteristics() == 0:
            raise Exception('Fingers do not match.')

        # Downloads the characteristics of template
        template = f.downloadCharacteristics(0x01)

        return template

    except Exception as e:
        print('Failed to get fingerprint template!')
        print('Exception message: ' + str(e))
        return None

def enroll_user():
    try:
        f = PyFingerprint('/dev/ttyS0', 57600, 0xFFFFFFFF, 0x00000000)

        if not f.verifyPassword():
            raise ValueError('The fingerprint sensor password is incorrect!')

        template = get_fingerprint_template(f)
        if template is None:
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT name, fingerprint_template FROM users')
        users = cursor.fetchall()

        for user in users:
            stored_template = list(map(int, user[1].strip('[]').split(', ')))
            f.uploadCharacteristics(0x01, stored_template)
            if f.compareCharacteristics() > 50:  # Similarity threshold
                print(f'Fingerprint already enrolled for {user[0]}.')
                conn.close()
                return

        name = input('Enter name: ')
        cursor.execute('INSERT INTO users (name, fingerprint_template) VALUES (?, ?)', (name, str(template)))
        conn.commit()
        conn.close()

        print(f'Fingerprint for {name} enrolled successfully.')

    except Exception as e:
        print('Failed to enroll user!')
        print('Exception message: ' + str(e))

def verify_fingerprint():
    try:
        f = PyFingerprint('/dev/ttyS0', 57600, 0xFFFFFFFF, 0x00000000)

        if not f.verifyPassword():
            raise ValueError('The fingerprint sensor password is incorrect!')

        print('Waiting for finger...')

        # Wait for finger to read
        while not f.readImage():
            pass

        # Converts read image to characteristics and stores it in charbuffer 1
        f.convertImage(0x01)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, fingerprint_template FROM users')
        users = cursor.fetchall()

        matched_user = None
        for user in users:
            stored_template = list(map(int, user[2].strip('[]').split(', ')))
            f.uploadCharacteristics(0x02, stored_template)  # Compare with charbuffer 2
            if f.compareCharacteristics() > 50:  # Similarity threshold
                matched_user = user
                break

        if matched_user:
            user_id, user_name = matched_user[0], matched_user[1]
            current_date = time.strftime('%Y-%m-%d')
            current_time = time.strftime('%H:%M:%S')

            cursor.execute('SELECT * FROM attendance WHERE user_id = ? AND date = ? AND time_out IS NULL', (user_id, current_date))
            attendance_record = cursor.fetchone()

            if attendance_record:
                cursor.execute('UPDATE attendance SET time_out = ? WHERE id = ?', (current_time, attendance_record[0]))
                print(f'Time-out recorded for {user_name} at {current_time}.')
            else:
                cursor.execute('INSERT INTO attendance (user_id, date, time_in) VALUES (?, ?, ?)',
                               (user_id, current_date, current_time))
                print(f'Time-in recorded for {user_name} at {current_time}.')

            conn.commit()
        else:
            print('Unrecognized fingerprint.')

        conn.close()

    except Exception as e:
        print('Failed to verify fingerprint!')
        print('Exception message: ' + str(e))

def update_fingerprint():
    name = input("Enter name to update fingerprint: ")
    try:
        f = PyFingerprint('/dev/ttyS0', 57600, 0xFFFFFFFF, 0x00000000)

        if not f.verifyPassword():
            raise ValueError('The fingerprint sensor password is incorrect!')

        template = get_fingerprint_template(f)
        if template is None:
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET fingerprint_template = ? WHERE name = ?', (str(template), name))
        conn.commit()
        conn.close()

        print(f'Fingerprint for {name} updated successfully.')

    except Exception as e:
        print('Failed to update fingerprint!')
        print('Exception message: ' + str(e))

def delete_fingerprint():
    name = input("Enter name to delete fingerprint: ")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT fingerprint_template FROM users WHERE name = ?', (name,))
        result = cursor.fetchone()

        if not result:
            print('Name not found.')
            return

        cursor.execute('DELETE FROM users WHERE name = ?', (name,))
        conn.commit()
        conn.close()

        print(f'Fingerprint for {name} deleted successfully.')

    except Exception as e:
        print('Failed to delete fingerprint!')
        print('Exception message: ' + str(e))

def view_fingerprints():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM users')
        users = cursor.fetchall()

        if not users:
            print('No fingerprints enrolled.')
        else:
            print('Enrolled fingerprints:')
            for user in users:
                print(user[0])

        conn.close()

    except Exception as e:
        print('Failed to fetch fingerprints!')
        print('Exception message: ' + str(e))

def main():
    create_database()

    while True:
        print("\n1. Enroll Fingerprint")
        print("2. Verify Fingerprint for Attendance")
        print("3. Update Fingerprint")
        print("4. Delete Fingerprint")
        print("5. View Enrolled Fingerprints")
        print("6. Exit")

        choice = input("Enter your choice: ")

        if choice == '1':
            enroll_user()
        elif choice == '2':
            verify_fingerprint()
        elif choice == '3':
            update_fingerprint()
        elif choice == '4':
            delete_fingerprint()
        elif choice == '5':
            view_fingerprints()
        elif choice == '6':
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
