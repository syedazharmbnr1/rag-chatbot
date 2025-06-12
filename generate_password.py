import streamlit_authenticator as stauth

passwords = ["1234"]
# hashed_passwords = stauth.Hasher(passwords).generate()
hashed_passwords = stauth.Hasher.hash_list(passwords)
# print(stauth.Hasher.hash("user1"))
for i, hashed_password in enumerate(hashed_passwords):
    print(f"hashed password of {passwords[i]} is: {hashed_password}")