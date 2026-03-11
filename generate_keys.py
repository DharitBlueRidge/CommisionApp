import streamlit_authenticator as stauth

# Version 0.4.x expects a credentials dictionary
credentials = {
    'usernames': {
        'admin': {
            'name': 'Admin User',
            'password': 'Howie-hacked-boost' # Replace this with your actual password
        }
    }
}

# The library hashes the passwords in-place in the credentials dictionary
stauth.Hasher.hash_passwords(credentials)

# Extract the hashed password
hashed_password = credentials['usernames']['admin']['password']

print("\n--- HASHED PASSWORD ---")
print(hashed_password)
print("-----------------------\n")
print("Copy the hash above and paste it into .streamlit/secrets.toml")