from fastapi import FastAPI


from pydantic import BaseModel
from typing import Optional

from hashing import Hash
from fastapi import FastAPI, HTTPException, Depends, Request,status
from oauth import get_current_user
from jwttoken import create_access_token
from fastapi.security import OAuth2PasswordRequestForm,OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from urllib.error import HTTPError

from typing import Union

import pymongo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
app = FastAPI()

@app.get("/items/")
async def read_items(token: str = Depends(oauth2_scheme)):
    return {"token": token}

origins = [
    "http://localhost:3000",
    "http://localhost:8080",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["testdb"]
mycol = mydb["testusers"]

#temporary fake db details into a dictionary



x=mycol.find({},{"username":1,"password":1})
dbdict=dict()
for data in x:
    em=data["username"]
    dbdict[em]={"password":data["password"]}

class User(BaseModel):
    username: str
    email: str
    password:str


class UserInDB(User):
    hashed_password: str

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

def fake_decode_token(token):
    # This doesn't provide any security at all
    # Check the next version
    user = get_user(dbdict, token)
    return user


class Login(BaseModel):
    username: str
    email:str
    password: str
class Token(BaseModel):
    access_token: str
    token_type: str
class TokenData(BaseModel):
    username: Optional[str] = None

def fake_decode_token(token):
    return User(
        username=token + "fakedecoded", email="john@example.com", full_name="John Doe"
    )


async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = fake_decode_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user




@app.get('/')
def index():
    return {'data':'Hello World'}


@app.post('/register')
def create_user(request:User):
   hashed_pass = Hash.bcrypt(request.password)
   user_object = dict(request)
   user_object["password"] = hashed_pass
   user_id = mycol.insert_one(user_object)
   return {"res":"created"}

#token endpoint
@app.post('/login')
def login(request:OAuth2PasswordRequestForm = Depends()):
    user = mycol.find_one({"username":request.username})
    if not user:
       raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not Hash.verify(user["password"],request.password):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    access_token = create_access_token(data={"sub": user["username"] })
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user




