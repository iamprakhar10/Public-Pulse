from test1 import func
def fun(a:int, b:str):
    print(a)
    print(b)

fun('2s',2)

"""
	
{
  "name": "test user",
  "email": "user@email.com",
  "phone": "9876543210",
  "password": "password"
}
{
  "id": 13,
  "name": "test user",
  "email": "user@email.com",
  "phone": "9876543210",
  "is_verified": false
}
"""




"""
one gmail id will have one refresh toke, if another laptop get's 
a refresh token from same id, the current on won't work to send
email, and even to revoke the old refresh token.
"""