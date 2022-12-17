from fastapi import FastAPI


from pydantic import BaseModel
from typing import Optional

from hashing import Hash
from fastapi import FastAPI, HTTPException, Depends, Request,status
# from oauth import get_current_user
from jwttoken import create_access_token
from fastapi.security import OAuth2PasswordRequestForm,OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from urllib.error import HTTPError

from jwttoken import *
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



x=mycol.find({},{"username":1,"password":1,"email":1})
dbdict=dict()
for data in x:
    em=data["username"]
    dbdict[em]={"password":data["password"],"username":em,"email":data["email"]}



class User(BaseModel):
    username: str
    email: Union[str, None] = None
    password: Union[str, None] = None
    disabled: Union[bool, None] = None


class UserInDB(User):
    password: str

def get_user(username: str):
    user = mycol.find_one({"username":username})
    if user:
        return UserInDB(**user)

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



async def get_current_user(token: str = Depends(oauth2_scheme)):
    # user = fake_decode_token(token)
    credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, SECRET_KEY,algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not Hash.verify(password,user.password):
        return False
    return user




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
@app.post('/token')
def login(request:OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(request.username, request.password)
    if not user:
       raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Incorrect username or password"
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub":user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}



@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
